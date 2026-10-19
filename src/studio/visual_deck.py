import os
import logging
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from src.studio.models import Slide, Chapter

logger = logging.getLogger(__name__)

class VisualDeckGenerator:
    """
    Renders 1920x1080 broadcast-grade presentation cards,
    feature breakdowns, benchmark comparisons, and chapter title decks
    inspired by top tech creators (Vaibhav Sisinty, Matt Wolfe, Fireship).
    """
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("output/slides")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = 1920
        self.height = 1080

    def generate_slide_image(self, slide: Slide, chapter_title: str, chapter_idx: int, total_chapters: int) -> str:
        out_file = self.output_dir / f"slide_ch{chapter_idx}_{slide.slide_id}.png"
        
        # Base background: Deep sleek tech slate with ambient radial glow
        img = Image.new("RGB", (self.width, self.height), (10, 15, 29))
        draw = ImageDraw.Draw(img)

        # 1. Subtle top-right ambient gradient glow (Cyan/Indigo)
        glow = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse([self.width - 600, -200, self.width + 400, 600], fill=(59, 130, 246, 35))
        glow_draw.ellipse([-200, self.height - 500, 500, self.height + 200], fill=(139, 92, 246, 25))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=80))
        img.paste(glow, (0, 0), glow)
        draw = ImageDraw.Draw(img)

        # 2. Top Header Bar: Category Tag & Chapter Indicator
        # Category pill
        category_text = f"●  {slide.category.upper()}"
        draw.rounded_rectangle([100, 70, 380, 115], radius=20, fill=(30, 41, 59), outline=(59, 130, 246), width=1)
        draw.text((125, 82), category_text, fill=(56, 189, 248))

        # Chapter pill on right
        chapter_pill = f"CHAPTER {chapter_idx:02d}/{total_chapters:02d}: {chapter_title.upper()}"
        draw.text((self.width - 550, 84), chapter_pill, fill=(148, 163, 184))

        # 3. Main Headline & Subheadline
        draw.text((100, 160), slide.headline, fill=(255, 255, 255))
        draw.text((100, 235), slide.subheadline, fill=(148, 163, 184))

        # Divider line
        draw.line([(100, 300), (self.width - 100, 300)], fill=(30, 41, 59), width=2)

        # 4. Content Layout: Left side Bullet Cards + Right side Stat Badge
        has_badge = bool(slide.stat_badge or slide.highlight_metric)
        left_width = 1100 if has_badge else 1720

        # Draw structured feature cards
        y_cursor = 340
        card_h = 110
        gap = 25
        for i, bp in enumerate(slide.bullet_points[:4]):
            card_box = [100, y_cursor, 100 + left_width, y_cursor + card_h]
            # Card background
            draw.rounded_rectangle(card_box, radius=16, fill=(17, 24, 39), outline=(31, 41, 55), width=1)
            
            # Number icon pill
            num_box = [125, y_cursor + 25, 185, y_cursor + 85]
            draw.rounded_rectangle(num_box, radius=12, fill=(30, 58, 138))
            draw.text((148, y_cursor + 45), f"{i+1}", fill=(96, 165, 250))

            # Bullet text
            draw.text((215, y_cursor + 42), bp[:95], fill=(241, 245, 249))
            y_cursor += card_h + gap

        # 5. Right Stat Badge Card (if available)
        if has_badge:
            right_x = 1260
            badge_box = [right_x, 340, self.width - 100, 840]
            # Gradient stat box
            draw.rounded_rectangle(badge_box, radius=24, fill=(15, 23, 42), outline=(59, 130, 246), width=2)
            
            # Badge icon / title
            draw.text((right_x + 50, 400), "KEY SPECIFICATION", fill=(56, 189, 248))
            
            # Metric
            metric = slide.highlight_metric or "1M TOKENS"
            draw.text((right_x + 50, 470), metric, fill=(255, 255, 255))
            
            # Stat description
            badge_desc = slide.stat_badge or "Next-Gen Multi-Modal Reasoning Architecture"
            draw.text((right_x + 50, 580), badge_desc[:70], fill=(148, 163, 184))

            # Verified checkmark badge
            draw.rounded_rectangle([right_x + 50, 680, right_x + 350, 740], radius=12, fill=(16, 185, 129, 40), outline=(16, 185, 129), width=1)
            draw.text((right_x + 75, 700), "✔ VERIFIED BENCHMARK", fill=(52, 211, 153))

        # 6. Bottom Progress Footer
        draw.line([(100, self.height - 90), (self.width - 100, self.height - 90)], fill=(30, 41, 59), width=1)
        draw.text((100, self.height - 65), "AI ARCHITECTURE & WEEKLY TECH DOSSIER", fill=(100, 116, 139))
        draw.text((self.width - 380, self.height - 65), "SUBSCRIBE FOR WEEKLY DEEP DIVES", fill=(59, 130, 246))

        img.save(out_file, quality=95)
        return str(out_file)
