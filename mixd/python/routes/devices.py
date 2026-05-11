from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/devices")
async def get_devices(request: Request) -> list[dict]:
    mixer = request.app.state.mixer
    return [{"name": d.name, "uid": d.uid, "direction": d.direction} for d in mixer.devices]
