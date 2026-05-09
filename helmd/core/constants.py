from enum import StrEnum


class ActionType(StrEnum):
    HTTP = "http"
    SHELL = "shell"
    KEYPRESS = "keypress"
    MULTI = "multi"


class KnobEvent(StrEnum):
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    PRESS = "press"


class ProfileTrigger(StrEnum):
    APP = "app"
    MANUAL = "manual"


class DeckModel(StrEnum):
    ORIGINAL = "original"
    ORIGINAL_V2 = "original_v2"
    MINI = "mini"
    XL = "xl"
    PLUS = "plus"
    PEDAL = "pedal"
