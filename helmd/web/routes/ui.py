from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    raise NotImplementedError
