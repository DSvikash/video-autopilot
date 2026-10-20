import os
import logging
from typing import Optional, List
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

class ThumbnailGenerator:
    """
    Renders 1280x720 high-CTR YouTube Thumbnails
    modeled on top tech creators (Vaibhav Sisinty, Fireship, Matt Wolfe).
    Features high-contrast typography, glowing neon tech badges, and vivid color accents.
    """
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("output/thumbnails")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = 1280
        self.height = 720

    def generate_thumbnail(
        self,
        topic: str,
        highlight_badge: str = "WE TESTED IT!",
        secondary_badge: str = "+10 AI UPDATES",
        output_filename: str = "thumbnail.jpg"
    ) -> str:
        out_path = self.output_dir / output_filename
        
        # 1. Dark tech canvas with intense ambient glow
        img = Image.new("RGB", (self.width, self.height), (11, 15, 28))
        
        # Radial neon glows
        glow = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        # Cyan glow top-left
        glow_draw.ellipse([-100, -100, 600, 600], fill=(0, 210, 255, 60))
        # Purple/Indigo glow bottom-right
        glow_draw.ellipse([self.width - 600, self.height - 500, self.width + 100, self.height + 100], fill=(147, 51, 234, 50))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=80))
        img.paste(glow, (0, 0), glow)
        
        draw = ImageDraw.Draw(img)

        # 2. Tech grid overlay lines
        for x in range(0, self.width, 80):
            draw.line([(x, 0), (x, self.height)], fill=(20, 28, 48), width=1)
        for y in range(0, self.height, 80):
            draw.line([(0, y), (self.width, y)], fill=(20, 28, 48), width=1)

        # 3. Top Eyebrow Badge (Neon Cyan)
        eyebrow = "● EXCLUSIVE DEEP DIVE"
        draw.rounded_rectangle([70, 60, 420, 115], radius=24, fill=(15, 23, 42), outline=(0, 210, 255), width=2)
        draw.text((100, 75), eyebrow, fill=(0, 229, 255))

        # 4. Giant Main Headline (High Contrast White / Yellow)
        # Split topic into 2 punchy lines
        words = topic.upper().split()
        if len(words) > 3:
            line1 = " ".join(words[:3])
            line2 = " ".join(words[3:7])
        else:
            line1 = topic.upper()
            line2 = "IS FINALLY HERE!"

        # Draw main title text with heavy dark shadow for maximum legibility
        def draw_shadowed_text(pos, text, fill_color):
            x, y = pos
            # Shadow
            for ox in [-4, 0, 4]:
                for oy in [-4, 0, 4]:
                    draw.text((x + ox, y + oy), text, fill=(0, 0, 0))
            draw.text((x, y), text, fill=fill_color)

        draw_shadowed_text((70, 160), line1[:24], (255, 255, 255))
        draw_shadowed_text((70, 270), line2[:24], (255, 212, 0))  # Vivid Yellow

        # 5. Right-Hand Floating Power Badges
        # Badge 1: Glowing Red / Orange "WE TESTED IT!"
        b1_x = self.width - 450
        draw.rounded_rectangle([b1_x, 150, self.width - 60, 270], radius=20, fill=(220, 38, 38), outline=(254, 202, 202), width=3)
        draw.text((b1_x + 35, 190), highlight_badge.upper()[:16], fill=(255, 255, 255))

        # Badge 2: Golden Yellow "+10 AI UPDATES"
        draw.rounded_rectangle([b1_x, 310, self.width - 60, 430], radius=20, fill=(234, 179, 8), outline=(254, 240, 138), width=3)
        draw.text((b1_x + 30, 350), secondary_badge.upper()[:18], fill=(0, 0, 0))

        # Badge 3: Cyan Benchmark Badge
        draw.rounded_rectangle([b1_x, 470, self.width - 60, 590], radius=20, fill=(15, 23, 42), outline=(56, 189, 248), width=2)
        draw.text((b1_x + 40, 500), "VERIFIED DATA", fill=(56, 189, 248))
        draw.text((b1_x + 40, 535), "1M TOKENS | 92.4%", fill=(255, 255, 255))

        # 6. Bottom Highlight Bar
        draw.rounded_rectangle([70, 580, 720, 650], radius=16, fill=(30, 41, 59), outline=(71, 85, 105), width=1)
        draw.text((100, 602), "FULL ARCHITECTURAL BREAKDOWN & BENCHMARKS", fill=(203, 213, 225))

        # Outer high-voltage border
        draw.rectangle([0, 0, self.width - 1, self.height - 1], outline=(59, 130, 246), width=4)

        img.save(out_path, format="JPEG", quality=95)
        logger.info(f"Generated high-CTR YouTube thumbnail: {out_path}")
        return str(out_path)
