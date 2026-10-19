import os
import math
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from moviepy import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    TextClip,
    ColorClip,
    concatenate_videoclips
)
from config.settings import config
from src.scripting.models import VideoScript, Scene

logger = logging.getLogger(__name__)

class TimelineComposer:
    """
    Hinglish Tech Shorts Director Composer.
    Features:
    - Dynamic Ken Burns camera zooms mapped to shot types (action, reveal, wide, closeup, static, tracking)
    - 2.5s Golden-Yellow Hook Overlay Banner (#FFD400) at top
    - High-retention Roman Hinglish bottom caption overlays
    """
    def __init__(self, is_short: bool = True):
        self.is_short = is_short
        self.width = 1080 if is_short else 1920
        self.height = 1920 if is_short else 1080
        self.fps = 30

    def compose_video(
        self,
        script: VideoScript,
        scene_assets: List[str],
        audio_path: str,
        subtitle_segments: Optional[List[Dict[str, Any]]],
        output_path: str
    ) -> str:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        audio_clip = AudioFileClip(audio_path)
        total_audio_duration = audio_clip.duration

        num_scenes = max(1, len(script.scenes))
        per_scene_duration = total_audio_duration / num_scenes

        logger.info(f"Composing timeline: {num_scenes} scenes, total duration: {total_audio_duration:.2f}s")

        clips = []
        for scene, asset_path in zip(script.scenes, scene_assets):
            duration = per_scene_duration
            clip = self._prepare_scene_clip(asset_path, duration, shot_type=scene.shot_type)
            clips.append(clip)

        base_video = concatenate_videoclips(clips, method="compose")
        base_video = base_video.with_duration(total_audio_duration)

        layers = [base_video]

        # 1. Add Hook Overlay Banner (Golden-Yellow at top, 0 to 2.5s)
        if self.is_short and script.hook_overlay:
            hook_clip = self._create_hook_banner(script.hook_overlay, duration=min(2.5, total_audio_duration))
            if hook_clip:
                layers.append(hook_clip)

        # 2. Add dynamic subtitle overlays
        # If per-scene captions are available from Director Script, use scene captions
        if subtitle_segments:
            sub_clips = self._create_subtitle_clips(subtitle_segments, total_audio_duration)
            layers.extend(sub_clips)
        else:
            # Fallback to scene-level captions
            scene_subs = self._create_scene_captions(script.scenes, per_scene_duration)
            layers.extend(scene_subs)

        composite = CompositeVideoClip(layers, size=(self.width, self.height))
        composite = composite.with_duration(total_audio_duration)
        composite = composite.with_audio(audio_clip)

        logger.info(f"Rendering final MP4 to {out_file}")
        composite.write_videofile(
            str(out_file),
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            preset="fast",
            threads=4,
            logger=None
        )

        for c in clips:
            c.close()
        audio_clip.close()
        composite.close()

        return str(out_file)

    def _prepare_scene_clip(self, asset_path: str, duration: float, shot_type: str = "static"):
        path = Path(asset_path)
        is_video = path.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]

        if is_video:
            clip = VideoFileClip(str(path))
            if clip.duration < duration:
                num_loops = int(duration / clip.duration) + 1
                clip = concatenate_videoclips([clip] * num_loops)
            clip = clip.subclipped(0, duration)
        else:
            clip = ImageClip(str(path)).with_duration(duration)

        # Fit to 1080x1920 canvas
        clip = self._fit_to_canvas(clip)

        # Apply Ken Burns Zoom effect based on shot_type
        clip = self._apply_ken_burns(clip, shot_type, duration)
        return clip

    def _apply_ken_burns(self, clip, shot_type: str, duration: float):
        """
        Ken Burns zoom mappings from n8n workflow:
        - action: 100% -> 135% fast zoom in
        - reveal: 135% -> 100% pull-out
        - wide: 118% -> 100% gentle pull
        - closeup: 100% -> 108% subtle zoom
        - static: 100% -> 106% gentle drift
        - tracking: 108% -> 125% tracking zoom
        """
        zoom_profiles = {
            "action": (1.00, 1.25),
            "reveal": (1.25, 1.00),
            "wide": (1.15, 1.00),
            "closeup": (1.00, 1.08),
            "static": (1.00, 1.06),
            "tracking": (1.05, 1.20)
        }
        start_scale, end_scale = zoom_profiles.get(shot_type, (1.0, 1.08))

        # Dynamic scaling function
        def zoom_func(t):
            progress = min(1.0, max(0.0, t / duration))
            scale = start_scale + (end_scale - start_scale) * progress
            return scale

        try:
            return clip.resized(zoom_func)
        except Exception:
            return clip

    def _fit_to_canvas(self, clip):
        w, h = clip.size
        target_ratio = self.width / self.height
        current_ratio = w / h

        if current_ratio > target_ratio:
            new_h = self.height
            new_w = int(w * (self.height / h))
            clip = clip.resized(height=new_h)
            x_center = (new_w - self.width) // 2
            clip = clip.cropped(x1=x_center, y1=0, x2=x_center + self.width, y2=self.height)
        else:
            new_w = self.width
            new_h = int(h * (self.width / w))
            clip = clip.resized(width=new_w)
            y_center = (new_h - self.height) // 2
            clip = clip.cropped(x1=0, y1=y_center, x2=self.width, y2=y_center + self.height)

        return clip

    def _create_hook_banner(self, hook_text: str, duration: float) -> Optional[CompositeVideoClip]:
        """
        Creates a vibrant Golden Yellow (#FFD400) badge with black text
        at top (y: 16%) displayed during the first 2.5 seconds to maximize viewer retention.
        """
        try:
            txt = hook_text.upper()[:40]
            # Text clip
            txt_clip = TextClip(
                text=txt,
                font_size=50,
                color="#000000",
                duration=duration
            )
            tw, th = txt_clip.size
            pad_x, pad_y = 40, 20
            bw, bh = tw + pad_x * 2, th + pad_y * 2
            
            # Yellow banner background
            bg_clip = ColorClip(size=(bw, bh), color=(255, 212, 0)).with_duration(duration)
            txt_positioned = txt_clip.with_position(("center", "center"))
            
            banner = CompositeVideoClip([bg_clip, txt_positioned], size=(bw, bh)).with_duration(duration)
            y_pos = int(self.height * 0.16)
            return banner.with_start(0).with_position(("center", y_pos))
        except Exception as e:
            logger.warning(f"Could not create hook banner: {e}")
            return None

    def _create_subtitle_clips(self, segments: List[Dict[str, Any]], max_duration: float) -> List[TextClip]:
        sub_clips = []
        font_size = 56 if self.is_short else 42
        y_pos = int(self.height * 0.74) if self.is_short else int(self.height * 0.82)

        for seg in segments:
            start = seg.get("start", 0.0)
            end = min(seg.get("end", start + 2.0), max_duration)
            dur = max(0.2, end - start)
            text = seg.get("text", "").strip().upper()
            if not text:
                continue

            color = "#FFFFFF" if len(sub_clips) % 2 == 0 else "#FFD400"
            try:
                txt_clip = TextClip(
                    text=text,
                    font_size=font_size,
                    color=color,
                    stroke_color="black",
                    stroke_width=4,
                    duration=dur
                )
                txt_clip = txt_clip.with_start(start).with_position(("center", y_pos))
                sub_clips.append(txt_clip)
            except Exception as e:
                logger.warning(f"Error creating subtitle clip for '{text}': {e}")

        return sub_clips

    def _create_scene_captions(self, scenes: List[Scene], per_scene_duration: float) -> List[TextClip]:
        clips = []
        y_pos = int(self.height * 0.74)
        for i, s in enumerate(scenes):
            cap = (s.caption or s.tts_text[:40]).strip().upper()
            start = i * per_scene_duration
            dur = per_scene_duration
            try:
                txt = TextClip(
                    text=cap,
                    font_size=54,
                    color="#FFFFFF",
                    stroke_color="black",
                    stroke_width=4,
                    duration=dur
                )
                txt = txt.with_start(start).with_position(("center", y_pos))
                clips.append(txt)
            except Exception as e:
                logger.warning(f"Error creating scene caption: {e}")
        return clips
