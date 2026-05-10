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


class DeckEvent(StrEnum):
    DIAL_TURN = "dial_turn"
    DIAL_PRESS = "dial_press"
    DIAL_RELEASE = "dial_release"


# Default button background colour used when a profile does not specify one.
DEFAULT_BUTTON_COLOR: tuple[int, int, int] = (30, 30, 30)
