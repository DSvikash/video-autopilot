import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

class SubtitleGenerator:
    """
    Generates high-retention viral style .ass and .srt subtitles
    with word-level timing and high-contrast YouTube Shorts typography.
    """
    def __init__(self, font_name: str = "Arial", font_size: int = 24, is_short: bool = True):
        self.font_name = font_name
        self.font_size = font_size if is_short else 18
        self.is_short = is_short
        # Safe margins so YouTube Shorts UI doesn't obscure the text
        self.margin_v = 220 if is_short else 80

    def generate_ass(self, segments: List[Dict[str, Any]], output_path: str) -> str:
        """
        Takes segments with start, end, text, and creates a styled .ass subtitle file.
        Each segment can be a 2-4 word punchy phrase or sentence chunk.
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        res_x = 1080 if self.is_short else 1920
        res_y = 1920 if self.is_short else 1080
        font_size = 54 if self.is_short else 42

        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {res_x}
PlayResY: {res_y}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.font_name},{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,40,40,{self.margin_v},1
Style: Highlight,{self.font_name},{font_size},&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,40,40,{self.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogue_lines = []
        for seg in segments:
            start_str = self._format_timestamp_ass(seg["start"])
            end_str = self._format_timestamp_ass(seg["end"])
            text = seg["text"].strip().upper()  # Uppercase increases viewer retention on Shorts
            
            # Escape curly brackets
            clean_text = text.replace("{", "").replace("}", "")
            dialogue_lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{clean_text}")

        full_content = ass_header + "\n".join(dialogue_lines) + "\n"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_content)

        return str(output_file)

    def generate_from_submaker(self, submaker: Any, output_path: str) -> str:
        """
        Converts edge-tts SubMaker output into chunked high-retention segments and writes .ass file.
        """
        srt_content = submaker.get_srt()
        segments = self._parse_srt_to_segments(srt_content)
        return self.generate_ass(segments, output_path)

    def _parse_srt_to_segments(self, srt_text: str) -> List[Dict[str, Any]]:
        entries = re.split(r'\n\s*\n', srt_text.strip())
        segments = []
        for entry in entries:
            lines = entry.strip().split('\n')
            if len(lines) >= 3:
                time_line = lines[1]
                match = re.match(r'(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)', time_line)
                if match:
                    start_sec = self._srt_time_to_seconds(match.group(1))
                    end_sec = self._srt_time_to_seconds(match.group(2))
                    text = " ".join(lines[2:])
                    segments.append({
                        "start": start_sec,
                        "end": end_sec,
                        "text": text
                    })
        return segments

    def _srt_time_to_seconds(self, srt_time: str) -> float:
        parts = srt_time.replace(',', ':').split(':')
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        millis = float(parts[3])
        return hours * 3600 + minutes * 60 + seconds + (millis / 1000.0)

    def _format_timestamp_ass(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int(round((seconds - int(seconds)) * 100))
        if centis >= 100:
            centis = 99
        return f"{hours:01d}:{minutes:02d}:{secs:02d}.{centis:02d}"
