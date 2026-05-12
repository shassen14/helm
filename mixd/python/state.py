from __future__ import annotations

from dataclasses import dataclass, field

from mixd.python.constants import MAX_CHANNELS, ChannelKind, MixOutput
from mixd.python.devices import AudioDevice


@dataclass
class ChannelState:
    """One mixer channel.

    `id` is the stable key used in URLs and in the channel dict. For app
    captures it is the bundle identifier; for mic / system captures it is a
    user-chosen short id (defaults to `mic` / `system`).
    `slot` is the Rust ring-buffer index — the FFI talks in slot numbers, not
    names — and is assigned by `MixerState.allocate_slot` when the channel is
    created.
    """

    id: str
    name: str
    kind: ChannelKind
    slot: int
    source_id: str | None = None
    level: float = 1.0
    muted: bool = False
    outputs: list[str] = field(default_factory=list)


@dataclass
class BusState:
    """One output bus (stream / monitor / chat).

    `device_name` is the cpal device name from `mixd_list_output_devices`; an
    empty string / None means "use OS default". `volume` is the per-bus master
    gain applied on top of every channel's own gain.
    """

    volume: float = 1.0
    device_name: str | None = None


def _default_buses() -> dict[str, BusState]:
    return {bus.value: BusState() for bus in MixOutput}


@dataclass
class MixerState:
    channels: dict[str, ChannelState] = field(default_factory=dict)
    devices: list[AudioDevice] = field(default_factory=list)
    buses: dict[str, BusState] = field(default_factory=_default_buses)

    def allocate_slot(self) -> int | None:
        used = {ch.slot for ch in self.channels.values()}
        for i in range(MAX_CHANNELS):
            if i not in used:
                return i
        return None


def default_state() -> MixerState:
    return MixerState()
