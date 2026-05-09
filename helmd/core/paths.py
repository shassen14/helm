from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HelmPaths:
    user_profiles_dir: Path
    state_file: Path
    log_dir: Path

    @classmethod
    def resolve(cls) -> "HelmPaths":
        if platform.system() == "Darwin":
            base = Path.home() / "Library" / "Application Support" / "helm"
        else:
            xdg = Path.home() / ".config"
            base = xdg / "helm"
        return cls(
            user_profiles_dir=base / "profiles",
            state_file=base / "state.json",
            log_dir=base / "logs",
        )
