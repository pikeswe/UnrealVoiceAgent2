"""Minimal Normalizer stub used when pynini-backed pipelines are unavailable."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Normalizer:
    """No-op text normalizer compatible with NeMo's interface."""

    lang: str | None = None
    input_case: str | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.lang = kwargs.get("lang")
        self.input_case = kwargs.get("input_case")

    def normalize(self, text: str, **kwargs: Any) -> str:
        """Return the text unchanged while preserving interface compatibility."""

        return text


__all__ = ["Normalizer"]
