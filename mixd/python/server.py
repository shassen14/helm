import uvicorn
from fastapi import FastAPI

app = FastAPI(title="mixd")


def serve(host: str = "127.0.0.1", port: int = 7101) -> None:
    uvicorn.run(app, host=host, port=port)
