from fastapi import APIRouter, HTTPException, Request

from helmd.actions.registry import create_action

router = APIRouter(prefix="/actions")


@router.post("/fire")
async def fire_action(body: dict, request: Request) -> dict:
    try:
        action = create_action(body)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    result = await action.execute()
    return {"ok": result.ok, "detail": result.detail}
