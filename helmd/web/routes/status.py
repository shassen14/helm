import platform

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/status")
async def get_status(request: Request) -> dict:
    m = request.app.state.manager
    return {
        "version": request.app.state.version,
        "active_profile": m.active.name if m.active else None,
        "connected_decks": [],
        "platform": platform.system().lower(),
    }
