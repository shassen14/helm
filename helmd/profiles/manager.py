from __future__ import annotations

import logging
from typing import Callable

from helmd.core.paths import HelmPaths
from helmd.profiles.loader import load_profile
from helmd.profiles.schema import Profile

_log = logging.getLogger(__name__)


class ProfileManager:
    def __init__(self) -> None:
        self._active: Profile | None = None
        self._profiles: dict[str, Profile] = {}
        self._callbacks: list[Callable[[Profile], None]] = []

    def discover(self, paths: HelmPaths) -> None:
        paths.user_profiles_dir.mkdir(parents=True, exist_ok=True)
        for toml_path in paths.user_profiles_dir.glob("*.toml"):
            try:
                p = load_profile(toml_path)
                self._profiles[p.name] = p
            except Exception as exc:
                _log.error("Failed to load profile %s: %s", toml_path, exc)

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
