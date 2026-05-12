from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from mixd.python.constants import ChannelKind
from mixd.python.state import ChannelState

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


class CreateChannelBody(BaseModel):
    kind: ChannelKind
    id: str | None = None
    name: str | None = None
    bundle_id: str | None = None
    outputs: list[str] = []


def _serialize(ch: ChannelState) -> dict:
    return {
        "id": ch.id,
        "name": ch.name,
        "kind": ch.kind.value,
        "slot": ch.slot,
        "source_id": ch.source_id,
        "level": ch.level,
        "muted": ch.muted,
        "outputs": ch.outputs,
    }


@router.get("/channels")
async def get_channels(request: Request) -> dict:
    mixer = request.app.state.mixer
    return {cid: _serialize(ch) for cid, ch in mixer.channels.items()}


@router.post("/channels")
async def create_channel(body: CreateChannelBody, request: Request) -> dict:
    mixer = request.app.state.mixer
    engine = request.app.state.engine

    match body.kind:
        case ChannelKind.APP:
            if not body.bundle_id:
                raise HTTPException(status_code=422, detail="bundle_id required for app channel")
            cid = body.id or body.bundle_id
            source_id = body.bundle_id
            default_name = body.bundle_id
        case ChannelKind.MIC:
            cid = body.id or "mic"
            source_id = None
            default_name = "Mic"
        case ChannelKind.SYSTEM:
            cid = body.id or "system"
            source_id = None
            default_name = "System"
        case _:
            raise HTTPException(status_code=422, detail=f"unknown kind: {body.kind}")

    if cid in mixer.channels:
        raise HTTPException(status_code=409, detail=f"channel exists: {cid}")

    slot = mixer.allocate_slot()
    if slot is None:
        raise HTTPException(status_code=507, detail="no free channel slots")

    ch = ChannelState(
        id=cid,
        name=body.name or default_name,
        kind=body.kind,
        slot=slot,
        source_id=source_id,
        outputs=body.outputs,
    )
    mixer.channels[cid] = ch

    engine.set_level(slot, ch.level)
    engine.set_muted(slot, ch.muted)
    engine.set_outputs(slot, ch.outputs)
    if not engine.start_capture(slot, ch.kind, ch.source_id):
        del mixer.channels[cid]
        raise HTTPException(status_code=502, detail="failed to start capture")

    request.app.state.persist()
    return _serialize(ch)


@router.delete("/channels/{channel}")
async def delete_channel(channel: str, request: Request) -> dict:
    mixer = request.app.state.mixer
    ch = mixer.channels.get(channel)
    if ch is None:
        raise HTTPException(status_code=404, detail=f"unknown channel: {channel}")
    request.app.state.engine.stop_capture(ch.slot)
    del mixer.channels[channel]
    request.app.state.persist()
    return {"id": channel, "removed": True}


@router.post("/channels/{channel}/level")
async def set_level(channel: str, body: LevelBody, request: Request) -> dict:
    mixer = request.app.state.mixer
    ch = mixer.channels.get(channel)
    if ch is None:
        raise HTTPException(status_code=404, detail=f"unknown channel: {channel}")
    ch.level = body.level
    request.app.state.engine.set_level(ch.slot, body.level)
    request.app.state.persist()
    return _serialize(ch)


@router.post("/channels/{channel}/mute")
async def set_mute(channel: str, body: MuteBody, request: Request) -> dict:
    mixer = request.app.state.mixer
    ch = mixer.channels.get(channel)
    if ch is None:
        raise HTTPException(status_code=404, detail=f"unknown channel: {channel}")
    ch.muted = body.muted
    request.app.state.engine.set_muted(ch.slot, body.muted)
    request.app.state.persist()
    return _serialize(ch)
