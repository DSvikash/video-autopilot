import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    TextClip,
    concatenate_videoclips
)

from config.settings import config
from src.studio.models import DocumentaryScript, Chapter, Slide
from src.studio.visual_deck import VisualDeckGenerator
from src.voice.synthesizer import VoiceSynthesizer
from src.mastering.audio_processor import AudioMasterer
from src.safety.compliance_gate import ComplianceGate
from src.publisher.youtube_uploader import YouTubeUploader

logger = logging.getLogger(__name__)

class StudioComposer:
    """
    Broadcast-grade Long-Form Documentary Production Engine.
    Produces high-retention 1920x1080 tech explainer videos with:
    - Multi-chapter structure & automatic YouTube timestamps
    - Sleek dark-mode technical visual decks & stat cards
    - Confident, articulate narrator voice
    - -14 LUFS broadcast audio mastering
    """
    def __init__(self):
        self.deck_generator = VisualDeckGenerator(output_dir=config.base_dir / "output" / "slides")
        self.voice_syn = VoiceSynthesizer(voice="en-US-ChristopherNeural", speed_factor=1.0)
        self.audio_masterer = AudioMasterer()
        self.uploader = YouTubeUploader()
        self.width = 1920
        self.height = 1080
        self.fps = 30

    def produce_documentary(
        self,
        script: DocumentaryScript,
        upload_to_youtube: bool = True
    ) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"=== Starting Studio Documentary Production: '{script.title}' ===")

        session_id = f"doc_{int(time.time())}"
        session_dir = config.base_dir / "output" / "documentaries" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        total_chapters = len(script.chapters)
        timeline_clips = []
        audio_clips = []
        
        current_time_offset = 0.0

        # Iterate through chapters and slides
        for ch_idx, chapter in enumerate(script.chapters, 1):
            # Calculate timestamp string (MM:SS)
            mins = int(current_time_offset // 60)
            secs = int(current_time_offset % 60)
            chapter.timestamp_str = f"{mins:02d}:{secs:02d}"
            chapter.start_seconds = current_time_offset

            logger.info(f"Producing Chapter {ch_idx}/{total_chapters}: '{chapter.title}' at {chapter.timestamp_str}")

            for slide in chapter.slides:
                # 1. Synthesize narration audio for this slide
                slide_audio_path = session_dir / f"audio_ch{ch_idx}_{slide.slide_id}.mp3"
                self.voice_syn.synthesize(slide.narration, str(slide_audio_path))
                
                audio_clip = AudioFileClip(str(slide_audio_path))
                slide_duration = audio_clip.duration + 0.6  # Add subtle natural breathing pause
                current_time_offset += slide_duration

                # 2. Render 1920x1080 visual deck card
                slide_img_path = self.deck_generator.generate_slide_image(
                    slide=slide,
                    chapter_title=chapter.title,
                    chapter_idx=ch_idx,
                    total_chapters=total_chapters
                )

                # 3. Create video clip for this slide
                img_clip = ImageClip(slide_img_path).with_duration(slide_duration)
                
                # Add subtle animated zoom (Ken Burns)
                def subtle_zoom(t):
                    return 1.0 + 0.04 * (t / slide_duration)
                
                try:
                    img_clip = img_clip.resized(subtle_zoom)
                except Exception:
                    pass

                # Set audio
                img_clip = img_clip.with_audio(audio_clip)
                timeline_clips.append(img_clip)
                audio_clips.append(audio_clip)

        # 4. Concatenate full video timeline
        logger.info(f"Concatenating {len(timeline_clips)} documentary slides into full master...")
        final_video = concatenate_videoclips(timeline_clips, method="compose")
        total_duration = final_video.duration

        raw_output_path = session_dir / "raw_documentary.mp4"
        final_video.write_videofile(
            str(raw_output_path),
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            preset="fast",
            threads=4,
            logger=None
        )

        # 5. Broadcast Audio Mastering (-14 LUFS)
        logger.info("Applying broadcast-grade -14 LUFS dialogue mastering to complete documentary...")
        mastered_output_path = session_dir / f"{session_id}_final_1080p.mp4"
        
        # Extract audio, master it, remux with video
        temp_audio = session_dir / "extracted_audio.wav"
        mastered_audio = session_dir / "mastered_audio.wav"
        
        os.system(f"ffmpeg -y -i '{raw_output_path}' -vn -ar 48000 -ac 2 '{temp_audio}' >/dev/null 2>&1")
        self.audio_masterer.master_dialogue(str(temp_audio), str(mastered_audio))
        os.system(f"ffmpeg -y -i '{raw_output_path}' -i '{mastered_audio}' -c:v copy -c:a aac -b:a 192k -map 0:v:0 -map 1:a:0 '{mastered_output_path}' >/dev/null 2>&1")

        if raw_output_path.exists():
            raw_output_path.unlink()

        # Clean up moviepy memory
        for c in timeline_clips:
            c.close()
        for a in audio_clips:
            a.close()
        final_video.close()

        # 6. Generate YouTube Description with Timestamps
        full_description = script.get_youtube_description_with_timestamps()
        meta_file = session_dir / "youtube_metadata.txt"
        with open(meta_file, "w") as f:
            f.write(f"TITLE:\n{script.title}\n\nDESCRIPTION:\n{full_description}\n\nTAGS:\n{', '.join(script.tags)}")

        # 7. Upload to YouTube if requested
        upload_result = None
        if upload_to_youtube:
            logger.info("Uploading High-Value Long-Form Documentary to YouTube...")
            # Wrap script into standard structure for uploader
            from src.scripting.models import VideoScript, Scene
            compat_script = VideoScript(
                topic=script.topic,
                format_type="long",
                title=script.title[:100],
                description=full_description[:5000],
                tags=script.tags[:50],
                call_to_action="Subscribe for more weekly deep dives!",
                contains_synthetic_media=True,
                estimated_total_duration=total_duration,
                scenes=[]
            )
            upload_result = self.uploader.upload_video(str(mastered_output_path), compat_script)

        elapsed = time.time() - start_time
        logger.info(f"=== Documentary Production Complete in {elapsed:.1f}s ===")

        return {
            "status": "success",
            "video_path": str(mastered_output_path),
            "title": script.title,
            "duration": total_duration,
            "chapters": [ch.model_dump() for ch in script.chapters],
            "description": full_description,
            "upload": upload_result,
            "elapsed_seconds": round(elapsed, 2)
        }
