from types import SimpleNamespace

import uvicorn
from fastapi import FastAPI

from helmd.web.routes import actions, mixer, profiles, status, ui


def create_app(state: SimpleNamespace) -> FastAPI:
    app = FastAPI(title="helmd")
    app.state.manager = state.manager
    app.state.platform = state.platform
    app.state.version = state.version
    app.state.surface_manager = state.surface_manager
    app.state.mixd_base_url = state.mixd_base_url
    app.include_router(ui.router)
    app.include_router(profiles.router)
    app.include_router(actions.router)
    app.include_router(status.router)
    app.include_router(mixer.router)
    return app


def serve(state: SimpleNamespace, host: str = "127.0.0.1", port: int = 7100) -> None:
    uvicorn.run(create_app(state), host=host, port=port)
