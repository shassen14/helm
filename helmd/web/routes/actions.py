from fastapi import APIRouter

router = APIRouter(prefix="/actions")


@router.post("/fire")
async def fire_action():
    raise NotImplementedError
