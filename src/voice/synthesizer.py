import asyncio
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import edge_tts
from config.settings import config

logger = logging.getLogger(__name__)

class VoiceSynthesizer:
    def __init__(self, voice: Optional[str] = None, speed_factor: Optional[float] = None):
        self.voice = voice or config.voice.edge_voice
        self.speed_factor = speed_factor or config.voice.speed_factor
        self.reference_sample = config.voice.custom_voice_sample

    def synthesize(self, text: str, output_path: str) -> Dict[str, Any]:
        """
        Synthesizes text into high quality speech audio file.
        Returns metadata including duration, file path, and word boundaries if available.
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if user has an ElevenLabs voice cloning API key configured
        eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
        eleven_voice_id = os.getenv("ELEVENLABS_VOICE_ID")
        if eleven_api_key and eleven_voice_id:
            try:
                return self._synthesize_elevenlabs(text, output_file, eleven_api_key, eleven_voice_id)
            except Exception as e:
                logger.warning(f"Voice cloning via ElevenLabs failed: {e}. Falling back to Neural Edge-TTS...")

        # Fast, zero-cost high-fidelity neural synthesis (Edge-TTS)
        return asyncio.run(self._synthesize_edge_tts(text, output_file))

    async def _synthesize_edge_tts(self, text: str, output_file: Path) -> Dict[str, Any]:
        rate_str = f"+{int((self.speed_factor - 1.0) * 100)}%" if self.speed_factor >= 1.0 else f"-{int((1.0 - self.speed_factor) * 100)}%"
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

    def _synthesize_elevenlabs(self, text: str, output_file: Path, api_key: str, voice_id: str) -> Dict[str, Any]:
        import requests
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8
            }
        }
        response = requests.post(url, json=data, headers=headers, timeout=60)
        response.raise_for_status()
        with open(output_file, "wb") as f:
            f.write(response.content)
            
        return {
            "audio_path": str(output_file),
            "engine": "elevenlabs-voice-clone",
            "voice_id": voice_id,
            "has_subtitles": False
        }
