from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from mixd.python.constants import MixOutput

router = APIRouter()

_VALID_OUTPUTS = {o.value for o in MixOutput}


class RoutingBody(BaseModel):
    outputs: list[str]


@router.get("/routing")
async def get_routing(request: Request) -> dict:
    mixer = request.app.state.mixer
    return {name: ch.outputs for name, ch in mixer.channels.items()}


@router.put("/routing/{channel}")
async def set_routing(channel: str, body: RoutingBody, request: Request) -> dict:
    mixer = request.app.state.mixer
    if channel not in mixer.channels:
        raise HTTPException(status_code=404, detail=f"unknown channel: {channel}")
    invalid = [o for o in body.outputs if o not in _VALID_OUTPUTS]
    if invalid:
        raise HTTPException(status_code=422, detail=f"unknown outputs: {invalid}")
    mixer.channels[channel].outputs = body.outputs
    request.app.state.engine.set_outputs(channel, body.outputs)
    return {"channel": channel, "outputs": mixer.channels[channel].outputs}
