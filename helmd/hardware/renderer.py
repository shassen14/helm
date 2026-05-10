from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_log = logging.getLogger(__name__)

_SYSTEM_FONTS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

_ICON_PADDING: int = 10
_TEXT_BOTTOM_MARGIN: int = 4
_TEXT_COLOR: tuple[int, int, int] = (255, 255, 255)
_TEXT_SHADOW_COLOR: tuple[int, int, int] = (0, 0, 0)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _SYSTEM_FONTS:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()


def render_key(
    label: str,
    icon_path: Path | None,
    color: tuple[int, int, int],
    size: tuple[int, int],
    font_size: int = 14,
) -> Image.Image:
    img = Image.new("RGB", size, color)

    if icon_path is not None:
        if icon_path.exists():
            try:
                icon = Image.open(icon_path).convert("RGBA")
                icon_size = (size[0] - _ICON_PADDING, size[1] - _ICON_PADDING)
                icon = icon.resize(icon_size, Image.LANCZOS)
                x = (size[0] - icon_size[0]) // 2
                y = (size[1] - icon_size[1]) // 2
                img.paste(icon, (x, y), mask=icon.split()[3] if icon.mode == "RGBA" else None)
            except Exception as exc:
                _log.warning("Failed to load icon %s: %s", icon_path, exc)
        else:
            _log.warning("Icon not found: %s", icon_path)

    if label:
        draw = ImageDraw.Draw(img)
        font = _load_font(font_size)
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (size[0] - text_w) // 2
        y = size[1] - text_h - _TEXT_BOTTOM_MARGIN
        draw.text((x + 1, y + 1), label, font=font, fill=_TEXT_SHADOW_COLOR)
        draw.text((x, y), label, font=font, fill=_TEXT_COLOR)

    return img
