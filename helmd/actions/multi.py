from helmd.actions.base import Action, ActionResult


class MultiAction(Action):
    def __init__(self, actions: list[Action]) -> None:
        self.actions = actions

    @classmethod
    def from_config(cls, config: dict) -> "MultiAction":
        from helmd.actions.registry import create_action
        return cls(actions=[create_action(a) for a in config["actions"]])

    async def execute(self) -> ActionResult:
        failures: list[str] = []
        for action in self.actions:
            result = await action.execute()
            if not result.ok:
                failures.append(result.detail)
        return ActionResult(ok=not failures, detail="; ".join(failures))
