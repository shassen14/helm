import logging
import subprocess

from pynput.keyboard import Controller, Key, KeyCode

from helmd.core.platform.base import Platform

_log = logging.getLogger(__name__)


class LinuxPlatform(Platform):
    def __init__(self) -> None:
        self._kb = Controller()
        self._xdotool_warned = False

    def active_window(self) -> str:
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode != 0:
                if not self._xdotool_warned:
                    _log.warning("xdotool returned non-zero: %s", result.stderr.strip())
                    self._xdotool_warned = True
                return ""
            return result.stdout.strip()
        except FileNotFoundError:
            if not self._xdotool_warned:
                _log.warning("xdotool not found; active window detection disabled")
                self._xdotool_warned = True
            return ""

    def _resolve_key(self, name: str) -> Key | KeyCode:
        try:
            return Key[name]
        except KeyError:
            return KeyCode.from_char(name)

    def send_keys(self, keys: list[str]) -> None:
        try:
            resolved = [self._resolve_key(k) for k in keys]
            for key in resolved:
                self._kb.press(key)
            for key in reversed(resolved):
                self._kb.release(key)
        except Exception as exc:
            _log.warning("send_keys failed (Wayland?): %s", exc)
