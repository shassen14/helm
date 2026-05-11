from __future__ import annotations

import json
import logging
import platform
import subprocess
from dataclasses import dataclass

_log = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    name: str
    uid: str
    direction: str  # "input" or "output"


def _list_devices_macos() -> list[AudioDevice]:
    raw = subprocess.check_output(
        ["system_profiler", "SPAudioDataType", "-json"],
        stderr=subprocess.DEVNULL,
    )
    data = json.loads(raw)
    devices: list[AudioDevice] = []
    for section in data.get("SPAudioDataType", []):
        for item in section.get("_items", []):
            name = item.get("_name", "")
            uid = item.get("coreaudio_device_uid", name)
            has_in = item.get("coreaudio_input_source") or item.get("coreaudio_default_audio_input_device")
            has_out = item.get("coreaudio_output_source") or item.get("coreaudio_default_audio_output_device")
            if has_in:
                devices.append(AudioDevice(name=name, uid=uid, direction="input"))
            if has_out:
                devices.append(AudioDevice(name=name, uid=uid, direction="output"))
            if not has_in and not has_out:
                devices.append(AudioDevice(name=name, uid=uid, direction="output"))
    return devices


def _list_devices_linux() -> list[AudioDevice]:
    devices: list[AudioDevice] = []
    for direction, cmd in (("output", ["pactl", "--format=json", "list", "sinks"]),
                           ("input", ["pactl", "--format=json", "list", "sources"])):
        raw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        for item in json.loads(raw):
            name = item.get("description", item.get("name", ""))
            uid = item.get("name", name)
            devices.append(AudioDevice(name=name, uid=uid, direction=direction))
    return devices


def list_devices() -> list[AudioDevice]:
    try:
        system = platform.system()
        if system == "Darwin":
            return _list_devices_macos()
        if system == "Linux":
            return _list_devices_linux()
        _log.warning("audio device enumeration not supported on %s", system)
        return []
    except Exception as exc:
        _log.warning("failed to enumerate audio devices: %s", exc)
        return []
