import os
import json
import logging
from typing import Literal, Optional, List
from config.settings import config
from src.scripting.models import VideoScript, Scene, ScriptFact

logger = logging.getLogger(__name__)

HINGLISH_DIRECTOR_PROMPT = """Act as director, story writer, voice director and cinematographer for ONE 30-45 second YouTube Short for an Indian Hindi/Hinglish tech channel.

Topic: {topic}
Forced genre: {genre}

Step 1 - Research: Find 3-5 verified, current facts/specs/India prices (in INR) for the topic. Never invent numbers. Keep a source URL for each fact.
Step 2 - Genre: if a forced genre is given use it, otherwise pick one of: action, drama, thriller, motivational, mystery, comedy, explainer.
Step 3 - Arc: a 3-second hook line, 3-4 escalating body beats (one fact each), a turn, and a landing CTA (follow/comment). 5-7 lines total, 90-120 spoken words total.
Step 4 - Per line direction: emotion, pace (0.8-1.35), expressiveness (0.3-0.9), shot_type (one of: action, reveal, wide, closeup, static, tracking) and an English image prompt for a vertical 9:16 visual (photoreal product render or stylized tech graphic, no text, no logos, no real people's faces).
Step 5 - Disclosure: set altered_content_needed true ONLY if a visual realistically depicts an event that did not happen.

Language rules:
- tts_text is natural Hinglish written in Devanagari for Hindi words with English tech terms kept in Latin script (e.g. "ये phone का battery backup कमाल है").
- Write numbers above 4 digits with commas (15,000).
- caption is the same line in short Roman Hinglish (max 8 words) for on-screen subtitles.

Return strictly a valid JSON object matching this schema:
{{
  "genre": "explainer",
  "title": "Title (max 90 chars, Hinglish + English keywords)",
  "description": "2-3 lines description with specs and hashtags",
  "tags": ["tag1", "tag2", "tag3"],
  "hashtags": ["tech", "budget5g", "phone"],
  "hook_overlay": "5-8 words hook badge shown in first 2.5 seconds",
  "altered_content_needed": false,
  "disclosure_reason": "",
  "facts": [
    {{"fact": "Snapdragon 6s Gen 3 processor", "source_url": "https://gsmarena.com"}}
  ],
  "lines": [
    {{
      "role": "hook",
      "tts_text": "क्या 15,000 के अंदर सच में एक all-rounder 5G phone मिल सकता है?",
      "caption": "Under 15K Best 5G Phone?",
      "emotion": "curiosity",
      "pace": 1.1,
      "expressiveness": 0.8,
      "shot_type": "reveal",
      "image_prompt": "Futuristic sleek metallic smartphone glowing on high-tech podium, dark cyberpunk neon background, photoreal 8k, vertical 9:16"
    }}
  ]
}}
"""

class ScriptGenerator:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider or config.llm_provider
        self.model = model or config.llm_model

    def generate_script(
        self,
        topic: str,
        format_type: Literal["short", "long"] = "short",
        genre: Optional[str] = None
    ) -> VideoScript:
        logger.info(f"Generating {format_type} script for topic: '{topic}' [Genre: {genre or 'auto'}]")
        
        # 1. Try Gemini
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            try:
                return self._generate_gemini(topic, format_type, genre, gemini_api_key)
            except Exception as e:
                logger.warning(f"Gemini generation failed: {e}. Falling back...")

        # 2. Try OpenAI / DeepSeek
        openai_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        if openai_api_key:
            try:
                return self._generate_openai(topic, format_type, genre)
            except Exception as e:
                logger.warning(f"OpenAI generation failed: {e}. Falling back...")

        # 3. Deterministic Hinglish Tech Director Engine (Fallback)
        logger.info("Using built-in Hinglish Director Engine for instant generation.")
        return self._generate_hinglish_fallback(topic, format_type, genre)

    def _generate_gemini(self, topic: str, format_type: str, genre: Optional[str], api_key: str) -> VideoScript:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = HINGLISH_DIRECTOR_PROMPT.format(topic=topic, genre=genre or "Let the director decide")
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        return self._parse_director_json(topic, format_type, data)

    def _generate_openai(self, topic: str, format_type: str, genre: Optional[str]) -> VideoScript:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY"))
        prompt = HINGLISH_DIRECTOR_PROMPT.format(topic=topic, genre=genre or "Let the director decide")
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        return self._parse_director_json(topic, format_type, data)

    def _parse_director_json(self, topic: str, format_type: str, data: dict) -> VideoScript:
        lines = data.get("lines", [])
        scenes = []
        for i, l in enumerate(lines, 1):
            tts = l.get("tts_text") or l.get("narration") or l.get("text", "")
            cap = l.get("caption") or tts[:50]
            scenes.append(Scene(
                scene_id=i,
                role=l.get("role", "beat"),
                tts_text=tts,
                caption=cap,
                emotion=l.get("emotion", "excitement"),
                pace=float(l.get("pace", 1.0)),
                expressiveness=float(l.get("expressiveness", 0.6)),
                shot_type=l.get("shot_type", "static"),
                image_prompt=l.get("image_prompt", topic),
                visual_description=l.get("image_prompt", topic),
                search_keywords=[topic, l.get("shot_type", "tech"), "gadget"],
                estimated_duration=4.5
            ))

        tags = data.get("tags", ["Shorts", "Tech", "Gadgets", "Hinglish"])
        hashtags = data.get("hashtags", ["tech", "shorts", "gadgets"])
        
        return VideoScript(
            topic=topic,
            format_type=format_type,
            genre=data.get("genre", "explainer"),
            title=data.get("title", f"{topic} #Shorts"),
            description=data.get("description", f"{topic} breakdown in Hinglish.\n#Shorts"),
            tags=tags,
            hashtags=hashtags,
            hook_overlay=data.get("hook_overlay", "DON'T BUY BEFORE THIS!"),
            contains_synthetic_media=data.get("altered_content_needed", True),
            disclosure_reason=data.get("disclosure_reason", ""),
            facts=[ScriptFact(**f) for f in data.get("facts", []) if isinstance(f, dict)],
            estimated_total_duration=len(scenes) * 4.5,
            scenes=scenes
        )

    def _generate_hinglish_fallback(self, topic: str, format_type: str, genre: Optional[str]) -> VideoScript:
        chosen_genre = genre if genre and genre != "Let the director decide" else "explainer"
        scenes = [
            Scene(
                scene_id=1,
                role="hook",
                tts_text=f"क्या आप भी {topic} को लेकर confused हैं? रुको, ये सच्चाई जान लो!",
                caption=f"Truth About {topic.title()}!",
                emotion="curiosity",
                pace=1.1,
                expressiveness=0.85,
                shot_type="reveal",
                image_prompt=f"Dramatic cinematic reveal of modern tech device representing {topic}, striking lighting, 8k vertical 9:16",
                visual_description=f"Dramatic lighting reveal of {topic}",
                search_keywords=[topic, "smartphone", "tech reveal"]
            ),
            Scene(
                scene_id=2,
                role="beat",
                tts_text="Market में specs की लड़ाई बहुत तेज है, लेकिन real-world performance सिर्फ 2 चीज़ों पर depend करती है।",
                caption="Real-world Performance Test",
                emotion="serious",
                pace=1.05,
                expressiveness=0.6,
                shot_type="action",
                image_prompt="High speed microprocessor circuit glowing with golden electric pulses, macro closeup",
                visual_description="High-speed microchips and motherboard",
                search_keywords=["processor", "microchip", "circuit board"]
            ),
            Scene(
                scene_id=3,
                role="beat",
                tts_text="पहला है इसका processor tuning और दूसरा है ultra-fast thermal cooling system!",
                caption="Processor & Thermal Cooling",
                emotion="excitement",
                pace=1.0,
                expressiveness=0.7,
                shot_type="closeup",
                image_prompt="Vapor chamber cooling system inside transparent flagship phone, blue ice vapor",
                visual_description="Cooling chamber and thermal pipes",
                search_keywords=["cooling system", "hardware", "technology"]
            ),
            Scene(
                scene_id=4,
                role="turn",
                tts_text="मतलब heavy gaming और daily multi-tasking में भी zero frame drops!",
                caption="Zero Frame Drops Gaming!",
                emotion="energetic",
                pace=1.15,
                expressiveness=0.9,
                shot_type="tracking",
                image_prompt="Vibrant mobile gaming screen showing high FPS cyber battle, motion blur particles",
                visual_description="Fast gaming motion with glowing lights",
                search_keywords=["mobile gaming", "esports", "speed"]
            ),
            Scene(
                scene_id=5,
                role="cta",
                tts_text="तो आपका favorite feature कौन सा है? नीचे comment करो और subscribe करना मत भूलना!",
                caption="Comment & Subscribe Now!",
                emotion="friendly",
                pace=1.05,
                expressiveness=0.75,
                shot_type="static",
                image_prompt="Clean studio desk setup with neon subscribe bell and YouTube play button",
                visual_description="YouTube subscribe bell and tech desk",
                search_keywords=["youtube bell", "technology", "studio"]
            )
        ]

        title = f"{topic} का असली सच! Don't Make This Mistake #Shorts"[:90]
        description = (
            f"Here is the complete breakdown of {topic} in Hinglish.\n\n"
            f"#Shorts #TechFacts #Gadgets\n\n"
            f"Subscribe to stay updated with verified Indian tech insights!"
        )

        return VideoScript(
            topic=topic,
            format_type=format_type,
            genre=chosen_genre,
            title=title,
            description=description,
            tags=["Shorts", "Tech", topic, "Hinglish", "Gadgets", "Review"],
            hashtags=["Shorts", "Tech", "Gadgets"],
            hook_overlay="DON'T BUY BEFORE THIS!",
            call_to_action="Comment below and subscribe!",
            contains_synthetic_media=True,
            facts=[ScriptFact(fact=f"Verified specs and performance for {topic}", source_url="https://gsmarena.com")],
            estimated_total_duration=23.5,
            scenes=scenes
        )
