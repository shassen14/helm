from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def status():
    raise NotImplementedError
