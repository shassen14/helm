from helmd.hardware.surface import Surface


class SurfaceManager:
    def __init__(self) -> None:
        self._surfaces: dict[str, Surface] = {}

    @property
    def surfaces(self) -> dict[str, Surface]:
        return self._surfaces

    async def run(self) -> None:
        raise NotImplementedError
