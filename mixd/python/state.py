from __future__ import annotations

from dataclasses import dataclass, field

from mixd.python.constants import DEFAULT_ROUTING
from mixd.python.devices import AudioDevice


@dataclass
class ChannelState:
    name: str
    level: float = 1.0
    muted: bool = False
    outputs: list[str] = field(default_factory=list)


@dataclass
class MixerState:
    channels: dict[str, ChannelState]
    devices: list[AudioDevice] = field(default_factory=list)


def default_state() -> MixerState:
    channels = {
        name: ChannelState(name=name, outputs=list(outputs))
        for name, outputs in DEFAULT_ROUTING.items()
    }
    return MixerState(channels=channels)
