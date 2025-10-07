import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from TTS.kani_engine import KaniTTSConfig, KaniTTSEngine
from TTS.kani_tts.synthesizer import KaniSynthesizer


class DummyGenerator:
    def __init__(self, captured):
        self.captured = captured

    def generate(self, text, writer, **kwargs):
        self.captured["generate_text"] = text
        self.captured["generate_kwargs"] = kwargs
        writer.audio_chunks.append(np.zeros(4, dtype=np.float32))


class DummyWriter:
    def __init__(self, player, output_file, *, sample_rate, chunk_size, lookback_frames, captured):
        captured["writer_sample_rate"] = sample_rate
        captured["writer_chunk_size"] = chunk_size
        captured["writer_lookback"] = lookback_frames
        self.player = player
        self.output_file = output_file
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.lookback_frames = lookback_frames
        self.audio_chunks = []
        self.started = False
        self.finalized = False

    def start(self):
        self.started = True

    def finalize(self):
        self.finalized = True


def test_engine_stream_forwards_configuration(monkeypatch, tmp_path):
    config = KaniTTSConfig(model_dir=tmp_path, sample_rate=16000, chunk_size=512, temperature=0.7)
    engine = KaniTTSEngine(config)

    class DummySynth:
        def stream(self, *, text, sample_rate, temperature, chunk_size):
            assert text == "hello"
            assert sample_rate == 16000
            assert temperature == 0.7
            assert chunk_size == 512
            yield b"abc"

    engine._synth = DummySynth()

    async def _collect():
        return [chunk async for chunk in engine.synthesize_stream("hello")]

    chunks = asyncio.run(_collect())

    assert chunks == [b"abc"]


def test_synthesizer_stream_accepts_overrides(monkeypatch):
    captured = {}
    synth = KaniSynthesizer(sample_rate=24000, chunk_size=1024, lookback_frames=4)

    def fake_load(self):
        self._player = SimpleNamespace()
        self._generator = DummyGenerator(captured)

    monkeypatch.setattr(KaniSynthesizer, "load", fake_load)

    monkeypatch.setattr(
        "TTS.kani_tts.synthesizer.StreamingAudioWriter",
        lambda player, output_file, *, sample_rate, chunk_size, lookback_frames: DummyWriter(
            player,
            output_file,
            sample_rate=sample_rate,
            chunk_size=chunk_size,
            lookback_frames=lookback_frames,
            captured=captured,
        ),
    )

    stream = synth.stream(
        "hello",
        sample_rate=16000,
        chunk_size=256,
        lookback_frames=2,
        temperature=0.5,
    )

    chunk = next(stream)
    assert isinstance(chunk, bytes)

    with pytest.raises(StopIteration):
        next(stream)

    assert captured["generate_text"] == "hello"
    assert captured["generate_kwargs"]["temperature"] == 0.5
    assert captured["writer_sample_rate"] == 16000
    assert captured["writer_chunk_size"] == 256
    assert captured["writer_lookback"] == 2
