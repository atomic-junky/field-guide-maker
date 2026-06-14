"""
PSD layout generator for animation background/layout work.
Produces a layered PSD with safe margin guides (text, image/action, bleed).
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from os import PathLike
from pathlib import Path
from typing import IO, Callable, Tuple

from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage
from psd_tools.api.layers import Layer, PixelLayer, Group
from psd_tools.constants import Compression, Tag
from psd_tools.psd.tagged_blocks import SheetColorType

RGBA = tuple[int, int, int, int]


def get_asset_path(filename: str) -> Path:
    return Path(__file__).parent / "assets" / filename


@dataclass
class SafeZone:
    name: str
    text: str | None
    scale: Tuple[float, float] | float
    color: RGBA
    border_width: int
    alignement: str = "o"


@dataclass
class FGMConfig:
    width: int
    height: int
    safe_margin: float
    absolute_margin: bool = False
    draw_cross: bool = True
    action_border: bool = True
    title_border: bool = True
    overscan_border: bool = True

    def __post_init__(self) -> None:
        self._safe_zones: list[SafeZone] = []

        if self.title_border:
            self._safe_zones.append(
                SafeZone(
                    name="title_safe",
                    text="title",
                    scale=0.8,
                    color=(0, 255, 255, 255),
                    border_width=2,
                )
            )

        if self.action_border:
            self._safe_zones.append(
                SafeZone(
                    name="action_safe",
                    text="action",
                    scale=0.9,
                    color=(0, 255, 255, 255),
                    border_width=2,
                )
            )

        self._safe_zones.append(
            SafeZone(
                name="frame",
                text=f"{self.width} x {self.height} ({int(self.width/self.ratio)}:{int(self.height/self.ratio)})",
                scale=1.0,
                color=(0, 0, 255, 255),
                border_width=3,
            )
        )

        if self.overscan_border:
            cw, ch = self.canvas_size
            overscan_scale: Tuple[float, float] = (cw / self.width, ch / self.height)
            self._safe_zones.append(
                SafeZone(
                    name="overscan",
                    text=f"{cw} x {ch} OVERSCAN",
                    scale=overscan_scale,
                    color=(255, 0, 255, 255),
                    border_width=2,
                    alignement="i",
                )
            )

    @property
    def ratio(self) -> int:
        return math.gcd(self.width, self.height)

    @property
    def canvas_size(self) -> tuple[int, int]:
        if self.absolute_margin:
            margin_px = max(self.width, self.height) * self.safe_margin / 2
            return int(self.width + 2 * margin_px), int(self.height + 2 * margin_px)
        else:
            total_scale = 1.0 + self.safe_margin
            return int(self.width * total_scale), int(self.height * total_scale)

    @property
    def inner_size(self) -> tuple[int, int]:
        return self.width, self.height

    def inner_origin(self) -> tuple[int, int]:
        cw, ch = self.canvas_size
        return (cw - self.width) // 2, (ch - self.height) // 2

    def safe_zone_rect(
        self, scale: Tuple[float, float] | float
    ) -> tuple[int, int, int, int]:
        cw, ch = self.canvas_size
        scale_x, scale_y = (scale, scale) if isinstance(scale, float) else scale
        sw = int(self.width * scale_x)
        sh = int(self.height * scale_y)
        return (cw - sw) // 2, (ch - sh) // 2, sw, sh


class ImageFactory:
    @staticmethod
    def solid(size: tuple[int, int], color: RGBA) -> Image.Image:
        return Image.new("RGBA", size, color)

    @staticmethod
    def border(width: int, height: int, color: RGBA, thickness: int) -> Image.Image:
        outer_w = width + thickness * 2
        outer_h = height + thickness * 2
        im = Image.new("RGBA", (outer_w, outer_h), color)
        ImageDraw.Draw(im).rectangle(
            [(thickness, thickness), (thickness + width - 1, thickness + height - 1)],
            fill=(0, 0, 0, 0),
        )
        return im

    @staticmethod
    def diagonals(width: int, height: int, color: RGBA, thickness: int) -> Image.Image:
        im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        draw.line((0, 0, width - 1, height - 1), fill=color, width=thickness)
        draw.line((width - 1, 0, 0, height - 1), fill=color, width=thickness)
        return im

    @staticmethod
    def text(text: str, color: RGBA, size: int = 16) -> Image.Image:
        font = _load_default_font(size=size)
        x, y, w, h = font.getbbox(text)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), text, font=font, fill=color)
        return im

    @staticmethod
    def cover_with_hole(
        canvas_w: int,
        canvas_h: int,
        hole_w: int,
        hole_h: int,
        hole_left: int,
        hole_top: int,
        color: RGBA,
    ) -> Image.Image:
        im = Image.new("RGBA", (canvas_w, canvas_h), color)
        ImageDraw.Draw(im).rectangle(
            [(hole_left, hole_top), (hole_left + hole_w - 1, hole_top + hole_h - 1)],
            fill=(0, 0, 0, 0),
        )
        return im


class FGMFactory:
    def __init__(self, config: FGMConfig) -> None:
        self.config = config
        self._psd = PSDImage.new(mode="RGBA", size=config.canvas_size, color=1.0)
        self._build()

    def add_layer(self, layer: PixelLayer) -> None:
        self._psd.append(layer)

    def save(self, fp: IO[bytes] | str | bytes | PathLike) -> None:
        self.log(f"Saving")
        self._psd.save(fp)

    def _build(self) -> None:
        self._add_background()
        self._add_frame_group()

    def _pixel_layer(
        self,
        image: Image.Image,
        name: str,
        top: int,
        left: int,
        opacity: int = 255,
    ) -> PixelLayer:
        layer = PixelLayer.frompil(image, self._psd, name, top, left, Compression.RLE)
        layer.opacity = opacity
        return layer

    def _add_background(self) -> None:
        cw, ch = self.config.canvas_size
        self._psd.append(
            self._pixel_layer(
                ImageFactory.solid((cw, ch), (255, 255, 255, 255)),
                "00+background",
                top=0,
                left=0,
            )
        )

    def _add_frame_group(self) -> None:
        cfg = self.config
        cw, ch = cfg.canvas_size
        inner_left, inner_top = cfg.inner_origin()
        iw, ih = cfg.inner_size

        group: Group = Group.new(self._psd, "99+field guide", open_folder=False)
        group.tagged_blocks.set_data(Tag.SHEET_COLOR_SETTING, SheetColorType.RED)

        layers: list[Layer] = []
        layers.append(
            self._pixel_layer(
                ImageFactory.cover_with_hole(
                    cw, ch, iw, ih, inner_left, inner_top, (0, 0, 0, 255)
                ),
                "cover",
                top=0,
                left=0,
                opacity=int(255 * 0.75),
            )
        )

        if cfg.draw_cross:
            layers.append(
                self._pixel_layer(
                    ImageFactory.diagonals(iw, ih, (0, 0, 255, 255), thickness=1),
                    "cross",
                    top=inner_top,
                    left=inner_left,
                    opacity=int(255 * 0.5),
                )
            )

        group.extend(layers)

        border_group: Group = Group.new(parent=group, name="borders", open_folder=False)
        for zone in cfg._safe_zones:
            sz_group: Group = Group.new(
                parent=border_group, name=zone.name, open_folder=False
            )

            zl, zt, zw, zh = cfg.safe_zone_rect(zone.scale)
            bw = zone.border_width

            if zone.alignement == "i":
                zl += bw
                zt += bw
                zw -= bw * 2
                zh -= bw * 2
            elif zone.alignement == "c":
                zl += bw // 2
                zt += bw // 2
                zw -= bw
                zh -= bw

            sz_group.extend(
                [
                    self._pixel_layer(
                        ImageFactory.border(zw, zh, zone.color, bw),
                        zone.name,
                        top=zt - bw,
                        left=zl - bw,
                    ),
                    self._pixel_layer(
                        ImageFactory.text(zone.text, zone.color),
                        zone.name + "_text",
                        top=(zt - bw) + (bw + 4),
                        left=(zl - bw) + (bw + 4),
                    ),
                ]
            )


def _load_default_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(get_asset_path("arial.ttf"), size=size, encoding="unic")
