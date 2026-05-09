from helmd.actions.base import Action
from helmd.actions.http import HttpAction
from helmd.actions.keypress import KeypressAction
from helmd.actions.multi import MultiAction
from helmd.actions.shell import ShellAction
from helmd.core.constants import ActionType

ACTION_REGISTRY: dict[ActionType, type[Action]] = {
    ActionType.HTTP: HttpAction,
    ActionType.SHELL: ShellAction,
    ActionType.KEYPRESS: KeypressAction,
    ActionType.MULTI: MultiAction,
}


def create_action(config: dict) -> Action:
    action_type = ActionType(config.get("type"))
    return ACTION_REGISTRY[action_type].from_config(config)
