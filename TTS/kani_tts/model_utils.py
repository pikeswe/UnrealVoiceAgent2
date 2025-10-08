"""Utilities to resolve the local Kani-TTS model directory.

This module keeps the runtime code resilient when the Hugging Face
checkpoint is unavailable.  It inspects the configured model directory,
falls back to the vendored `external/kani-tts` checkout when necessary,
and emits helpful log messages that describe what happened.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

_REQUIRED_MANIFEST_FILES: tuple[str, ...] = (
    "config.json",
    "generation_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
)


def _has_weight_files(directory: Path) -> bool:
    """Return ``True`` when the folder contains any model weight files."""
    for pattern in ("*.safetensors", "*.bin", "*.pt"):
        if any(directory.glob(pattern)):
            return True
    return False


def describe_directory_status(directory: Path) -> str:
    """Return a human readable description of why ``directory`` is incomplete."""
    missing: list[str] = []
    for filename in _REQUIRED_MANIFEST_FILES:
        if not (directory / filename).exists():
            missing.append(filename)

    weight_state = "found" if _has_weight_files(directory) else "missing"
    parts = []
    if missing:
        parts.append(f"missing files: {', '.join(sorted(missing))}")
    parts.append(f"weights: {weight_state}")
    return "; ".join(parts)


def is_model_dir_complete(model_dir: Path) -> bool:
    """Check whether the supplied directory contains a usable checkpoint."""
    directory = model_dir.expanduser()
    if not directory.exists() or not directory.is_dir():
        return False

    for filename in _REQUIRED_MANIFEST_FILES:
        if not (directory / filename).exists():
            return False

    if not _has_weight_files(directory):
        return False

    return True


def project_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[2]


def external_repo_dir() -> Path:
    """Directory where the official Kani-TTS repository should live."""
    return project_root() / "external" / "kani-tts"


def external_model_dir() -> Path:
    """Directory that contains the fallback model weights within the repo clone."""
    return external_repo_dir() / "models" / "kani_tts"


def _normalise(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except Exception:  # pragma: no cover - extremely defensive
        return path


def _candidate_directories(preferred: Path) -> Iterable[Path]:
    expanded = preferred.expanduser()
    candidates = [expanded]

    if not expanded.is_absolute():
        root = project_root()
        candidates.append(_normalise(root / expanded))
        candidates.append(_normalise(Path.cwd() / expanded))

    seen: set[Path] = set()
    for candidate in candidates:
        candidate = _normalise(candidate)
        if candidate not in seen:
            seen.add(candidate)
            yield candidate


def resolve_model_directory(preferred: Path, *, log: logging.Logger | None = None) -> Path:
    """Resolve the best available directory for the Kani-TTS model.

    The function checks ``preferred`` (along with useful absolute variants)
    and falls back to ``external/kani-tts/models/kani_tts`` when the primary
    location is missing or obviously incomplete.
    """
    logger_obj = log or logger

    for candidate in _candidate_directories(preferred):
        if is_model_dir_complete(candidate):
            return candidate

    fallback = external_model_dir()
    if is_model_dir_complete(fallback):
        logger_obj.warning(
            "Primary Kani-TTS model directory '%s' missing or incomplete; "
            "using fallback '%s'.",
            preferred,
            fallback,
        )
        return fallback

    if fallback.exists():
        logger_obj.debug(
            "Kani-TTS fallback directory '%s' exists but is incomplete (%s).",
            fallback,
            describe_directory_status(fallback),
        )

    # Fall back to the first candidate even if incomplete so the caller can
    # surface a clearer error message to the user or trigger a download.
    return _normalise(next(_candidate_directories(preferred)))


def resolve_model_reference(reference: str | Path, *, log: logging.Logger | None = None) -> str:
    """Return the string that should be passed to ``from_pretrained``."""
    logger_obj = log or logger
    resolved = resolve_model_directory(Path(str(reference)), log=logger_obj)
    if is_model_dir_complete(resolved):
        return str(resolved)
    return str(reference)
