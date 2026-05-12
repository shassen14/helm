from fastapi import APIRouter, HTTPException

from mixd.python.helper import list_capturable_apps

router = APIRouter()


@router.get("/apps")
async def get_apps() -> list[dict]:
    try:
        return await list_capturable_apps()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
