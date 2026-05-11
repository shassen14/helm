from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from helmd.core.constants import DEFAULT_BUTTON_COLOR, DeckEvent
from helmd.core.paths import HelmPaths
from helmd.hardware.deck import StreamDeckSurface
from helmd.hardware.renderer import render_key

if TYPE_CHECKING:
    from helmd.core.config import DevicesConfig
    from helmd.hardware.surface import Surface
    from helmd.profiles.manager import ProfileManager
    from helmd.profiles.schema import Profile

_log = logging.getLogger(__name__)


class SurfaceManager:
    def __init__(
        self,
        manager: ProfileManager,
        devices_config: DevicesConfig,
        brightness: int = 70,
        poll_interval_s: float = 3.0,
    ) -> None:
        self._manager = manager
        self._devices_config = devices_config
        self._brightness = brightness
        self._poll_interval = poll_interval_s
        self._surfaces: dict[str, Surface] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def surfaces(self) -> dict[str, Surface]:
        return dict(self._surfaces)

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._manager.register_callback(self._on_profile_change)
        if self._manager.active:
            self._on_profile_change(self._manager.active)
        try:
            while True:
                await self._poll_devices()
                await asyncio.sleep(self._poll_interval)
        finally:
            self._close_all()

    async def _poll_devices(self) -> None:
        try:
            from StreamDeck.DeviceManager import DeviceManager

            found = DeviceManager().enumerate()
        except Exception as exc:
            _log.debug("Device enumeration failed: %s", exc)
            return

        found_serials: set[str] = set()
        allowlist = set(self._devices_config.allowed_deck_serials)

        # Build path→serial map for already-open surfaces so we can recognise
        # them in the enumeration without re-opening their held device handle.
        tracked_by_path = {
            s.device_path: serial
            for serial, s in self._surfaces.items()
            if s.device_path
        }

        for raw in found:
            raw_path = raw.device.device_info.get("path", "")

            if raw_path and raw_path in tracked_by_path:
                found_serials.add(tracked_by_path[raw_path])
                continue

            # New device — open to confirm serial.
            try:
                raw.open()
                serial = raw.get_serial_number()
                found_serials.add(serial)

                if serial in self._surfaces or (allowlist and serial not in allowlist):
                    raw.close()
                    continue

                self._attach(StreamDeckSurface(raw))
            except Exception as exc:
                _log.warning("Failed to probe device: %s", exc)
                try:
                    raw.close()
                except Exception:
                    pass

        for serial in list(self._surfaces):
            if serial not in found_serials:
                self._detach(serial)

    def _attach(self, surface: Surface) -> None:
        surface.set_brightness(self._brightness)
        loop = self._loop

        def on_key(key: int, pressed: bool) -> None:
            asyncio.run_coroutine_threadsafe(
                self._on_key(surface.serial, key, pressed), loop
            )

        def on_dial(dial: int, event: DeckEvent, value: int) -> None:
            asyncio.run_coroutine_threadsafe(
                self._on_dial(surface.serial, dial, event, value), loop
            )

        surface.register_key_callback(on_key)
        surface.register_dial_callback(on_dial)
        self._surfaces[surface.serial] = surface
        _log.info("Deck attached serial=%s model=%s", surface.serial, surface.model)

        profile = self._manager.active
        if profile:
            self._render_profile(surface, profile)

    def _detach(self, serial: str) -> None:
        surface = self._surfaces.pop(serial, None)
        if surface:
            try:
                surface.close()
            except Exception as exc:
                _log.warning("Error closing deck %s: %s", serial, exc)
            _log.info("Deck detached serial=%s", serial)

    def _render_profile(self, surface: Surface, profile: Profile) -> None:
        paths = HelmPaths.resolve()
        button_map = {b.index: b for b in profile.buttons}
        size = surface.key_size

        for idx in range(surface.button_count):
            button = button_map.get(idx)
            if button is None:
                surface.clear_key(idx)
                continue

            icon_path = None
            if button.icon:
                raw_path = paths.user_profiles_dir / button.icon
                if raw_path.is_relative_to(paths.user_profiles_dir):
                    icon_path = raw_path

            try:
                image = render_key(
                    label=button.label,
                    icon_path=icon_path,
                    color=DEFAULT_BUTTON_COLOR,
                    size=size,
                )
                surface.set_key_image(idx, image)
            except Exception as exc:
                _log.error("Render error for key %d: %s", idx, exc)
                surface.clear_key(idx)

    def _on_profile_change(self, profile: Profile) -> None:
        for surface in self._surfaces.values():
            try:
                self._render_profile(surface, profile)
            except Exception as exc:
                _log.error("Re-render error for deck %s: %s", surface.serial, exc)

    async def _on_key(self, serial: str, index: int, pressed: bool) -> None:
        if not pressed:
            return
        profile = self._manager.active
        if not profile:
            return
        button_map = {b.index: b for b in profile.buttons}
        button = button_map.get(index)
        if not button or not button.action:
            return
        try:
            from helmd.actions.registry import create_action

            await create_action(button.action).execute()
        except Exception as exc:
            _log.error("Action error for key %d: %s", index, exc)

    async def _on_dial(self, serial: str, index: int, event: DeckEvent, value: int) -> None:
        profile = self._manager.active
        if not profile:
            return
        knob_map = {k.index: k for k in profile.knobs}
        knob = knob_map.get(index)
        if not knob:
            return

        action_config = None
        if event == DeckEvent.DIAL_TURN:
            action_config = knob.on_turn
        elif event == DeckEvent.DIAL_PRESS:
            action_config = knob.on_press

        if not action_config:
            return
        try:
            from helmd.actions.registry import create_action

            resolved = {
                k: v.replace("{delta}", str(value)) if isinstance(v, str) else v
                for k, v in action_config.items()
            }
            await create_action(resolved).execute()
        except Exception as exc:
            _log.error("Action error for dial %d event %s: %s", index, event, exc)

    def _close_all(self) -> None:
        for serial in list(self._surfaces):
            self._detach(serial)
