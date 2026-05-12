import asyncio
import logging
import threading
from pathlib import Path

from mixd.python import persistence
from mixd.python.config import load_config
from mixd.python.devices import list_devices
from mixd.python.engine import MixEngine
from mixd.python.server import serve

_log = logging.getLogger(__name__)

_HELM_DIR = Path(__file__).parent.parent.parent
_CONFIG_PATH = _HELM_DIR / "helm.toml"
_MIXER_STATE_PATH = _HELM_DIR / "mixer.toml"


async def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = load_config(_CONFIG_PATH)

    mixer = persistence.load(_MIXER_STATE_PATH)
    mixer.devices = list_devices()

    engine = MixEngine()
    engine.sync_state(mixer)

    # Re-spawn any persisted captures so the user picks up exactly where they
    # left off after a restart.
    for ch in mixer.channels.values():
        engine.start_capture(ch.slot, ch.kind, ch.source_id)

    def persist() -> None:
        persistence.save(mixer, _MIXER_STATE_PATH)

    _log.info("mixd listening on %s:%d", settings.host, settings.port)

    threading.Thread(
        target=serve,
        args=(mixer, engine, persist),
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
