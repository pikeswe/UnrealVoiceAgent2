"""Windows compatibility helpers for NeMo text processing."""
from __future__ import annotations

import importlib
import logging
import os
import sys
from pathlib import Path
from types import ModuleType

_LOGGER = logging.getLogger(__name__)
_STUB_PACKAGE = "nemo_text_processing"


def _stub_directory() -> Path:
    """Return the repository's stub directory."""

    module_dir = Path(__file__).resolve().parent
    repo_root = module_dir.parent
    return repo_root / "stubs"


def _load_stub_module(stub_dir: Path) -> ModuleType:
    """Import the bundled nemo_text_processing stub package."""

    if not stub_dir.exists():
        raise RuntimeError(
            "Missing nemo_text_processing stub directory. Expected at "
            f"{stub_dir}"
        )

    stub_path = str(stub_dir)
    if stub_path not in sys.path:
        sys.path.insert(0, stub_path)

    if _STUB_PACKAGE in sys.modules:
        del sys.modules[_STUB_PACKAGE]

    module = importlib.import_module(_STUB_PACKAGE)
    _LOGGER.info(
        "Falling back to bundled nemo_text_processing stub for Windows compatibility."
    )
    return module


def _should_use_stub(exc: ImportError) -> bool:
    """Decide whether to fall back to the stub implementation."""

    message = f"{exc}".lower()
    return "pynini" in message or os.name == "nt"


def ensure_windows_nemo_text_processing() -> None:
    """Ensure nemo_text_processing is importable on Windows without pynini."""

    if os.name != "nt":
        return

    stub_dir = _stub_directory()

    try:
        module = importlib.import_module(_STUB_PACKAGE)
    except ModuleNotFoundError:
        _load_stub_module(stub_dir)
        return
    except ImportError as exc:
        if _should_use_stub(exc):
            _load_stub_module(stub_dir)
            return
        raise

    if not hasattr(module, "Normalizer"):
        _load_stub_module(stub_dir)


__all__ = ["ensure_windows_nemo_text_processing"]
