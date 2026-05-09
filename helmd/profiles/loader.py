import tomllib
from pathlib import Path

from helmd.profiles.schema import Button, KnobBinding, Profile, SCHEMA_VERSION


def load_profile(path: Path) -> Profile:
    raw = tomllib.loads(path.read_text())
    version = raw.get("schema_version", 0)
    if version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported profile schema_version {version} (expected {SCHEMA_VERSION})")
    p = raw["profile"]
    return Profile(
        schema_version=version,
        name=p["name"],
        trigger_apps=p.get("trigger_apps", []),
        deck=p.get("deck", "any"),
        buttons=[Button(**b) for b in p.get("buttons", [])],
        knobs=[KnobBinding(**k) for k in p.get("knobs", [])],
    )
