import os
from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent

class VideoSpecs(BaseModel):
    format_type: Literal["short", "long"] = "short"
    width: int = 1080
    height: int = 1920
    fps: int = 30
    max_duration_seconds: int = 60
    min_duration_seconds: int = 15

class AudioMasteringConfig(BaseModel):
    target_lufs: float = -14.0
    true_peak_dbtp: float = -1.5
    highpass_freq: int = 80
    deesser_intensity: float = 0.4
    afftdn_delay_compensation_ms: int = 25
    music_ducking_volume: float = 0.12  # Background music relative volume

class VoiceConfig(BaseModel):
    provider: Literal["edge-tts", "custom-clone", "kokoro"] = "edge-tts"
    edge_voice: str = "en-US-ChristopherNeural"  # Professional energetic documentary voice
    custom_voice_sample: str = str(BASE_DIR / "data" / "voice_samples" / "default_voice.m4a")
    speed_factor: float = 1.05  # Slightly faster for high-retention Shorts

class SafetyConfig(BaseModel):
    contains_synthetic_media: bool = True
    min_visual_relevance_score: float = 6.0  # 1-10 scale
    auto_publish: bool = False  # If false, upload as unlisted/private for review
    privacy_status: Literal["public", "private", "unlisted"] = "private"

class YouTubeConfig(BaseModel):
    client_secrets_file: str = str(BASE_DIR / "client_secrets.json")
    credentials_storage: str = str(BASE_DIR / "oauth_credentials.json")
    daily_upload_limit: int = 10
    default_category_id: str = "27"  # 27 = Education, 28 = Science & Tech, 24 = Entertainment
    tags_default: list[str] = ["Shorts", "Facts", "Education", "Tech", "Viral"]

class PipelineConfig(BaseModel):
    base_dir: Path = BASE_DIR
    output_dir: Path = BASE_DIR / "output"
    cache_dir: Path = BASE_DIR / "data" / "cache"
    video_specs: VideoSpecs = Field(default_factory=VideoSpecs)
    audio: AudioMasteringConfig = Field(default_factory=AudioMasteringConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    youtube: YouTubeConfig = Field(default_factory=YouTubeConfig)
    
    # LLM Settings
    llm_provider: Literal["gemini", "openai", "ollama"] = "gemini"
    llm_model: str = "gemini-1.5-flash"

    def get_specs_for_format(self, fmt: Literal["short", "long"]) -> VideoSpecs:
        if fmt == "short":
            return VideoSpecs(
                format_type="short",
                width=1080,
                height=1920,
                fps=30,
                max_duration_seconds=60,
                min_duration_seconds=20
            )
        else:
            return VideoSpecs(
                format_type="long",
                width=1920,
                height=1080,
                fps=30,
                max_duration_seconds=600,
                min_duration_seconds=120
            )

# Singleton global configuration
config = PipelineConfig()
