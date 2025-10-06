"""High level synthesizer API exposed to the rest of the project."""
from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Generator, Iterable, Optional

import numpy as np

from . import config
from .audio import LLMAudioPlayer, StreamingAudioWriter
from .generation import TTSGenerator


class KaniSynthesizer:
    """Wraps the original Kani-TTS reference implementation."""

    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        voice: str | None = None,
        sample_rate: int | None = None,
        chunk_size: int | None = None,
        lookback_frames: int | None = None,
    ) -> None:
        self.model_path = str(model_path) if model_path else config.MODEL_NAME
        self.voice = voice or "kari"
        self.sample_rate = sample_rate or config.SAMPLE_RATE
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.lookback_frames = lookback_frames or config.LOOKBACK_FRAMES

        self._generator: Optional[TTSGenerator] = None
        self._player: Optional[LLMAudioPlayer] = None

    def load(self) -> None:
        if self._generator is None:
            self._generator = TTSGenerator(model_name=self.model_path)
        if self._player is None:
            self._player = LLMAudioPlayer(self._generator.tokenizer)

    def stream(
        self,
        text: str,
        *,
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterable[bytes]:
        if not text:
            return iter(())

        self.load()
        assert self._generator is not None
        assert self._player is not None

        chunk_queue: "queue.Queue[tuple[str, Optional[np.ndarray] | Optional[str]]]" = queue.Queue()

        class _ChunkList(list):
            def append(self, chunk: np.ndarray) -> None:  # type: ignore[override]
                super().append(chunk)
                chunk_queue.put(("chunk", chunk))

        writer = StreamingAudioWriter(
            self._player,
            output_file=None,
            sample_rate=self.sample_rate,
            chunk_size=self.chunk_size,
            lookback_frames=self.lookback_frames,
        )
        writer.audio_chunks = _ChunkList()  # type: ignore[assignment]

        def _generate() -> None:
            try:
                writer.start()
                self._generator.generate(
                    text,
                    writer,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
                writer.finalize()
                chunk_queue.put(("done", None))
            except Exception as exc:  # pragma: no cover - propagation
                chunk_queue.put(("error", str(exc)))

        thread = threading.Thread(target=_generate, daemon=True)
        thread.start()

        def _pcm_chunks() -> Generator[bytes, None, None]:
            while True:
                message, payload = chunk_queue.get()
                if message == "chunk":
                    assert isinstance(payload, np.ndarray)
                    pcm_data = np.clip(payload, -1.0, 1.0)
                    yield (pcm_data * 32767).astype(np.int16).tobytes()
                elif message == "done":
                    break
                elif message == "error":
                    raise RuntimeError(payload or "KaniSynthesizer failed")

        return _pcm_chunks()
