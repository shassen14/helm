from helmd.core.platform.base import Platform


class MacPlatform(Platform):
    def active_window(self) -> str:
        raise NotImplementedError

    def send_keys(self, keys: list[str]) -> None:
        raise NotImplementedError
