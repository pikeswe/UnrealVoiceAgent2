"""Utilities to convert high-level emotion labels into Unreal-friendly payloads."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class EmotionMapper:
    """Translates textual emotions into slider payloads for MetaHuman animator."""

    emotion_map: Dict[str, Dict[str, float]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.emotion_map is None:
            self.emotion_map = {
                "Neutral": {
                    "Neutral": 0.8,
                    "Happy": 0.0,
                    "Sad": 0.0,
                    "Angry": 0.0,
                    "Disgust": 0.0,
                    "Fear": 0.0,
                    "Surprise": 0.0,
                },
                "Happy": {
                    "Neutral": 0.4,
                    "Happy": 1.0,
                    "Sad": 0.0,
                    "Angry": 0.0,
                    "Disgust": 0.0,
                    "Fear": 0.1,
                    "Surprise": 0.6,
                },
                "Sad": {
                    "Neutral": 0.5,
                    "Happy": 0.0,
                    "Sad": 1.0,
                    "Angry": 0.2,
                    "Disgust": 0.0,
                    "Fear": 0.4,
                    "Surprise": 0.0,
                },
                "Angry": {
                    "Neutral": 0.3,
                    "Happy": 0.0,
                    "Sad": 0.2,
                    "Angry": 1.0,
                    "Disgust": 0.3,
                    "Fear": 0.2,
                    "Surprise": 0.2,
                },
                "Disgust": {
                    "Neutral": 0.2,
                    "Happy": 0.0,
                    "Sad": 0.3,
                    "Angry": 0.4,
                    "Disgust": 1.0,
                    "Fear": 0.2,
                    "Surprise": 0.0,
                },
                "Fear": {
                    "Neutral": 0.4,
                    "Happy": 0.0,
                    "Sad": 0.4,
                    "Angry": 0.0,
                    "Disgust": 0.0,
                    "Fear": 1.0,
                    "Surprise": 0.8,
                },
                "Surprise": {
                    "Neutral": 0.3,
                    "Happy": 0.6,
                    "Sad": 0.0,
                    "Angry": 0.0,
                    "Disgust": 0.0,
                    "Fear": 0.6,
                    "Surprise": 1.0,
                },
            }

    def to_payload(self, emotion: str) -> Dict[str, float]:
        canonical = emotion.capitalize()
        return self.emotion_map.get(canonical, self.emotion_map["Neutral"])
