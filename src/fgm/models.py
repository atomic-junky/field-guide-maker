import dataclasses
from dataclasses import dataclass, field
import json
import math
from typing import Tuple


RGBA = tuple[int, int, int, int]

@dataclass
class SafeZone:
    name: str
    text: str | None
    scale: Tuple[float, float] | float
    color: RGBA
    border_width: int
    alignement: str = "o"

    def get_rect(self, size: tuple[int, int], canvas_size: tuple[int, int]) -> tuple[int, int, int, int]:
        cw, ch = canvas_size
        width, height = size
        scale_x, scale_y = (self.scale, self.scale) if isinstance(self.scale, float) else self.scale
        sw = int(width * scale_x)
        sh = int(height * scale_y)
        return (cw - sw) // 2, (ch - sh) // 2, sw, sh


@dataclass
class Settings:
    width: int = 1920
    height: int = 1080
    _safe_margin_input: int = 15
    absolute_margin: bool = False
    display_cross: bool = True
    display_action_safe: bool = True
    display_title_safe: bool = True
    display_overscan: bool = True

    _action_safe_scale_input: int = 90
    _title_safe_scale_input: int = 80

    action_border_color: str = "#00ffff"
    title_border_color: str = "#00ffff"
    border_color: str = "#0000ff"
    overscan_border_color: str = "#ff00ff"
    cross_color: str = "#00ff00"
    
    @property
    def safe_margin(self) -> float:
        return self._safe_margin_input / 100
    
    @property
    def action_safe_scale(self) -> float:
        return self._action_safe_scale_input / 100
    
    @property
    def title_safe_scale(self) -> float:
        return self._title_safe_scale_input / 100

    @property
    def ratio(self) -> int:
        return math.gcd(self.width, self.height)
    
    @property
    def inner_size(self) -> tuple[int, int]:
        return self.width, self.height

    @property
    def inner_origin(self) -> tuple[int, int]:
        cw, ch = self.canvas_size
        return (cw - self.width) // 2, (ch - self.height) // 2
    
    @property
    def outer_ratio(self) -> int:
        return math.gcd(*self.canvas_size)
    
    @property
    def outer_margin(self) -> tuple[int, int]:
        if self.absolute_margin:
            margin = (max(self.width, self.height) * self.safe_margin)

            return (margin, margin)

        return (self.width * (self.safe_margin),
                self.height * (self.safe_margin))

    @property
    def canvas_size(self) -> tuple[int, int]:
        margin: tuple = self.outer_margin
        print(margin)
        
        return (int(self.width + margin[0]),
                int(self.height + margin[1]))
    
    @property
    def safe_zones(self) -> list[SafeZone]:
        safe_zones: list[SafeZone] = []
        
        if self.display_title_safe:
            safe_zones.append(
                SafeZone(
                    name="title_safe",
                    text="title",
                    scale=self.title_safe_scale,
                    color=(0, 255, 255, 255),
                    border_width=2,
                )
            )

        if self.display_action_safe:
            safe_zones.append(
                SafeZone(
                    name="action_safe",
                    text="action",
                    scale=self.action_safe_scale,
                    color=(0, 255, 255, 255),
                    border_width=2,
                )
            )

        safe_zones.append(
            SafeZone(
                name="frame",
                text=f"{self.width} x {self.height} ({int(self.width/self.ratio)}:{int(self.height/self.ratio)})",
                scale=1.0,
                color=(0, 0, 255, 255),
                border_width=3,
            )
        )

        if self.display_overscan:
            cw, ch = self.canvas_size
            overscan_scale: Tuple[float, float] = (cw / self.width, ch / self.height)
            safe_zones.append(
                SafeZone(
                    name="overscan",
                    text=f"{cw} x {ch} OVERSCAN",
                    scale=overscan_scale,
                    color=(255, 0, 255, 255),
                    border_width=2,
                    alignement="i",
                )
            )
        
        return safe_zones

    def reset(self) -> None:
        for key, value in dataclasses.asdict(self).items():
            setattr(self, key, value)

    def from_json(cls, data: dict) -> 'Settings':
        return Settings(**json.loads(data))

    def to_json(self) -> dict:
        return json.dumps(dataclasses.asdict(self))