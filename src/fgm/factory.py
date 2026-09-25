"""
PSD layout generator for animation background/layout work.
Produces a layered PSD with safe margin guides (text, image/action, bleed).
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from os import PathLike
from pathlib import Path
from typing import IO

from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage
from psd_tools.api.layers import Layer, PixelLayer, Group
from psd_tools.constants import Compression, Tag
from psd_tools.psd.tagged_blocks import SheetColorType

from .models import Settings, RGBA


def get_asset_path(filename: str) -> Path:
    return Path(__file__).parent / "assets" / filename


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


class FieldGuideFactory:
    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self._psd = PSDImage.new(mode="RGBA", size=self.s.canvas_size, color=1.0)
        self._build()

    def add_layer(self, layer: PixelLayer) -> None:
        self._psd.append(layer)

    def save(self, fp: IO[bytes] | str | bytes | PathLike) -> None:
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
        cw, ch = self.s.canvas_size
        self._psd.append(
            self._pixel_layer(
                ImageFactory.solid((cw, ch), (255, 255, 255, 255)),
                "00+background",
                top=0,
                left=0,
            )
        )

    def _add_frame_group(self) -> None:
        cw, ch = self.s.canvas_size
        inner_left, inner_top = self.s.inner_origin
        iw, ih = self.s.inner_size

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

        if self.s.display_cross:
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
        for zone in self.s.safe_zones:
            sz_group: Group = Group.new(
                parent=border_group, name=zone.name, open_folder=False
            )

            zl, zt, zw, zh = zone.get_rect(self.s.inner_size, self.s.canvas_size)
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
    return ImageFont.truetype(
        get_asset_path("lato.black.ttf"), size=size, encoding="unic"
    )
