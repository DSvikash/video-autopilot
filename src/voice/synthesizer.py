import asyncio
import os
import logging
import base64
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import edge_tts
from config.settings import config

logger = logging.getLogger(__name__)

class VoiceSynthesizer:
    def __init__(self, voice: Optional[str] = None, speed_factor: Optional[float] = None):
        # Default to Indian Hindi/Hinglish energetic narrator
        self.voice = voice or os.getenv("DEFAULT_VOICE", "hi-IN-MadhurNeural")
        self.speed_factor = speed_factor or config.voice.speed_factor
        self.sarvam_api_key = os.getenv("SARVAM_API_KEY")

    def synthesize(self, text: str, output_path: str, pace: float = 1.05) -> Dict[str, Any]:
        """
        Synthesizes Hinglish / English script text into clear broadcast-quality audio.
        Supports Sarvam AI (speaker: shubh) and zero-cost Indian Neural Edge-TTS (hi-IN-MadhurNeural).
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 1. Try Sarvam AI if API key is provided
        if self.sarvam_api_key:
            try:
                logger.info("Synthesizing Hinglish voice via Sarvam AI (bulbul:v3, speaker: shubh)...")
                return self._synthesize_sarvam(text, output_file, pace=pace)
            except Exception as e:
                logger.warning(f"Sarvam AI TTS failed: {e}. Falling back to Indian Neural Edge-TTS...")

        # 2. Fast Zero-Cost Neural Edge-TTS (hi-IN-MadhurNeural)
        return asyncio.run(self._synthesize_edge_tts(text, output_file, pace=pace))

    def _synthesize_sarvam(self, text: str, output_file: Path, pace: float) -> Dict[str, Any]:
        url = "https://api.sarvam.ai/text-to-speech"
        headers = {
            "Content-Type": "application/json",
            "api-subscription-key": self.sarvam_api_key
        }
        payload = {
            "text": text,
            "language_code": "hi-IN",
            "model": "bulbul:v3",
            "speaker": "shubh",
            "pace": pace,
            "speech_sample_rate": 44100,
            "output_audio_codec": "mp3"
        }
        res = requests.post(url, json=payload, headers=headers, timeout=60)
        res.raise_for_status()
        data = res.json()
        
        audios = data.get("audios", [])
        if not audios:
            raise ValueError("Sarvam AI returned empty audio response")
            
        audio_bytes = base64.b64decode("".join(audios))
        with open(output_file, "wb") as f:
            f.write(audio_bytes)

        return {
            "audio_path": str(output_file),
            "engine": "sarvam-ai",
            "speaker": "shubh",
            "has_subtitles": False
        }

    async def _synthesize_edge_tts(self, text: str, output_file: Path, pace: float) -> Dict[str, Any]:
        # Speed adjustment
        effective_pace = pace * self.speed_factor
        rate_int = int((effective_pace - 1.0) * 100)
        rate_str = f"+{rate_int}%" if rate_int >= 0 else f"{rate_int}%"
        
        communicate = edge_tts.Communicate(text, self.voice, rate=rate_str)
        submaker = edge_tts.SubMaker()
        with open(output_file, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)

        return {
            "audio_path": str(output_file),
            "engine": "edge-tts",
            "voice": self.voice,
            "has_subtitles": True,
            "submaker": submaker
        }
