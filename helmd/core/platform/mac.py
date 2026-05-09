import logging
import subprocess

from pynput.keyboard import Controller, Key, KeyCode

from helmd.core.platform.base import Platform

_log = logging.getLogger(__name__)


class MacPlatform(Platform):
    def __init__(self) -> None:
        self._kb = Controller()

    def active_window(self) -> str:
        script = 'tell application "System Events" to get name of first application process whose frontmost is true'
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=3,
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def _resolve_key(self, name: str) -> Key | KeyCode:
        try:
            return Key[name]
        except KeyError:
            return KeyCode.from_char(name)

    def send_keys(self, keys: list[str]) -> None:
        resolved = [self._resolve_key(k) for k in keys]
        for key in resolved:
            self._kb.press(key)
        for key in reversed(resolved):
            self._kb.release(key)
