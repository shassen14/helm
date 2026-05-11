from __future__ import annotations

import ctypes
import logging
import platform
from pathlib import Path

from mixd.python.constants import ChannelName, MixOutput

_log = logging.getLogger(__name__)

_CHANNEL_IDX: dict[str, int] = {
    ChannelName.SPOTIFY: 0,
    ChannelName.MIC: 1,
    ChannelName.DESKTOP: 2,
}

_OUTPUT_BIT: dict[str, int] = {
    MixOutput.STREAM: 0b001,
    MixOutput.MONITOR: 0b010,
    MixOutput.CHAT: 0b100,
}


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
        for name, ch in mixer.channels.items():
            self.set_level(name, ch.level)
            self.set_muted(name, ch.muted)
            self.set_outputs(name, ch.outputs)

    def set_level(self, channel: str, gain: float) -> None:
        if not self.available:
            return
        if (idx := _CHANNEL_IDX.get(channel)) is None:
            return
        self._lib.mixd_set_level(self._ptr, idx, gain)

    def set_muted(self, channel: str, muted: bool) -> None:
        if not self.available:
            return
        if (idx := _CHANNEL_IDX.get(channel)) is None:
            return
        self._lib.mixd_set_muted(self._ptr, idx, int(muted))

    def set_outputs(self, channel: str, outputs: list[str]) -> None:
        if not self.available:
            return
        if (idx := _CHANNEL_IDX.get(channel)) is None:
            return
        mask = 0
        for o in outputs:
            if (bit := _OUTPUT_BIT.get(o)) is not None:
                mask |= bit
        self._lib.mixd_set_outputs(self._ptr, idx, mask)

    def close(self) -> None:
        if self._ptr is not None and self._lib is not None:
            self._lib.mixd_destroy(self._ptr)
            self._ptr = None

    def __del__(self) -> None:
        self.close()
