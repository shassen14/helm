from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from PIL.Image import Image
    from helmd.core.constants import DeckEvent


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

    @property
    @abstractmethod
    def key_size(self) -> tuple[int, int]:
        raise NotImplementedError

    @abstractmethod
    def set_brightness(self, percent: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_key_image(self, key_index: int, image: "Image") -> None:
        raise NotImplementedError

    @abstractmethod
    def clear_key(self, key_index: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def register_key_callback(self, cb: Callable[[int, bool], None]) -> None:
        raise NotImplementedError

    @abstractmethod
    def register_dial_callback(self, cb: Callable[[int, "DeckEvent", int], None]) -> None:
        raise NotImplementedError

    @property
    def device_path(self) -> str:
        return ""
