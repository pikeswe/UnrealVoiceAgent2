"""Core utilities for loading and running the local LLM."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from threading import Thread

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration parameters for :class:`LLMEngine`."""

    model_name_or_path: str
    type: str = "transformers"
    device: str = "cuda"
    max_new_tokens: int = 256
    temperature: float = 0.6
    top_p: float = 0.9
    repetition_penalty: float = 1.05
    system_prompt: str = (
        "You are Nova, an empathetic companion living inside Unreal Engine. "
        "Always respond with a compact JSON object shaped as {\"emotion\": <emotion>, \"text\": <reply>}. "
        "Supported emotions: Neutral, Happy, Sad, Angry, Disgust, Fear, Surprise."
    )
    quantization: Optional[str] = None


class LLMEngine:
    """Wrapper around a Hugging Face causal language model.

    The class is designed to work with models such as Qwen 2.5 4B Instruct
    AWQ and its quantised derivatives. Only open-source, locally hosted models are
    supported; no remote endpoints are contacted.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._model = None
        self._tokenizer = None
        self._streamer: Optional[TextIteratorStreamer] = None

    def load(self) -> None:
        """Loads the tokenizer and model into memory."""

        logger.info("Loading tokenizer from %s", self.config.model_name_or_path)
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name_or_path, use_fast=True
        )

        model_kwargs: Dict[str, object] = {}
        if self.config.quantization and self.config.quantization.lower() in {"awq", "int4"}:
            model_kwargs.update({"torch_dtype": torch.float16})

        logger.info("Loading causal LM from %s", self.config.model_name_or_path)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.config.model_name_or_path,
            device_map="auto",
            low_cpu_mem_usage=True,
            trust_remote_code=True,
            **model_kwargs,
        )
        self._model.eval()

        logger.info("Model loaded to device map: %s", self._model.hf_device_map)

    @property
    def is_ready(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    def _build_prompt(self, user_message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        segments: List[str] = [f"<|system|>\n{self.config.system_prompt}"]
        if chat_history:
            for turn in chat_history:
                segments.append(f"<|user|>\n{turn['user']}")
                segments.append(f"<|assistant|>\n{turn['assistant']}")
        segments.append(f"<|user|>\n{user_message}\n<|assistant|>")
        return "\n".join(segments)

    def generate(self, user_message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, str]:
        if not self.is_ready:
            raise RuntimeError("LLMEngine.generate called before load().")

        prompt = self._build_prompt(user_message, chat_history)
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)

        streamer = TextIteratorStreamer(self._tokenizer, skip_prompt=True, skip_special_tokens=True)
        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=self.config.max_new_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            repetition_penalty=self.config.repetition_penalty,
            do_sample=True,
        )

        logger.debug("Starting LLM generation")
        collected_text = ""

        def _run_generation() -> None:
            with torch.no_grad():
                self._model.generate(**generation_kwargs)

        generation_thread = Thread(target=_run_generation, daemon=True)
        generation_thread.start()

        for token_text in streamer:
            collected_text += token_text

        generation_thread.join()
        logger.debug("LLM generation completed: %s", collected_text)
        return self._parse_json_output(collected_text)

    def _parse_json_output(self, raw_text: str) -> Dict[str, str]:
        """Attempts to coerce the model output into the expected JSON schema."""
        raw_text = raw_text.strip()
        if "{" not in raw_text:
            logger.warning("Model output lacked JSON braces: %s", raw_text)
            return {"emotion": "Neutral", "text": raw_text}

        json_start = raw_text.find("{")
        json_end = raw_text.rfind("}") + 1
        candidate = raw_text[json_start:json_end]

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            logger.exception("Failed to parse JSON from model output: %s", candidate)
            payload = {"emotion": "Neutral", "text": raw_text}

        emotion = payload.get("emotion", "Neutral")
        text = payload.get("text", raw_text)
        return {"emotion": emotion, "text": text}


def load_config(path: Path) -> LLMConfig:
    """Loads a configuration JSON file into :class:`LLMConfig`."""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return LLMConfig(**data)
