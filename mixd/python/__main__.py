import asyncio
import logging
import threading
from pathlib import Path

from mixd.python.config import load_config
from mixd.python.devices import list_devices
from mixd.python.engine import MixEngine
from mixd.python.server import serve
from mixd.python.state import default_state

_log = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent.parent / "helm.toml"


async def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = load_config(_CONFIG_PATH)

    mixer = default_state()
    mixer.devices = list_devices()

    engine = MixEngine()
    engine.sync_state(mixer)

    _log.info("mixd listening on %s:%d", settings.host, settings.port)

    threading.Thread(
        target=serve,
        args=(mixer, engine),
        kwargs={"host": settings.host, "port": settings.port},
        daemon=True,
    ).start()

    try:
        await asyncio.Event().wait()
    finally:
        engine.close()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
