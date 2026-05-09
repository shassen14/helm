from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/profiles")


@router.get("")
async def list_profiles(request: Request) -> dict:
    manager = request.app.state.manager
    return {"profiles": list(manager.profiles.keys())}


@router.get("/{name}")
async def get_profile(name: str, request: Request) -> dict:
    manager = request.app.state.manager
    profile = manager.profiles.get(name)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")
    return asdict(profile)


@router.post("/active")
async def set_active_profile(body: dict, request: Request) -> dict:
    name = body.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="'name' is required")
    manager = request.app.state.manager
    if not manager.swap_by_name(name):
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")
    return {"ok": True, "active_profile": name}
