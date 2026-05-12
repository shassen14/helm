import asyncio
import threading
from pathlib import Path
from types import SimpleNamespace

from helmd.actions.keypress import KeypressAction
from helmd.core.config import load_config
from helmd.core.logger import setup_logging
from helmd.core.paths import HelmPaths
from helmd.core.platform import get_platform
from helmd.hardware.supervisor import SurfaceManager
from helmd.profiles.manager import ProfileManager
from helmd.profiles.switcher import ProfileSwitcher
from helmd.web.server import serve

_CONFIG_PATH = Path(__file__).parent.parent / "helm.toml"
_VERSION = "0.1.0"


async def _main() -> None:
    setup_logging()
    settings = load_config(_CONFIG_PATH)
    paths = HelmPaths.resolve()
    plat = get_platform()
    KeypressAction.set_platform(plat)

    manager = ProfileManager()
    manager.discover(paths)

    surface_manager = SurfaceManager(
        manager=manager,
        devices_config=settings.devices,
        brightness=settings.helmd.brightness,
    )

    mixd_base_url = f"http://{settings.mixd.host}:{settings.mixd.port}"

    state = SimpleNamespace(
        manager=manager,
        platform=plat,
        version=_VERSION,
        surface_manager=surface_manager,
        mixd_base_url=mixd_base_url,
    )

    threading.Thread(
        target=serve,
        args=(state,),
        kwargs={"host": settings.helmd.host, "port": settings.helmd.port},
        daemon=True,
    ).start()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(surface_manager.run())
        if settings.switcher.enabled:
            tg.create_task(ProfileSwitcher(plat, manager, settings.switcher.poll_interval_s).run())
        else:
            tg.create_task(asyncio.Event().wait())


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
