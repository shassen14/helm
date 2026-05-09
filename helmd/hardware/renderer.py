from pathlib import Path


def render_key(label: str, icon_path: Path | None = None, color: tuple[int, int, int] = (0, 0, 0)) -> bytes:
    raise NotImplementedError
