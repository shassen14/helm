from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MixerState:
    channels: dict[str, float] = field(default_factory=dict)
