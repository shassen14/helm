from __future__ import annotations

from helmd.profiles.schema import Profile


class ProfileManager:
    def __init__(self) -> None:
        self._active: Profile | None = None

    @property
    def active(self) -> Profile | None:
        return self._active

    def swap(self, profile: Profile) -> None:
        self._active = profile
