from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class HelmdConfig:
    host: str = "127.0.0.1"
    port: int = 7100
    brightness: int = 70


@dataclass
class MixdConfig:
    host: str = "127.0.0.1"
    port: int = 7101


@dataclass
class ServicesConfig:
    veil_url: str = "http://192.168.1.X:8002"
    couch_url: str = "http://192.168.1.X:8003"


@dataclass
class SwitcherConfig:
    enabled: bool = True
    poll_interval_s: float = 2.0


@dataclass
class DevicesConfig:
    allowed_deck_serials: list[str] = field(default_factory=list)


@dataclass
class Settings:
    helmd: HelmdConfig = field(default_factory=HelmdConfig)
    mixd: MixdConfig = field(default_factory=MixdConfig)
    services: ServicesConfig = field(default_factory=ServicesConfig)
    switcher: SwitcherConfig = field(default_factory=SwitcherConfig)
    devices: DevicesConfig = field(default_factory=DevicesConfig)


def load_config(path: Path) -> Settings:
    raw = tomllib.loads(path.read_text())
    return Settings(
        helmd=HelmdConfig(**raw.get("helmd", {})),
        mixd=MixdConfig(**raw.get("mixd", {})),
        services=ServicesConfig(**raw.get("services", {})),
        switcher=SwitcherConfig(**raw.get("switcher", {})),
        devices=DevicesConfig(**raw.get("devices", {})),
    )
