"""Wrapper for the Kani-TTS synthesiser with streaming output."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import AsyncIterator, Optional

import numpy as np

from TTS.kani_tts import KaniSynthesizer
from TTS.kani_tts.model_utils import resolve_model_directory


logger = logging.getLogger(__name__)


class KaniTTSConfig:
    """Configuration for the Kani-TTS wrapper."""

    def __init__(
        self,
        model_dir: Path,
        voice: str = "kari",
        sample_rate: int = 24000,
        chunk_size: int = 1024,
        temperature: float = 0.8,
    ) -> None:
        self.model_dir = model_dir
        self.voice = voice
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.temperature = temperature


class KaniTTSEngine:
    """Provides streaming synthesis using the open-source Kani-TTS models."""

    def __init__(self, config: KaniTTSConfig):
        self.config = config
        self._synth: Optional[KaniSynthesizer] = None

    async def load(self) -> None:

        resolved_model_dir = resolve_model_directory(self.config.model_dir, log=logger)
        logger.info("Loading Kani-TTS models from %s", resolved_model_dir)
        self._synth = KaniSynthesizer(
            model_path=str(resolved_model_dir),
            voice=self.config.voice,
            sample_rate=self.config.sample_rate,
            chunk_size=self.config.chunk_size,
        )
        logger.info("Kani-TTS ready with voice '%s'", self.config.voice)

    @property
    def is_ready(self) -> bool:
        return self._synth is not None

    async def synthesize_stream(
        self,
        text: str,
        *,
        sample_rate: Optional[int] = None,
        temperature: Optional[float] = None,
        chunk_size: Optional[int] = None,
    ) -> AsyncIterator[bytes]:
        """Generates PCM16 audio chunks for the supplied text."""
        if not self.is_ready:
            raise RuntimeError("KaniTTSEngine.synthesize_stream called before load().")

        assert self._synth is not None

        stream_sample_rate = sample_rate or self.config.sample_rate
        stream_temperature = temperature if temperature is not None else self.config.temperature
        stream_chunk_size = chunk_size or self.config.chunk_size

        stream = self._synth.stream(  # type: ignore[attr-defined]
            text=text,
            sample_rate=stream_sample_rate,
            temperature=stream_temperature,
            chunk_size=stream_chunk_size,
        )

        if hasattr(stream, "__aiter__"):
            async for chunk in stream:  # type: ignore[assignment]
                if isinstance(chunk, np.ndarray):
                    yield chunk.tobytes()
                else:
                    yield bytes(chunk)
        else:
            for chunk in stream:  # type: ignore[assignment]
                if isinstance(chunk, np.ndarray):
                    yield chunk.tobytes()
                else:
                    yield bytes(chunk)

    async def synthesize_to_file(self, text: str, output_path: Path) -> Path:
        """Synthesise the provided text to a WAV file on disk."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio_data = bytearray()
        async for chunk in self.synthesize_stream(text):
            audio_data.extend(chunk)
        output_path.write_bytes(bytes(audio_data))
        return output_path
