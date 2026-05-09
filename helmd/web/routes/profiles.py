from fastapi import APIRouter

router = APIRouter(prefix="/profiles")


@router.get("")
async def list_profiles():
    raise NotImplementedError


@router.post("")
async def create_profile():
    raise NotImplementedError
