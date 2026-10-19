from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class Scene(BaseModel):
    scene_id: int
    narration: str = Field(description="Exact script text for voiceover narration in this scene")
    visual_description: str = Field(description="Semantic visual scene description for asset matching")
    search_keywords: List[str] = Field(description="2-4 specific stock footage search keywords")
    estimated_duration: float = Field(default=5.0, description="Estimated duration in seconds")

class VideoScript(BaseModel):
    topic: str
    format_type: Literal["short", "long"]
    title: str
    description: str
    tags: List[str]
    call_to_action: str
    contains_synthetic_media: bool = True
    estimated_total_duration: float
    scenes: List[Scene]

    def get_full_narration(self) -> str:
        return " ".join([s.narration.strip() for s in self.scenes if s.narration.strip()])
