"""Utility script to fetch the required models for offline use."""
from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download LLM and TTS assets")
    parser.add_argument("--llm", type=str, default="Qwen/Qwen2.5-4B-Instruct", help="Model repo id for the LLM")
    parser.add_argument("--tts", type=str, default="nineninesix/kani-tts-370m-MLX", help="Model repo id for the TTS checkpoint")
    parser.add_argument("--output", type=Path, default=Path("models"), help="Destination directory")
    parser.add_argument("--revision", type=str, default="main", help="Specific revision to download")
    parser.add_argument("--tts-revision", type=str, default="main", help="Specific revision of the TTS repo")
    parser.add_argument("--skip-tts", action="store_true", help="Only download the LLM assets")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=args.llm,
        revision=args.revision,
        local_dir=str(output_dir / "llm"),
        local_dir_use_symlinks=False,
    )

    if not args.skip_tts and args.tts:
        snapshot_download(
            repo_id=args.tts,
            revision=args.tts_revision,
            local_dir=str(output_dir / "kani_tts"),
            local_dir_use_symlinks=False,
        )

    print("Download complete. Configure config/default_config.json to point to the new model paths.")

if __name__ == "__main__":
    main()
