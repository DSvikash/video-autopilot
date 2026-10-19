import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Literal, Optional

from config.settings import config
from src.scripting.generator import ScriptGenerator
from src.voice.synthesizer import VoiceSynthesizer
from src.alignment.subtitle_generator import SubtitleGenerator
from src.sourcing.asset_manager import AssetManager
from src.mastering.audio_processor import AudioMasterer
from src.composer.timeline_composer import TimelineComposer
from src.safety.compliance_gate import ComplianceGate
from src.publisher.youtube_uploader import YouTubeUploader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("VideoAutopilotPipeline")

class VideoAutopilotPipeline:
    """
    Autonomous End-to-End Hinglish & Global Video Pipeline:
    Topic + Genre -> Director Script -> Speech -> -14 LUFS Mastering -> Subtitles -> Sourcing ->
    Ken Burns + Hook Banner Composition -> Compliance -> YouTube Resumable Upload
    """
    def __init__(self):
        self.script_gen = ScriptGenerator()
        self.voice_syn = VoiceSynthesizer()
        self.asset_mgr = AssetManager()
        self.audio_masterer = AudioMasterer()
        self.compliance_gate = ComplianceGate()
        self.uploader = YouTubeUploader()

    def run(
        self,
        topic: str,
        format_type: Literal["short", "long"] = "short",
        genre: Optional[str] = "explainer",
        upload_to_youtube: bool = True
    ) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"=== Starting Hinglish Tech Director Pipeline ===")
        logger.info(f"Topic: '{topic}' | Format: {format_type.upper()} | Genre: {genre or 'explainer'}")

        session_id = f"{int(time.time())}_{format_type}"
        session_dir = config.output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # 1. Script Generation (Director Script with Facts & per-line Direction)
        logger.info("Stage 1/8: Generating Director Script...")
        script = self.script_gen.generate_script(topic, format_type=format_type, genre=genre)
        script_file = session_dir / "script.json"
        with open(script_file, "w") as f:
            f.write(script.model_dump_json(indent=2))

        # 2. Voice Narration Synthesis
        logger.info("Stage 2/8: Synthesizing Voice Narration...")
        full_narration = script.get_full_narration()
        raw_voice_file = session_dir / "raw_narration.mp3"
        voice_result = self.voice_syn.synthesize(full_narration, str(raw_voice_file))

        # 3. Audio Mastering (-14 LUFS Broadcast Standard)
        logger.info("Stage 3/8: Mastering Audio Dialogue Chain (-14 LUFS)...")
        mastered_voice_file = session_dir / "mastered_narration.wav"
        self.audio_masterer.master_dialogue(str(raw_voice_file), str(mastered_voice_file))

        # 4. Subtitle Generation & Alignment
        logger.info("Stage 4/8: Generating Timed Subtitles...")
        sub_generator = SubtitleGenerator(is_short=(format_type == "short"))
        subtitle_segments = []
        if voice_result.get("submaker"):
            submaker = voice_result["submaker"]
            srt_content = submaker.get_srt()
            subtitle_segments = sub_generator._parse_srt_to_segments(srt_content)
            ass_path = session_dir / "subtitles.ass"
            sub_generator.generate_ass(subtitle_segments, str(ass_path))

        # 5. Scene Asset Sourcing & Visual Verification
        logger.info("Stage 5/8: Sourcing & Verifying Scene Assets...")
        scene_assets = []
        is_short = (format_type == "short")
        for scene in script.scenes:
            asset_path = self.asset_mgr.fetch_scene_asset(scene, is_short=is_short)
            scene_assets.append(asset_path)

        # 6. Timeline Composition with Ken Burns & Golden Hook Banner
        logger.info("Stage 6/8: Composing Timeline with Ken Burns & Hook Banner...")
        composer = TimelineComposer(is_short=is_short)
        rendered_video_path = session_dir / f"final_{format_type}.mp4"
        composer.compose_video(
            script=script,
            scene_assets=scene_assets,
            audio_path=str(mastered_voice_file),
            subtitle_segments=subtitle_segments,
            output_path=str(rendered_video_path)
        )

        # 7. Compliance & Safety Inspection Gate
        logger.info("Stage 7/8: Inspecting Pre-Flight Compliance...")
        passed, compliance_report = self.compliance_gate.inspect(str(rendered_video_path), script)
        if not passed:
            raise RuntimeError(f"Video failed compliance inspection: {compliance_report}")

        # 8. YouTube Ingestion & Upload
        upload_result = None
        if upload_to_youtube:
            logger.info("Stage 8/8: Initiating YouTube Publishing...")
            upload_result = self.uploader.upload_video(str(rendered_video_path), script)

        total_elapsed = time.time() - start_time
        logger.info(f"=== Pipeline Completed Successfully in {total_elapsed:.1f}s ===")

        return {
            "status": "success",
            "elapsed_seconds": round(total_elapsed, 2),
            "topic": topic,
            "genre": script.genre,
            "format": format_type,
            "title": script.title,
            "hook_overlay": script.hook_overlay,
            "video_path": str(rendered_video_path),
            "script": script.model_dump(),
            "compliance": compliance_report,
            "upload": upload_result
        }
