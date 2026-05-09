import asyncio

from helmd.core.platform.base import Platform
from helmd.profiles.manager import ProfileManager


class ProfileSwitcher:
    def __init__(self, platform: Platform, manager: ProfileManager, poll_interval_s: float = 2.0) -> None:
        self._platform = platform
        self._manager = manager
        self._poll_interval = poll_interval_s

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self._poll_interval)
