import os
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from moviepy import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    TextClip,
    concatenate_videoclips
)
from config.settings import config
from src.scripting.models import VideoScript, Scene

logger = logging.getLogger(__name__)

class TimelineComposer:
    """
    Modern MoviePy v2.2+ compositor.
    Supports both Shorts (1080x1920 vertical) and Long-form (1920x1080 horizontal),
    with Ken Burns subtle motion and built-in Pillow-rendered viral subtitles.
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
        """
        Assembles all scene assets, syncs total duration to audio,
        applies dynamic scaling, and embeds high-contrast subtitles.
        """
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # 1. Audio clip & duration
        audio_clip = AudioFileClip(audio_path)
        total_audio_duration = audio_clip.duration

        num_scenes = max(1, len(script.scenes))
        per_scene_duration = total_audio_duration / num_scenes

        logger.info(f"Composing timeline: {num_scenes} scenes, total duration: {total_audio_duration:.2f}s")

        clips = []
        for scene, asset_path in zip(script.scenes, scene_assets):
            duration = per_scene_duration
            clip = self._prepare_scene_clip(asset_path, duration)
            clips.append(clip)

        # Base video timeline
        base_video = concatenate_videoclips(clips, method="compose")
        base_video = base_video.with_duration(total_audio_duration)

        # 2. Add dynamic subtitle overlays if segments provided
        layers = [base_video]
        if subtitle_segments:
            logger.info(f"Adding {len(subtitle_segments)} dynamic subtitle overlays...")
            sub_clips = self._create_subtitle_clips(subtitle_segments, total_audio_duration)
            layers.extend(sub_clips)

        # Composite everything together
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

        # Clean up resources
        for c in clips:
            c.close()
        audio_clip.close()
        composite.close()

        return str(out_file)

    def _prepare_scene_clip(self, asset_path: str, duration: float):
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

        clip = self._fit_to_canvas(clip)
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

    def _create_subtitle_clips(self, segments: List[Dict[str, Any]], max_duration: float) -> List[TextClip]:
        sub_clips = []
        font_size = 54 if self.is_short else 42
        y_pos = int(self.height * 0.72) if self.is_short else int(self.height * 0.82)

        for seg in segments:
            start = seg.get("start", 0.0)
            end = min(seg.get("end", start + 2.0), max_duration)
            dur = max(0.2, end - start)
            text = seg.get("text", "").strip().upper()
            if not text:
                continue

            # Alternate between vibrant Yellow and Crisp White for visual punch
            color = "#FACC15" if len(sub_clips) % 2 == 0 else "#FFFFFF"

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
