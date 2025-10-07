#!/usr/bin/env python3
"""Smoketest utility for the Kani-TTS engine.

Usage:
    python scripts/tts_smoketest.py --text "Hello there" --out output.wav

Loads the project's default configuration, runs the Kani text-to-speech engine
for the provided text, and writes a PCM16 WAV file to the requested location.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from TTS.kani_engine import KaniTTSEngine
from Utils.config import load_orchestrator_config

DEFAULT_CONFIG = Path("config/default_config.json")


class AudioGenerationError(RuntimeError):
    """Raised when the TTS engine fails to generate audio."""


async def _synthesize(text: str, output_path: Path, config_path: Path) -> None:
    orchestrator_config = load_orchestrator_config(config_path)
    tts_config = orchestrator_config.tts

    engine = KaniTTSEngine(tts_config)
    await engine.load()

    audio_frames = bytearray()
    async for chunk in engine.synthesize_stream(text):
        audio_frames.extend(chunk)

    if not audio_frames:
        raise AudioGenerationError(
            "Kani-TTS produced no audio frames for the supplied text."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # PCM16
        wav_file.setframerate(tts_config.sample_rate)
        wav_file.writeframes(bytes(audio_frames))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", required=True, help="Text to synthesise")
    parser.add_argument("--out", required=True, type=Path, help="Output WAV file path")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to orchestrator config (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Logging verbosity",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))

    if not args.text.strip():
        print("Error: --text must not be empty.", file=sys.stderr)
        raise SystemExit(1)

    if not args.config.exists():
        print(f"Error: config file '{args.config}' does not exist.", file=sys.stderr)
        raise SystemExit(1)

    try:
        asyncio.run(_synthesize(args.text, args.out, args.config))
    except AudioGenerationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
