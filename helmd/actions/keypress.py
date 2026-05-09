from helmd.actions.base import Action, ActionResult


class KeypressAction(Action):
    def __init__(self, keys: list[str]) -> None:
        self.keys = keys

    async def execute(self) -> ActionResult:
        raise NotImplementedError
