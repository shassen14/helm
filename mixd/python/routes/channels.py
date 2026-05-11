from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

router = APIRouter()


class LevelBody(BaseModel):
    level: float

    @field_validator("level")
    @classmethod
    def _validate_level(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("level must be between 0.0 and 1.0")
        return v


class MuteBody(BaseModel):
    muted: bool


@router.get("/channels")
async def get_channels(request: Request) -> dict:
    mixer = request.app.state.mixer
    return {
        name: {"level": ch.level, "muted": ch.muted, "outputs": ch.outputs}
        for name, ch in mixer.channels.items()
    }


@router.post("/channels/{channel}/level")
async def set_level(channel: str, body: LevelBody, request: Request) -> dict:
    mixer = request.app.state.mixer
    if channel not in mixer.channels:
        raise HTTPException(status_code=404, detail=f"unknown channel: {channel}")
    mixer.channels[channel].level = body.level
    ch = mixer.channels[channel]
    return {"name": channel, "level": ch.level, "muted": ch.muted, "outputs": ch.outputs}


@router.post("/channels/{channel}/mute")
async def set_mute(channel: str, body: MuteBody, request: Request) -> dict:
    mixer = request.app.state.mixer
    if channel not in mixer.channels:
        raise HTTPException(status_code=404, detail=f"unknown channel: {channel}")
    mixer.channels[channel].muted = body.muted
    ch = mixer.channels[channel]
    return {"name": channel, "level": ch.level, "muted": ch.muted, "outputs": ch.outputs}
