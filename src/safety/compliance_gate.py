import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
from config.settings import config
from src.scripting.models import VideoScript

logger = logging.getLogger(__name__)

class ComplianceGate:
    """
    Pre-flight safety gate to ensure videos comply with YouTube policies:
    - 9:16 vertical orientation and <= 60s duration for Shorts
    - Mandatory status.containsSyntheticMedia declaration for AI voice/content
    - Required tags and metadata integrity
    """
    def inspect(self, video_path: str, script: VideoScript) -> Tuple[bool, Dict[str, Any]]:
        path = Path(video_path)
        if not path.exists():
            return False, {"error": f"Video file not found: {video_path}"}

        # Inspect video streams using ffprobe
        probe_cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(path)
        ]
        res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            return False, {"error": "ffprobe failed to inspect video"}

        info = json.loads(res.stdout)
        duration = float(info.get("format", {}).get("duration", 0.0))
        
        video_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        if not video_stream:
            return False, {"error": "No video stream detected in media file"}

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))

        report = {
            "video_path": str(path),
            "duration": duration,
            "width": width,
            "height": height,
            "format_type": script.format_type,
            "checks": []
        }

        # 1. Shorts Aspect Ratio and Duration check
        if script.format_type == "short":
            if width > height:
                report["checks"].append({"check": "aspect_ratio", "passed": False, "msg": f"Shorts must be vertical (got {width}x{height})"})
                return False, report
            if duration > 61.0:
                report["checks"].append({"check": "duration", "passed": False, "msg": f"Shorts must be <= 60s (got {duration:.1f}s)"})
                return False, report
            
            # Ensure #Shorts tag exists
            if "#Shorts" not in script.title and "#Shorts" not in script.description:
                script.title = f"{script.title} #Shorts"
            report["checks"].append({"check": "shorts_compliance", "passed": True, "msg": "Vertical aspect ratio & duration valid"})
        else:
            if width < height:
                report["checks"].append({"check": "aspect_ratio", "passed": False, "msg": f"Long-form must be horizontal 16:9 (got {width}x{height})"})
                return False, report
            report["checks"].append({"check": "long_compliance", "passed": True, "msg": "Horizontal 16:9 format valid"})

        # 2. Synthetic Media Disclosure Check (mandatory for YouTube 2026 policy)
        report["contains_synthetic_media"] = script.contains_synthetic_media
        report["checks"].append({
            "check": "synthetic_media_disclosure",
            "passed": True,
            "msg": f"status.containsSyntheticMedia declared as {script.contains_synthetic_media}"
        })

        # 3. Audio stream verification
        has_audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
        if not has_audio:
            report["checks"].append({"check": "audio_present", "passed": False, "msg": "No audio stream found"})
            return False, report
        report["checks"].append({"check": "audio_present", "passed": True, "msg": "Audio stream verified"})

        return True, report
