from helmd.actions.base import Action, ActionResult


class MultiAction(Action):
    def __init__(self, actions: list[Action]) -> None:
        self.actions = actions

    async def execute(self) -> ActionResult:
        raise NotImplementedError
