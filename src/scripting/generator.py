import os
import json
import logging
from typing import Literal, Optional
from config.settings import config
from src.scripting.models import VideoScript, Scene

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an elite YouTube content strategist and viral scriptwriter.
Your goal is to write a high-retention video script that maximizes viewer watch time and engagement for YouTube monetization.

Format Guidelines:
1. For SHORTS (under 60s):
   - Hook in the first 2 seconds (provocative question or unbelievable fact).
   - Fast pacing, 4-6 concise scenes.
   - Spoken word count must be 120-150 words total.
   - Include #Shorts in title and tags.
2. For LONG-FORM (3-8 minutes):
   - Strong 15s hook + overview.
   - 8-15 progressive scenes with valuable insights, smooth transitions, and narrative tension.
   - Compelling Call To Action (like, subscribe, comment).

Respond strictly with a valid JSON object matching this schema:
{
  "topic": "...",
  "format_type": "short" | "long",
  "title": "Viral Click-worthy Title",
  "description": "Engaging description with timestamps, summary, and hashtags",
  "tags": ["tag1", "tag2", "tag3"],
  "call_to_action": "Subscribe for more insights!",
  "contains_synthetic_media": true,
  "estimated_total_duration": 45.0,
  "scenes": [
    {
      "scene_id": 1,
      "narration": "What if I told you the world's most powerful AI wasn't built by a tech giant?",
      "visual_description": "Cinematic shot of glowing neural network pulses across a dark digital globe",
      "search_keywords": ["artificial intelligence", "glowing network", "futuristic tech"],
      "estimated_duration": 5.0
    }
  ]
}
"""

class ScriptGenerator:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider or config.llm_provider
        self.model = model or config.llm_model

    def generate_script(self, topic: str, format_type: Literal["short", "long"] = "short") -> VideoScript:
        logger.info(f"Generating {format_type} script for topic: '{topic}' via provider: {self.provider}")
        
        # 1. Try Gemini
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            try:
                return self._generate_gemini(topic, format_type, gemini_api_key)
            except Exception as e:
                logger.warning(f"Gemini generation failed: {e}. Falling back...")

        # 2. Try OpenAI / DeepSeek / Ollama compatible
        openai_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        if openai_api_key or os.getenv("OLLAMA_HOST"):
            try:
                return self._generate_openai_compatible(topic, format_type)
            except Exception as e:
                logger.warning(f"OpenAI/Ollama generation failed: {e}. Falling back...")

        # 3. Deterministic High-Quality Fallback Engine (runs offline without API keys)
        logger.info("Using built-in deterministic Script Engine for instant testing.")
        return self._generate_fallback(topic, format_type)

    def _generate_gemini(self, topic: str, format_type: str, api_key: str) -> VideoScript:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = f"Write a complete viral YouTube {format_type} script about: '{topic}'."
        response = client.models.generate_content(
            model=self.model if "gemini" in self.model else "gemini-1.5-flash",
            contents=f"{SYSTEM_PROMPT}\n\n{prompt}",
            config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        return VideoScript(**data)

    def _generate_openai_compatible(self, topic: str, format_type: str) -> VideoScript:
        from openai import OpenAI
        base_url = os.getenv("OPENAI_BASE_URL")  # Can be Ollama http://localhost:11434/v1 or DeepSeek
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or "ollama"
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        prompt = f"Write a complete viral YouTube {format_type} script about: '{topic}'."
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        return VideoScript(**data)

    def _generate_fallback(self, topic: str, format_type: str) -> VideoScript:
        clean_topic = topic.strip().capitalize()
        if format_type == "short":
            scenes = [
                Scene(
                    scene_id=1,
                    narration=f"Here is the mind-blowing truth about {clean_topic} that almost nobody talks about.",
                    visual_description=f"Dramatic cinematic opening showcasing {clean_topic} with striking lighting",
                    search_keywords=[clean_topic, "technology", "abstract light"],
                    estimated_duration=4.5
                ),
                Scene(
                    scene_id=2,
                    narration=f"Most people believe {clean_topic} is simple, but recent breakthroughs have completely flipped the script.",
                    visual_description=f"Fast-paced futuristic data visualization representing evolution of {clean_topic}",
                    search_keywords=["futuristic screen", "digital transformation", "data stream"],
                    estimated_duration=5.0
                ),
                Scene(
                    scene_id=3,
                    narration=f"In fact, industry pioneers are already leveraging this to achieve 10 times better results in record time.",
                    visual_description="High-tech modern office and robotics working at ultra-fast speed",
                    search_keywords=["robotics", "modern technology", "success"],
                    estimated_duration=5.0
                ),
                Scene(
                    scene_id=4,
                    narration=f"Would you use this breakthrough today? Hit subscribe and drop your thoughts in the comments below!",
                    visual_description="Sleek glowing subscribe button and mobile smartphone interface",
                    search_keywords=["smartphone", "digital media", "neon subscribe"],
                    estimated_duration=4.5
                )
            ]
            return VideoScript(
                topic=topic,
                format_type="short",
                title=f"The Shocking Truth About {clean_topic}! #Shorts",
                description=f"Discover the hidden reality behind {clean_topic}. Don't forget to like and subscribe for more daily insights! #Shorts #{clean_topic.replace(' ', '')}",
                tags=["Shorts", clean_topic, "Education", "Viral", "Technology"],
                call_to_action="Subscribe for daily breakthrough facts!",
                contains_synthetic_media=True,
                estimated_total_duration=19.0,
                scenes=scenes
            )
        else:
            scenes = [
                Scene(
                    scene_id=1,
                    narration=f"Welcome back! Today we are doing a deep dive into {clean_topic}, and why it matters more than ever in 2026.",
                    visual_description=f"Cinematic wide angle drone shot introducing {clean_topic}",
                    search_keywords=[clean_topic, "aerial landscape", "cinematic tech"],
                    estimated_duration=6.0
                ),
                Scene(
                    scene_id=2,
                    narration=f"To understand the real impact of {clean_topic}, we first have to look at the foundational principles that make it work.",
                    visual_description="Detailed architectural blueprint and circuit analysis",
                    search_keywords=["blueprint", "engineering", "circuit board"],
                    estimated_duration=7.5
                ),
                Scene(
                    scene_id=3,
                    narration=f"When applied effectively, {clean_topic} creates compounding advantages that transform productivity and operational speed.",
                    visual_description="Dynamic graph climbing upwards with glowing light trails",
                    search_keywords=["growth chart", "exponential success", "data analytics"],
                    estimated_duration=7.0
                ),
                Scene(
                    scene_id=4,
                    narration="If you found this breakdown valuable, make sure to hit that like button, subscribe, and let me know your perspective in the comments.",
                    visual_description="Clean studio background with channel branding and animated social links",
                    search_keywords=["youtube studio", "subscribe bell", "content creator"],
                    estimated_duration=6.0
                )
            ]
            return VideoScript(
                topic=topic,
                format_type="long",
                title=f"{clean_topic} Explained: The Complete Guide & Breakthroughs",
                description=f"A complete comprehensive breakdown of {clean_topic}. Timestamps:\n0:00 - Introduction\n0:30 - Core Fundamentals\n1:45 - Key Advantages\n3:00 - Conclusion\n\nSubscribe for more in-depth analyses!",
                tags=[clean_topic, "Explained", "Documentary", "Technology", "Guide"],
                call_to_action="Subscribe to stay ahead of future technology!",
                contains_synthetic_media=True,
                estimated_total_duration=26.5,
                scenes=scenes
            )
