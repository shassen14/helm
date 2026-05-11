import uvicorn
from fastapi import FastAPI

from mixd.python.routes import channels, devices, routing, status
from mixd.python.state import MixerState


def create_app(mixer: MixerState) -> FastAPI:
    app = FastAPI(title="mixd")
    app.state.mixer = mixer
    app.include_router(status.router)
    app.include_router(devices.router)
    app.include_router(channels.router)
    app.include_router(routing.router)
    return app


def serve(mixer: MixerState, host: str = "127.0.0.1", port: int = 7101) -> None:
    uvicorn.run(create_app(mixer), host=host, port=port, log_level="warning")
