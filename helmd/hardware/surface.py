from abc import ABC, abstractmethod


class Surface(ABC):
    @property
    @abstractmethod
    def serial(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def model(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def button_count(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def knob_count(self) -> int:
        raise NotImplementedError
