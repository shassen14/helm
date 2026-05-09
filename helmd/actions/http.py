from helmd.actions.base import Action, ActionResult


class HttpAction(Action):
    def __init__(self, url: str, method: str = "POST", body: dict | None = None) -> None:
        self.url = url
        self.method = method
        self.body = body or {}

    async def execute(self) -> ActionResult:
        raise NotImplementedError
