from __future__ import annotations

import ctypes
import logging
import platform
from pathlib import Path

from mixd.python.constants import BUS_INDEX, OUTPUT_BITS, ChannelKind

_log = logging.getLogger(__name__)


def _lib_path() -> Path:
    crate = Path(__file__).parent.parent / "rust"
    suffix = ".dylib" if platform.system() == "Darwin" else ".so"
    for profile in ("release", "debug"):
        p = crate / "target" / profile / f"libmixd{suffix}"
        if p.exists():
            return p
    raise FileNotFoundError(
        f"libmixd{suffix} not found; run: cd mixd/rust && cargo build --release"
    )


def _load_lib() -> ctypes.CDLL | None:
    try:
        lib = ctypes.CDLL(str(_lib_path()))
    except (FileNotFoundError, OSError) as exc:
        _log.warning("Rust audio core unavailable: %s", exc)
        return None
    lib.mixd_create.argtypes = []
    lib.mixd_create.restype = ctypes.c_void_p
    lib.mixd_destroy.argtypes = [ctypes.c_void_p]
    lib.mixd_destroy.restype = None
    lib.mixd_set_level.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_float]
    lib.mixd_set_level.restype = None
    lib.mixd_set_muted.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]
    lib.mixd_set_muted.restype = None
    lib.mixd_set_outputs.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]
    lib.mixd_set_outputs.restype = None
    lib.mixd_start_capture_app.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p]
    lib.mixd_start_capture_app.restype = ctypes.c_int32
    lib.mixd_start_capture_mic.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.mixd_start_capture_mic.restype = ctypes.c_int32
    lib.mixd_start_capture_system.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.mixd_start_capture_system.restype = ctypes.c_int32
    lib.mixd_stop_capture.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.mixd_stop_capture.restype = ctypes.c_int32
    lib.mixd_set_bus_volume.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_float]
    lib.mixd_set_bus_volume.restype = None
    lib.mixd_open_bus.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p]
    lib.mixd_open_bus.restype = ctypes.c_int32
    lib.mixd_close_bus.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.mixd_close_bus.restype = None
    lib.mixd_list_output_devices.argtypes = [ctypes.c_void_p]
    lib.mixd_list_output_devices.restype = ctypes.c_void_p
    lib.mixd_free_string.argtypes = [ctypes.c_void_p]
    lib.mixd_free_string.restype = None
    return lib


class MixEngine:
    def __init__(self) -> None:
        self._lib = _load_lib()
        self._ptr: int | None = None
        if self._lib:
            ptr = self._lib.mixd_create()
            if ptr:
                self._ptr = ptr
                _log.info("Rust audio core started")
            else:
                _log.error("mixd_create returned null")

    @property
    def available(self) -> bool:
        return self._ptr is not None

    def sync_state(self, mixer) -> None:
        for bus_name, bus in mixer.buses.items():
            self.set_bus_volume(bus_name, bus.volume)
            self.open_bus(bus_name, bus.device_name)
        for ch in mixer.channels.values():
            self.set_level(ch.slot, ch.level)
            self.set_muted(ch.slot, ch.muted)
            self.set_outputs(ch.slot, ch.outputs)

    def set_level(self, slot: int, gain: float) -> None:
        if not self.available:
            return
        self._lib.mixd_set_level(self._ptr, slot, gain)

    def set_muted(self, slot: int, muted: bool) -> None:
        if not self.available:
            return
        self._lib.mixd_set_muted(self._ptr, slot, int(muted))

    def set_outputs(self, slot: int, outputs: list[str]) -> None:
        if not self.available:
            return
        mask = 0
        for o in outputs:
            if (bit := OUTPUT_BITS.get(o)) is not None:
                mask |= bit
        self._lib.mixd_set_outputs(self._ptr, slot, mask)

    def start_capture(self, slot: int, kind: ChannelKind, source_id: str | None) -> bool:
        if not self.available:
            return False
        match kind:
            case ChannelKind.APP:
                if not source_id:
                    return False
                rc = self._lib.mixd_start_capture_app(self._ptr, slot, source_id.encode())
            case ChannelKind.MIC:
                rc = self._lib.mixd_start_capture_mic(self._ptr, slot)
            case ChannelKind.SYSTEM:
                rc = self._lib.mixd_start_capture_system(self._ptr, slot)
            case _:
                return False
        return rc == 0

    def stop_capture(self, slot: int) -> None:
        if not self.available:
            return
        self._lib.mixd_stop_capture(self._ptr, slot)

    def set_bus_volume(self, bus: str, volume: float) -> None:
        if not self.available:
            return
        idx = BUS_INDEX.get(bus)
        if idx is None:
            return
        self._lib.mixd_set_bus_volume(self._ptr, idx, volume)

    def open_bus(self, bus: str, device_name: str | None) -> bool:
        if not self.available:
            return False
        idx = BUS_INDEX.get(bus)
        if idx is None:
            return False
        encoded = device_name.encode() if device_name else None
        return self._lib.mixd_open_bus(self._ptr, idx, encoded) == 0

    def list_output_devices(self) -> list[str]:
        if not self.available:
            return []
        ptr = self._lib.mixd_list_output_devices(self._ptr)
        if not ptr:
            return []
        try:
            raw = ctypes.cast(ptr, ctypes.c_char_p).value or b""
            text = raw.decode(errors="replace")
        finally:
            self._lib.mixd_free_string(ptr)
        return [line for line in text.split("\n") if line]

    def close(self) -> None:
        if self._ptr is not None and self._lib is not None:
            self._lib.mixd_destroy(self._ptr)
            self._ptr = None

    def __del__(self) -> None:
        self.close()
