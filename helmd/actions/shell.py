from helmd.actions.base import Action, ActionResult


class ShellAction(Action):
    def __init__(self, command: str) -> None:
        self.command = command

    async def execute(self) -> ActionResult:
        raise NotImplementedError
