"""Locate and invoke the platform capture helper (e.g. `mixd-capture-darwin`).

The Rust audio core knows how to find and spawn the helper for streaming PCM.
Python only needs to invoke its `list-apps` subcommand to enumerate capturable
applications for the UI — so this module deliberately mirrors a small subset of
the Rust resolver in `backends/wire.rs`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
from pathlib import Path

_log = logging.getLogger(__name__)

ENV_OVERRIDE = "MIXD_CAPTURE_HELPER"
LIST_APPS_SUBCOMMAND = "list-apps"
LIST_APPS_TIMEOUT_S = 5.0

_REPO_ROOT = Path(__file__).resolve().parent.parent

_HELPERS_BY_OS: dict[str, tuple[str, tuple[str, ...]]] = {
    "Darwin": (
        "mixd-capture-darwin",
        (
            "swift/.build/arm64-apple-macosx/release/mixd-capture-darwin",
            "swift/.build/release/mixd-capture-darwin",
            "swift/.build/arm64-apple-macosx/debug/mixd-capture-darwin",
            "swift/.build/debug/mixd-capture-darwin",
        ),
    ),
    "Linux": ("mixd-capture-linux", ()),
    "Windows": ("mixd-capture-windows.exe", ()),
}


def resolve_helper_path() -> Path | None:
    if override := os.environ.get(ENV_OVERRIDE):
        p = Path(override)
        if p.exists():
            return p
    spec = _HELPERS_BY_OS.get(platform.system())
    if not spec:
        return None
    _binary, candidates = spec
    for rel in candidates:
        p = _REPO_ROOT / rel
        if p.exists():
            return p
    return None


async def list_capturable_apps() -> list[dict]:
    helper = resolve_helper_path()
    if helper is None:
        raise FileNotFoundError("capture helper not found; build it first")
    proc = await asyncio.create_subprocess_exec(
        str(helper),
        LIST_APPS_SUBCOMMAND,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=LIST_APPS_TIMEOUT_S
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError("capture helper list-apps timed out")
    if proc.returncode != 0:
        msg = stderr.decode(errors="replace").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"capture helper failed: {msg}")
    apps = json.loads(stdout.decode())
    if not isinstance(apps, list):
        raise RuntimeError("capture helper returned non-list payload")
    return apps
