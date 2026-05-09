from helmd.hardware.surface import Surface


class StreamDeckSurface(Surface):
    def __init__(self, device) -> None:
        self._device = device

    @property
    def serial(self) -> str:
        raise NotImplementedError

    @property
    def model(self) -> str:
        raise NotImplementedError

    @property
    def button_count(self) -> int:
        raise NotImplementedError

    @property
    def knob_count(self) -> int:
        raise NotImplementedError
