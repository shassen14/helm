"""Mixer state persistence.

Mixer state lives in its own TOML next to `helm.toml` so the static helm
config never gets rewritten by the mixer's runtime mutations. The file is
written atomically on every change and reloaded on startup.
"""

from __future__ import annotations

import logging
import os
import tomllib
from pathlib import Path
from typing import Any

from mixd.python.constants import MAX_CHANNELS, ChannelKind, MixOutput
from mixd.python.state import BusState, ChannelState, MixerState

_log = logging.getLogger(__name__)


def _serialize(mixer: MixerState) -> dict[str, Any]:
    return {
        "channels": [
            {
                "id": ch.id,
                "name": ch.name,
                "kind": ch.kind.value,
                "slot": ch.slot,
                "source_id": ch.source_id or "",
                "level": ch.level,
                "muted": ch.muted,
                "outputs": ch.outputs,
            }
            for ch in mixer.channels.values()
        ],
        "buses": {
            name: {"volume": bus.volume, "device_name": bus.device_name or ""}
            for name, bus in mixer.buses.items()
        },
    }


def _toml_dump(data: dict[str, Any]) -> str:
    """Tiny TOML emitter — limited to the shape we serialize above.

    Pulling in `tomli_w` for two tables and a list-of-tables would be silly;
    tomllib is read-only in the stdlib until 3.13.
    """
    lines: list[str] = []
    buses = data.get("buses", {})
    if buses:
        for name, bus in buses.items():
            lines.append(f"[buses.{name}]")
            lines.append(f'volume = {bus["volume"]}')
            lines.append(f'device_name = "{_escape(bus["device_name"])}"')
            lines.append("")
    for ch in data.get("channels", []):
        lines.append("[[channels]]")
        lines.append(f'id = "{_escape(ch["id"])}"')
        lines.append(f'name = "{_escape(ch["name"])}"')
        lines.append(f'kind = "{ch["kind"]}"')
        lines.append(f'slot = {ch["slot"]}')
        lines.append(f'source_id = "{_escape(ch["source_id"])}"')
        lines.append(f'level = {ch["level"]}')
        lines.append(f'muted = {"true" if ch["muted"] else "false"}')
        outs = ", ".join(f'"{_escape(o)}"' for o in ch["outputs"])
        lines.append(f"outputs = [{outs}]")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def save(mixer: MixerState, path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(_toml_dump(_serialize(mixer)))
        os.replace(tmp, path)
    except OSError as exc:
        _log.warning("failed to persist mixer state to %s: %s", path, exc)


def load(path: Path) -> MixerState:
    state = MixerState()
    if not path.exists():
        return state
    try:
        raw = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("failed to read mixer state %s: %s", path, exc)
        return state

    valid_outputs = {o.value for o in MixOutput}
    used_slots: set[int] = set()
    for entry in raw.get("channels", []):
        try:
            slot = int(entry["slot"])
            if slot < 0 or slot >= MAX_CHANNELS or slot in used_slots:
                continue
            outputs = [o for o in entry.get("outputs", []) if o in valid_outputs]
            ch = ChannelState(
                id=str(entry["id"]),
                name=str(entry["name"]),
                kind=ChannelKind(entry["kind"]),
                slot=slot,
                source_id=str(entry.get("source_id") or "") or None,
                level=float(entry.get("level", 1.0)),
                muted=bool(entry.get("muted", False)),
                outputs=outputs,
            )
        except (KeyError, ValueError) as exc:
            _log.warning("skipping malformed channel entry %r: %s", entry, exc)
            continue
        state.channels[ch.id] = ch
        used_slots.add(slot)

    for name, bus in raw.get("buses", {}).items():
        if name not in valid_outputs:
            continue
        state.buses[name] = BusState(
            volume=float(bus.get("volume", 1.0)),
            device_name=str(bus.get("device_name") or "") or None,
        )
    return state
