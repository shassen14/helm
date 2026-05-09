import httpx

from helmd.actions.base import Action, ActionResult


class HttpAction(Action):
    def __init__(
        self,
        url: str,
        method: str = "POST",
        body: dict | None = None,
        body_template: str | None = None,
    ) -> None:
        self.url = url
        self.method = method
        self.body = body or {}
        self.body_template = body_template

    @classmethod
    def from_config(cls, config: dict) -> "HttpAction":
        return cls(
            url=config["url"],
            method=config.get("method", "POST"),
            body=config.get("body"),
            body_template=config.get("body_template"),
        )

    async def execute(self) -> ActionResult:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.request(self.method, self.url, json=self.body or None)
            if resp.is_success:
                return ActionResult(ok=True)
            return ActionResult(ok=False, detail=f"HTTP {resp.status_code}")
        except httpx.HTTPError as exc:
            return ActionResult(ok=False, detail=str(exc))
