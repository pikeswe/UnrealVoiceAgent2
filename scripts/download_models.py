"""Utility script to fetch the required models for offline use.

If the Hugging Face download stalls or fails, the script falls back to
cloning the official Kani-TTS GitHub repository and copies its weights
into the requested ``--output`` directory.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from huggingface_hub import snapshot_download

OFFICIAL_KANI_REPO = "https://github.com/nineninesix-ai/kani-tts.git"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download LLM and TTS assets")
    default_llm_repo = "Qwen/Qwen3-4B-Instruct-2507"
    parser.add_argument(
        "--llm",
        type=str,
        default=default_llm_repo,
        help=(
            "Model repo id for the LLM (default: Qwen/Qwen3-4B-Instruct-2507). "
            "Example: --llm Qwen/Qwen3-4B-Instruct-2507"
        ),
    )
    parser.add_argument("--tts", type=str, default="nineninesix/kani-tts-370m-MLX", help="Model repo id for the TTS checkpoint")
    parser.add_argument("--output", type=Path, default=Path("models"), help="Destination directory")
    parser.add_argument("--revision", type=str, default="main", help="Specific revision to download")
    parser.add_argument("--tts-revision", type=str, default="main", help="Specific revision of the TTS repo")
    parser.add_argument("--skip-tts", action="store_true", help="Only download the LLM assets")
    return parser.parse_args()


def try_snapshot_download(*, repo_id: str, revision: str, destination: Path) -> bool:
    try:
        snapshot_download(
            repo_id=repo_id,
            revision=revision,
            local_dir=str(destination),
            local_dir_use_symlinks=False,
        )
        return True
    except Exception as exc:  # pragma: no cover - network failure path
        print(f"[warn] Hugging Face download failed for {repo_id}: {exc}")
        return False


def _git_clone_with_progress(repo_url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        print(f"[info] Repository already present at {destination}, skipping clone.")
        return

    print(f"[info] Cloning {repo_url} into {destination} ...")
    process = subprocess.Popen(
        ["git", "clone", "--depth", "1", "--progress", repo_url, str(destination)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    last_update = time.time()
    line_counter = 0
    assert process.stdout is not None
    try:
        for line in process.stdout:
            line_counter += 1
            line = line.strip()
            if not line:
                continue
            if "%" in line or "Checking out files" in line or time.time() - last_update > 5:
                print(f"[git] {line}")
                last_update = time.time()
            elif line_counter % 20 == 0:
                print(f"[git] {line}")
    finally:
        process.stdout.close()

    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"git clone failed with exit code {return_code}")

    file_count = sum(1 for path in destination.rglob("*") if path.is_file())
    print(f"[info] Clone complete. Retrieved {file_count} files from {repo_url}.")


def _copy_tree(source: Path, destination: Path) -> None:
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def _clone_kani_repo_into_models(output_dir: Path) -> None:
    repo_root = project_root() / "external" / "kani-tts"
    _git_clone_with_progress(OFFICIAL_KANI_REPO, repo_root)

    source_models = repo_root / "models" / "kani_tts"
    if not source_models.exists():
        raise FileNotFoundError(
            f"Kani-TTS repository cloned to {repo_root} but models/kani_tts was not found."
        )

    destination = output_dir / "kani_tts"
    if destination.exists():
        print(f"[info] Syncing fallback models into existing directory {destination}.")
    else:
        destination.mkdir(parents=True, exist_ok=True)

    _copy_tree(source_models, destination)
    print(f"[info] Copied fallback Kani-TTS weights into {destination}.")


def main() -> None:
    args = parse_args()
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    llm_repo_id = args.llm
    llm_dir_name = llm_repo_id.split("/")[-1] if llm_repo_id else "llm"
    llm_dir = output_dir / "llm" / llm_dir_name
    llm_dir.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=llm_repo_id,
        revision=args.revision,
        local_dir=str(llm_dir),
        local_dir_use_symlinks=False,
    )

    if not args.skip_tts and args.tts:
        tts_destination = output_dir / "kani_tts"
        success = try_snapshot_download(
            repo_id=args.tts,
            revision=args.tts_revision,
            destination=tts_destination,
        )
        if not success:
            try:
                _clone_kani_repo_into_models(output_dir)
            except Exception as exc:  # pragma: no cover - network path
                print(
                    "[error] Failed to clone the official Kani-TTS repository as a fallback:\n"
                    f"        {exc}"
                )
                sys.exit(1)

    print(
        f"Download complete. Point config/default_config.json -> llm.model_name_or_path to: {llm_dir}"
    )

if __name__ == "__main__":
    main()
