from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from mixd.python.constants import MixOutput
from mixd.python.state import BusState

router = APIRouter()

_VALID_BUSES = {o.value for o in MixOutput}


class BusBody(BaseModel):
    volume: float | None = None
    device_name: str | None = None

    @field_validator("volume")
    @classmethod
    def _validate_volume(cls, v: float | None) -> float | None:
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("volume must be between 0.0 and 1.0")
        return v


def _serialize(name: str, bus: BusState) -> dict:
    return {"bus": name, "volume": bus.volume, "device_name": bus.device_name}


@router.get("/outputs")
async def get_outputs(request: Request) -> dict:
    mixer = request.app.state.mixer
    return {name: _serialize(name, bus) for name, bus in mixer.buses.items()}


@router.put("/outputs/{bus}")
async def set_output(bus: str, body: BusBody, request: Request) -> dict:
    if bus not in _VALID_BUSES:
        raise HTTPException(status_code=404, detail=f"unknown bus: {bus}")
    mixer = request.app.state.mixer
    engine = request.app.state.engine
    state = mixer.buses.setdefault(bus, BusState())

    if body.volume is not None:
        state.volume = body.volume
        engine.set_bus_volume(bus, body.volume)
    if body.device_name is not None:
        state.device_name = body.device_name or None
        if not engine.open_bus(bus, state.device_name):
            raise HTTPException(status_code=502, detail="failed to open output device")

    request.app.state.persist()
    return _serialize(bus, state)


@router.get("/output-devices")
async def list_output_devices(request: Request) -> list[str]:
    return request.app.state.engine.list_output_devices()
