from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MixdSettings:
    host: str = "127.0.0.1"
    port: int = 7101
