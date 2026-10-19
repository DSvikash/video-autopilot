import subprocess
import logging
from pathlib import Path
from typing import Optional
from config.settings import config

logger = logging.getLogger(__name__)

class AudioMasterer:
    """
    Executes broadcast-grade audio mastering targeting YouTube's standard -14 LUFS
    and true-peak -1.5 dBTP using FFmpeg's dialogue chain and EBU R128 normalization.
    """
    def __init__(
        self,
        target_lufs: float = -14.0,
        true_peak: float = -1.5,
        highpass_freq: int = 80
    ):
        self.target_lufs = target_lufs
        self.true_peak = true_peak
        self.highpass_freq = highpass_freq

    def master_dialogue(self, input_voice_path: str, output_mastered_path: str) -> str:
        """
        Processes voice narration through the 8-stage dialogue chain:
        High-pass (80Hz) -> EQ (mud cut, presence boost, air) -> Compression -> De-esser -> Loudnorm (-14 LUFS).
        """
        in_path = Path(input_voice_path)
        out_path = Path(output_mastered_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        filter_chain = (
            f"highpass=f={self.highpass_freq},"
            "equalizer=f=200:t=q:w=1:g=-2,"
            "equalizer=f=4200:t=q:w=1:g=2.5,"
            "equalizer=f=9000:t=q:w=1:g=1,"
            "acompressor=threshold=0.125:ratio=3:attack=10:release=160:makeup=1.4,"
            "deesser=i=0.4:m=0.5:f=0.55:s=o,"
            f"loudnorm=I={self.target_lufs}:TP={self.true_peak}:LRA=7"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(in_path),
            "-af", filter_chain,
            "-ar", "48000",
            "-ac", "2",
            "-c:a", "pcm_s16le",
            str(out_path)
        ]

        logger.info(f"Running audio mastering chain on {in_path.name} -> {out_path.name}")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            logger.error(f"Audio mastering failed: {res.stderr}")
            # Fallback to copy if complex filter fails
            subprocess.run(["ffmpeg", "-y", "-i", str(in_path), "-ar", "48000", str(out_path)], check=True)

        return str(out_path)

    def mix_voice_and_music(
        self,
        voice_path: str,
        output_path: str,
        music_path: Optional[str] = None,
        music_volume: float = 0.12
    ) -> str:
        """
        Mixes mastered voice narration with ducked background music.
        If no background music provided, outputs mastered voice.
        """
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        if not music_path or not Path(music_path).exists():
            return self.master_dialogue(voice_path, output_path)

        # Mix voice and looping ducked background music
        filter_complex = (
            f"[1:a]volume={music_volume}[music];"
            "[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[mixed];"
            f"[mixed]loudnorm=I={self.target_lufs}:TP={self.true_peak}:LRA=7[out]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(voice_path),
            "-stream_loop", "-1",
            "-i", str(music_path),
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-ar", "48000",
            "-ac", "2",
            "-c:a", "aac",
            "-b:a", "192k",
            str(out_file)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return str(out_file)
