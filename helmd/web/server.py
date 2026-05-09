import uvicorn
from fastapi import FastAPI

from helmd.web.routes import actions, profiles, status, ui

app = FastAPI(title="helmd")
app.include_router(ui.router)
app.include_router(profiles.router)
app.include_router(actions.router)
app.include_router(status.router)


def serve(host: str = "127.0.0.1", port: int = 7100) -> None:
    uvicorn.run(app, host=host, port=port)
