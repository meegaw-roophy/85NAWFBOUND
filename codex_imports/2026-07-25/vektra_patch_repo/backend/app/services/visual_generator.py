"""
Small local visual generator for launch-critical share cards.
Produces a PNG without external services, so birthday cards never fail because
an AI image provider or design API is unavailable.
"""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont


class VisualGenerator:
    def _font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        candidates = [
            "arialbd.ttf" if bold else "arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "arial.ttf",
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "segoeui.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
        return ImageFont.load_default()

    def _centered_text(
        self,
        draw: ImageDraw.ImageDraw,
        box: Tuple[int, int, int, int],
        text: str,
        font: ImageFont.ImageFont,
        fill: Tuple[int, int, int],
        spacing: int = 8,
    ) -> None:
        lines = text.splitlines()
        line_boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
        heights = [bottom - top for _, top, _, bottom in line_boxes]
        total_height = sum(heights) + spacing * max(0, len(lines) - 1)
        x1, y1, x2, y2 = box
        y = y1 + ((y2 - y1) - total_height) / 2

        for line, text_box, height in zip(lines, line_boxes, heights):
            width = text_box[2] - text_box[0]
            x = x1 + ((x2 - x1) - width) / 2
            draw.text((x, y), line, font=font, fill=fill)
            y += height + spacing

    def generate_birthday_image(
        self,
        user_name: str,
        age: int,
        width: int = 1920,
        height: int = 1080,
    ) -> bytes:
        image = Image.new("RGB", (width, height), (10, 10, 15))
        draw = ImageDraw.Draw(image)

        for y in range(height):
            t = y / max(1, height - 1)
            r = int(10 + 32 * t)
            g = int(10 + 12 * t)
            b = int(15 + 42 * t)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        accent = (108, 99, 255)
        pink = (236, 72, 153)
        white = (245, 247, 255)
        muted = (168, 176, 194)
        margin = int(width * 0.055)

        draw.rounded_rectangle(
            (margin, margin, width - margin, height - margin),
            radius=36,
            outline=(58, 64, 86),
            width=3,
        )
        draw.line((margin * 2, height - margin * 2, width - margin * 2, margin * 2), fill=accent, width=6)
        draw.ellipse(
            (width - margin * 2 - 24, margin * 2 - 24, width - margin * 2 + 24, margin * 2 + 24),
            fill=pink,
        )

        brand_font = self._font(42, bold=True)
        title_font = self._font(92, bold=True)
        age_font = self._font(64, bold=True)
        body_font = self._font(34)

        draw.text((margin + 28, margin + 24), "VEKTRA", font=brand_font, fill=accent)
        draw.text((margin + 28, margin + 80), "BIRTHDAY TRAJECTORY CARD", font=self._font(24, bold=True), fill=muted)

        self._centered_text(draw, (margin, int(height * 0.30), width - margin, int(height * 0.56)), user_name, title_font, white)
        self._centered_text(draw, (margin, int(height * 0.55), width - margin, int(height * 0.68)), f"Year {age + 1} begins today", age_font, pink)
        self._centered_text(draw, (margin, int(height * 0.71), width - margin, int(height * 0.84)), "Vector = Magnitude x Direction", body_font, muted)

        output = BytesIO()
        image.save(output, format="PNG", optimize=True)
        return output.getvalue()

    def encode_image_to_base64(self, image_bytes: bytes) -> str:
        return base64.b64encode(image_bytes).decode("ascii")


visual_generator = VisualGenerator()
