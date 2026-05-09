from helmd.actions.base import Action
from helmd.core.constants import ActionType

ACTION_REGISTRY: dict[ActionType, type[Action]] = {}
