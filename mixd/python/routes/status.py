from fastapi import APIRouter, Request

router = APIRouter()

_VERSION = "0.1.0"


@router.get("/status")
async def get_status(request: Request) -> dict:
    mixer = request.app.state.mixer
    return {
        "version": _VERSION,
        "channel_count": len(mixer.channels),
        "device_count": len(mixer.devices),
    }
