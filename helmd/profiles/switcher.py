import asyncio

from helmd.core.platform.base import Platform
from helmd.profiles.manager import ProfileManager


class ProfileSwitcher:
    def __init__(self, platform: Platform, manager: ProfileManager, poll_interval_s: float = 2.0) -> None:
        self._platform = platform
        self._manager = manager
        self._poll_interval = poll_interval_s
        self._current_app = ""

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self._poll_interval)
            app = self._platform.active_window()
            if app == self._current_app:
                continue
            self._current_app = app
            self._maybe_switch(app)

    def _maybe_switch(self, app: str) -> None:
        for profile in self._manager.profiles.values():
            for trigger_app in profile.trigger_apps:
                if trigger_app.lower() in app.lower():
                    if self._manager.active is not profile:
                        self._manager.swap(profile)
                    return
