from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

SlideType = Literal["title", "feature_card", "benchmark", "comparison", "code_snippet", "news_roundup", "takeaway"]

class Slide(BaseModel):
    slide_id: int
    slide_type: SlideType
    category: str = "AI ARCHITECTURE & NEWS"
    headline: str
    subheadline: str
    bullet_points: List[str] = Field(default_factory=list)
    stat_badge: Optional[str] = ""
    highlight_metric: Optional[str] = ""
    narration: str = Field(description="Rich conversational, expert-level spoken script for this slide")
    duration: float = Field(default=8.0, description="Estimated duration in seconds")

class Chapter(BaseModel):
    chapter_index: int
    title: str
    timestamp_str: str = "00:00"
    start_seconds: float = 0.0
    slides: List[Slide]

class DocumentaryScript(BaseModel):
    topic: str
    title: str
    lead_hook: str
    description: str
    tags: List[str]
    chapters: List[Chapter]
    total_duration_estimate: float = 300.0

    def get_full_narration(self) -> str:
        all_narrations = []
        for ch in self.chapters:
            for sl in ch.slides:
                if sl.narration.strip():
                    all_narrations.append(sl.narration.strip())
        return " ".join(all_narrations)

    def get_youtube_description_with_timestamps(self) -> str:
        lines = [self.description.strip(), "\n📌 TIMESTAMPS:"]
        for ch in self.chapters:
            lines.append(f"{ch.timestamp_str} - {ch.title}")
        lines.append("\n#AINews #TechDeepDive #ArtificialIntelligence #Gemini #OpenAI")
        return "\n".join(lines)
