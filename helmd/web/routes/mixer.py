from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter(prefix="/mixer")

_TIMEOUT_S = 3.0


async def _proxy(
    request: Request,
    method: str,
    path: str,
    json: Any = None,
) -> Response:
    base = request.app.state.mixd_base_url
    url = f"{base}{path}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.request(method, url, json=json)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"mixd unreachable: {exc}") from exc
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


@router.get("/channels")
async def get_channels(request: Request) -> Response:
    return await _proxy(request, "GET", "/channels")


@router.post("/channels/{channel}/level")
async def set_level(channel: str, request: Request) -> Response:
    body = await request.json()
    return await _proxy(request, "POST", f"/channels/{channel}/level", json=body)


@router.post("/channels/{channel}/mute")
async def set_mute(channel: str, request: Request) -> Response:
    body = await request.json()
    return await _proxy(request, "POST", f"/channels/{channel}/mute", json=body)


@router.get("/routing")
async def get_routing(request: Request) -> Response:
    return await _proxy(request, "GET", "/routing")


@router.put("/routing/{channel}")
async def set_routing(channel: str, request: Request) -> Response:
    body = await request.json()
    return await _proxy(request, "PUT", f"/routing/{channel}", json=body)


@router.get("/devices")
async def get_devices(request: Request) -> Response:
    return await _proxy(request, "GET", "/devices")


@router.get("/status")
async def get_status(request: Request) -> Response:
    return await _proxy(request, "GET", "/status")
