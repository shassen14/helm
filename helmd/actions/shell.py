import asyncio

from helmd.actions.base import Action, ActionResult

_TIMEOUT_S = 30


class ShellAction(Action):
    def __init__(self, command: str) -> None:
        self.command = command

    @classmethod
    def from_config(cls, config: dict) -> "ShellAction":
        return cls(command=config["command"])

    async def execute(self) -> ActionResult:
        proc = await asyncio.create_subprocess_shell(
            self.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), _TIMEOUT_S)
        except asyncio.TimeoutError:
            proc.kill()
            return ActionResult(ok=False, detail=f"timed out after {_TIMEOUT_S}s")
        rc = proc.returncode
        detail = (stdout or stderr).decode().strip()
        return ActionResult(ok=rc == 0, detail=detail)
