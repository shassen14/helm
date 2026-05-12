from pathlib import Path
from typing import Callable

import uvicorn
from fastapi import FastAPI

from mixd.python.engine import MixEngine
from mixd.python.routes import apps, channels, devices, outputs, routing, status
from mixd.python.state import MixerState


def create_app(
    mixer: MixerState,
    engine: MixEngine,
    persist: Callable[[], None],
) -> FastAPI:
    app = FastAPI(title="mixd")
    app.state.mixer = mixer
    app.state.engine = engine
    app.state.persist = persist
    app.include_router(status.router)
    app.include_router(devices.router)
    app.include_router(channels.router)
    app.include_router(routing.router)
    app.include_router(apps.router)
    app.include_router(outputs.router)
    return app


def serve(
    mixer: MixerState,
    engine: MixEngine,
    persist: Callable[[], None],
    host: str = "127.0.0.1",
    port: int = 7101,
) -> None:
    uvicorn.run(
        create_app(mixer, engine, persist),
        host=host,
        port=port,
        log_level="warning",
    )
