import asyncio
import threading
from pathlib import Path
from types import SimpleNamespace

from helmd.actions.keypress import KeypressAction
from helmd.core.config import load_config
from helmd.core.logger import setup_logging
from helmd.core.paths import HelmPaths
from helmd.core.platform import get_platform
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

    state = SimpleNamespace(manager=manager, platform=plat, version=_VERSION)
    threading.Thread(
        target=serve,
        args=(state,),
        kwargs={"host": settings.helmd.host, "port": settings.helmd.port},
        daemon=True,
    ).start()

    if settings.switcher.enabled:
        await ProfileSwitcher(plat, manager, settings.switcher.poll_interval_s).run()
    else:
        await asyncio.Event().wait()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
