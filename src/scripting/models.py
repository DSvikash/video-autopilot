from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

ShotType = Literal["action", "reveal", "wide", "closeup", "static", "tracking"]
GenreType = Literal["explainer", "action", "drama", "thriller", "motivational", "mystery", "comedy", "general"]

class ScriptFact(BaseModel):
    fact: str
    source_url: Optional[str] = ""

class Scene(BaseModel):
    scene_id: int
    role: Optional[str] = "beat"  # "hook", "beat", "turn", "cta"
    tts_text: str = Field(description="Exact spoken text for narration (Hindi/Devanagari + English terms)")
    narration: Optional[str] = ""  # Backward compatibility fallback
    caption: str = Field(default="", description="Punchy Roman Hinglish subtitle text (max 8 words)")
    emotion: Optional[str] = "excitement"
    pace: float = Field(default=1.0, ge=0.5, le=2.0)
    expressiveness: float = Field(default=0.6, ge=0.01, le=1.0)
    shot_type: ShotType = "static"
    image_prompt: Optional[str] = ""
    visual_description: str = Field(default="", description="Semantic visual scene description for asset matching")
    search_keywords: List[str] = Field(default_factory=list, description="2-4 stock search keywords")
    estimated_duration: float = Field(default=5.0, description="Estimated duration in seconds")

    def __init__(self, **data):
        super().__init__(**data)
        if not self.narration and self.tts_text:
            self.narration = self.tts_text
        elif not self.tts_text and self.narration:
            self.tts_text = self.narration
        if not self.caption:
            self.caption = self.tts_text[:60]

class VideoScript(BaseModel):
    topic: str
    format_type: Literal["short", "long"] = "short"
    genre: Optional[str] = "explainer"
    title: str
    description: str
    tags: List[str]
    hashtags: Optional[List[str]] = Field(default_factory=list)
    hook_overlay: Optional[str] = Field(default="", description="5-8 word punchy badge for first 2.5s")
    call_to_action: str = "Subscribe for more daily tech insights!"
    contains_synthetic_media: bool = True
    disclosure_reason: Optional[str] = ""
    facts: Optional[List[ScriptFact]] = Field(default_factory=list)
    estimated_total_duration: float = 35.0
    scenes: List[Scene]

    def get_full_narration(self) -> str:
        return " ".join([s.tts_text.strip() for s in self.scenes if s.tts_text.strip()])
