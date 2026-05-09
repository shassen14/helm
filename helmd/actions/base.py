from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ActionResult:
    ok: bool
    detail: str = ""


class Action(ABC):
    @abstractmethod
    async def execute(self) -> ActionResult:
        raise NotImplementedError
