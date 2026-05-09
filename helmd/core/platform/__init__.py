import platform

from helmd.core.platform.base import Platform


def get_platform() -> Platform:
    system = platform.system()
    if system == "Darwin":
        from helmd.core.platform.mac import MacPlatform
        return MacPlatform()
    if system == "Linux":
        from helmd.core.platform.linux import LinuxPlatform
        return LinuxPlatform()
    raise RuntimeError(f"Unsupported platform: {system}")
