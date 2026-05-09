from __future__ import annotations

from helmd.actions.base import Action, ActionResult
from helmd.core.platform.base import Platform


class KeypressAction(Action):
    _platform: Platform | None = None

    def __init__(self, keys: list[str]) -> None:
        self.keys = keys

    @classmethod
    def set_platform(cls, platform: Platform) -> None:
        cls._platform = platform

    @classmethod
    def from_config(cls, config: dict) -> "KeypressAction":
        return cls(keys=config["keys"])

    async def execute(self) -> ActionResult:
        if self._platform is None:
            return ActionResult(ok=False, detail="platform not set")
        self._platform.send_keys(self.keys)
        return ActionResult(ok=True)
