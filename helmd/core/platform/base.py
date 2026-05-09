from abc import ABC, abstractmethod


class Platform(ABC):
    @abstractmethod
    def active_window(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def send_keys(self, keys: list[str]) -> None:
        raise NotImplementedError
