"""Audio player for LLM-generated speech tokens"""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from typing import TYPE_CHECKING, List
import numpy as np
import torch

from .. import config

from ..config import (
    TOKENIZER_LENGTH, START_OF_TEXT, END_OF_TEXT,
    START_OF_SPEECH, END_OF_SPEECH, START_OF_HUMAN, END_OF_HUMAN,
    START_OF_AI, END_OF_AI, PAD_TOKEN, AUDIO_TOKENS_START, CODEBOOK_SIZE
)


if TYPE_CHECKING:  # pragma: no cover - help static analysis without importing Nemo at runtime
    from nemo.collections.tts.models import AudioCodecModel  # noqa: F401

_OPTIONAL_MODULES = {
    "nemo": "nemo_toolkit[tts]",
    "lhotse": "lhotse==1.19.1",
    "sentencepiece": "sentencepiece>=0.2.0",
    "pandas": "pandas>=2.0.0",
}


_INSTALL_HINTS = {
    "nemo": (
        "pip install --extra-index-url https://pypi.nvidia.com "
        "nemo_toolkit[tts]"
    ),
    "lhotse": "pip install lhotse==1.19.1",
    "sentencepiece": "pip install sentencepiece>=0.2.0",
    "pandas": "pip install pandas>=2.0.0",
}


def _missing_optional_dependencies() -> List[str]:
    """Return pip requirement strings for optional modules that are absent."""

    missing: List[str] = []
    for module_name, requirement in _OPTIONAL_MODULES.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(requirement)
    return missing


def _install_instructions(missing: List[str]) -> str:
    """Return per-module install hints so Windows users avoid pynini build errors."""

    hints: List[str] = []
    for requirement in missing:
        module_name = next(
            (name for name, req in _OPTIONAL_MODULES.items() if req == requirement),
            None,
        )
        if module_name is None:
            continue
        hint = _INSTALL_HINTS.get(module_name)
        if hint is None:
            hint = f"pip install {requirement}"
        hints.append(f"  - {hint}")

    if not hints:
        return ""

    joined_hints = "\n".join(hints)
    return f"\nInstall the missing pieces with:\n{joined_hints}"

@lru_cache(maxsize=1)
def _load_audio_codec_model():  # pragma: no cover - heavy dependency
    """Import NeMo's ``AudioCodecModel`` lazily with clearer error messages."""

    missing = _missing_optional_dependencies()
    if missing:
        requirement_list = ", ".join(missing)
        hints = _install_instructions(missing)
        message = f"Missing dependencies for NeMo audio decoding: {requirement_list}."
        if hints:
            message = f"{message}{hints}"
        raise RuntimeError(message)


    try:
        from nemo.collections.tts.models import AudioCodecModel  # type: ignore
    except ImportError as exc:
        hint = _INSTALL_HINTS.get("nemo")
        install_msg = f" Install it via `{hint}` and retry." if hint else ""
        raise RuntimeError(
            "nemo_toolkit[tts] is required for audio decoding." + install_msg

        ) from exc

    return AudioCodecModel


class LLMAudioPlayer:
    def __init__(self, tokenizer) -> None:
        try:
            audio_codec_model = _load_audio_codec_model()
        except RuntimeError as exc:
            raise RuntimeError(str(exc)) from exc

        self.nemo_codec_model = audio_codec_model.from_pretrained(
            config.CODEC_MODEL_NAME
        ).eval()

        if torch.cuda.is_available():
            self.device = 'cuda'
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = 'mps'
        else:
            self.device = 'cpu'

        self.nemo_codec_model.to(self.device)
        self.tokenizer = tokenizer

        self.tokeniser_length = TOKENIZER_LENGTH
        self.start_of_text = START_OF_TEXT
        self.end_of_text = END_OF_TEXT
        self.start_of_speech = START_OF_SPEECH
        self.end_of_speech = END_OF_SPEECH
        self.start_of_human = START_OF_HUMAN
        self.end_of_human = END_OF_HUMAN
        self.start_of_ai = START_OF_AI
        self.end_of_ai = END_OF_AI
        self.pad_token = PAD_TOKEN
        self.audio_tokens_start = AUDIO_TOKENS_START
        self.codebook_size = CODEBOOK_SIZE

    def output_validation(self, out_ids):
        start_of_speech_flag = self.start_of_speech in out_ids
        end_of_speech_flag = self.end_of_speech in out_ids
        if not (start_of_speech_flag and end_of_speech_flag):
            raise ValueError('Special speech tokens not exist!')

    def get_nano_codes(self, out_ids):
        start_a_idx = (out_ids == self.start_of_speech).nonzero(as_tuple=True)[0].item()
        end_a_idx   = (out_ids == self.end_of_speech).nonzero(as_tuple=True)[0].item()
        if start_a_idx >= end_a_idx:
            raise ValueError('Invalid audio codes sequence!')

        audio_codes = out_ids[start_a_idx+1 : end_a_idx]
        if len(audio_codes) % 4:
            raise ValueError('The length of the sequence must be a multiple of 4!')
        audio_codes = audio_codes.reshape(-1, 4)
        audio_codes = audio_codes - torch.tensor([self.codebook_size * i for i in range(4)])
        audio_codes = audio_codes - self.audio_tokens_start
        if (audio_codes < 0).sum().item() > 0:
            raise ValueError('Invalid audio tokens!')

        audio_codes = audio_codes.T.unsqueeze(0)
        len_ = torch.tensor([audio_codes.shape[-1]])
        return audio_codes, len_

    def get_text(self, out_ids):
        try:
            start_t_idx = (out_ids == self.start_of_text).tolist().index(True)
            end_t_idx   = (out_ids == self.end_of_text).tolist().index(True)
            txt_tokens = out_ids[start_t_idx : end_t_idx+1]
            text = self.tokenizer.decode(txt_tokens, skip_special_tokens=True)
            return text
        except ValueError:
            return None

    def get_waveform(self, out_ids):
        out_ids = out_ids.flatten()
        self.output_validation(out_ids)
        audio_codes, len_ = self.get_nano_codes(out_ids)
        audio_codes, len_ = audio_codes.to(self.device), len_.to(self.device)
        with torch.inference_mode():
            reconstructed_audio, _ = self.nemo_codec_model.decode(tokens=audio_codes, tokens_len=len_)
            output_audio = reconstructed_audio.cpu().detach().numpy().squeeze()

        text = self.get_text(out_ids)
        return output_audio, text

    def decode_audio_chunk(self, audio_codes):
        """Decode a chunk of audio codes (shape: [num_frames, 4])"""
        if len(audio_codes) == 0:
            return None

        # Process audio codes: subtract offsets for each codebook
        audio_codes = torch.tensor(audio_codes, device=self.device)
        audio_codes = audio_codes - torch.tensor([self.codebook_size * i for i in range(4)], device=self.device)
        audio_codes = audio_codes - self.audio_tokens_start

        if (audio_codes < 0).sum().item() > 0:
            return None  # Invalid tokens, skip

        # Shape: (1, 4, num_frames) - batch_size=1, num_codebooks=4, num_frames
        audio_codes = audio_codes.T.unsqueeze(0)
        len_ = torch.tensor([audio_codes.shape[-1]], device=self.device)

        with torch.inference_mode():
            reconstructed_audio, _ = self.nemo_codec_model.decode(tokens=audio_codes, tokens_len=len_)
            output_audio = reconstructed_audio.cpu().detach().numpy().squeeze()

        return output_audio
