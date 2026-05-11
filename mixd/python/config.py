from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MixdSettings:
    host: str = "127.0.0.1"
    port: int = 7101


def load_config(path: Path) -> MixdSettings:
    raw = tomllib.loads(path.read_text())
    return MixdSettings(**raw.get("mixd", {}))
