"""Stub implementation of :mod:`nemo_text_processing` for Windows builds."""

print("[INFO] Using stubbed nemo_text_processing (pynini disabled).")

from .text_normalization.normalize import Normalizer  # noqa: E402

__all__ = ["Normalizer"]
