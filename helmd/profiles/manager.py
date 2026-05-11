from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Callable

from helmd.core.paths import HelmPaths
from helmd.profiles.loader import load_profile
from helmd.profiles.schema import Profile

_log = logging.getLogger(__name__)

_SEED_DIR = Path(__file__).parent.parent.parent / "profiles"


class ProfileManager:
    def __init__(self) -> None:
        self._active: Profile | None = None
        self._profiles: dict[str, Profile] = {}
        self._callbacks: list[Callable[[Profile], None]] = []

    def discover(self, paths: HelmPaths) -> None:
        paths.user_profiles_dir.mkdir(parents=True, exist_ok=True)
        self._seed_profiles(paths.user_profiles_dir)
        for toml_path in paths.user_profiles_dir.glob("*.toml"):
            try:
                p = load_profile(toml_path)
                self._profiles[p.name] = p
            except Exception as exc:
                _log.error("Failed to load profile %s: %s", toml_path, exc)
        self._activate_default()

    def _seed_profiles(self, dest: Path) -> None:
        if not _SEED_DIR.is_dir():
            return
        for src in _SEED_DIR.glob("*.toml"):
            target = dest / src.name
            if not target.exists():
                shutil.copy2(src, target)
                _log.info("Seeded profile %s", src.name)

    def _activate_default(self) -> None:
        if not self._profiles:
            _log.warning("No profiles found")
            return
        preferred = self._profiles.get("default") or next(iter(self._profiles.values()))
        self._active = preferred
        _log.info("Active profile: %s", preferred.name)

    def register_callback(self, cb: Callable[[Profile], None]) -> None:
        self._callbacks.append(cb)

    def swap(self, profile: Profile) -> None:
        self._active = profile
        _log.info("Active profile: %s", profile.name)
        for cb in self._callbacks:
            try:
                cb(profile)
            except Exception as exc:
                _log.error("Profile callback error: %s", exc)

    def swap_by_name(self, name: str) -> bool:
        profile = self._profiles.get(name)
        if profile is None:
            return False
        self.swap(profile)
        return True

    @property
    def active(self) -> Profile | None:
        return self._active

    @property
    def profiles(self) -> dict[str, Profile]:
        return dict(self._profiles)
