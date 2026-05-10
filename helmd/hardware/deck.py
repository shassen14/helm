from __future__ import annotations

import logging
from typing import Callable

from StreamDeck.ImageHelpers import PILHelper

from helmd.core.constants import DeckEvent
from helmd.hardware.surface import Surface

_log = logging.getLogger(__name__)

_DIAL_EVENT_MAP: dict = {}
try:
    from StreamDeck.Devices.StreamDeckPlus import DialEventType

    _DIAL_EVENT_MAP = {
        DialEventType.TURN: DeckEvent.DIAL_TURN,
        DialEventType.PUSH: DeckEvent.DIAL_PRESS,
    }
except ImportError:
    pass


class StreamDeckSurface(Surface):
    def __init__(self, device) -> None:
        self._device = device
        self._serial: str = device.get_serial_number()

    @property
    def serial(self) -> str:
        return self._serial

    @property
    def model(self) -> str:
        return self._device.DECK_TYPE

    @property
    def button_count(self) -> int:
        return self._device.KEY_COUNT

    @property
    def knob_count(self) -> int:
        return getattr(self._device, "DIAL_COUNT", 0)

    @property
    def device_path(self) -> str:
        try:
            return self._device.device.device_info.get("path", "")
        except Exception:
            return ""

    @property
    def key_size(self) -> tuple[int, int]:
        return self._device.key_image_format()["size"]

    def set_brightness(self, percent: int) -> None:
        self._device.set_brightness(max(0, min(100, percent)))

    def set_key_image(self, key_index: int, image) -> None:
        with self._device:
            native = PILHelper.to_native_key_format(self._device, image)
            self._device.set_key_image(key_index, native)

    def clear_key(self, key_index: int) -> None:
        with self._device:
            blank = PILHelper.create_key_image(self._device)
            native = PILHelper.to_native_key_format(self._device, blank)
            self._device.set_key_image(key_index, native)

    def reset(self) -> None:
        self._device.reset()

    def close(self) -> None:
        self._device.close()

    def register_key_callback(self, cb: Callable[[int, bool], None]) -> None:
        def _wrapper(deck, key: int, state: bool) -> None:
            try:
                cb(key, state)
            except Exception as exc:
                _log.error("Key callback error: %s", exc)

        self._device.set_key_callback(_wrapper)

    def register_dial_callback(self, cb: Callable[[int, DeckEvent, int], None]) -> None:
        if not _DIAL_EVENT_MAP:
            return

        def _wrapper(deck, dial: int, event_type, value) -> None:
            deck_evt = _DIAL_EVENT_MAP.get(event_type)
            if deck_evt is None:
                return
            try:
                cb(dial, deck_evt, int(value))
            except Exception as exc:
                _log.error("Dial callback error: %s", exc)

        self._device.set_dial_callback(_wrapper)
