from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = 1


@dataclass
class Button:
    index: int
    label: str
    icon: str = ""
    action: dict = field(default_factory=dict)


@dataclass
class KnobBinding:
    index: int
    label: str = ""
    on_turn: dict = field(default_factory=dict)
    on_press: dict = field(default_factory=dict)


@dataclass
class Profile:
    schema_version: int
    name: str
    trigger_apps: list[str] = field(default_factory=list)
    deck: str = "any"
    buttons: list[Button] = field(default_factory=list)
    knobs: list[KnobBinding] = field(default_factory=list)
