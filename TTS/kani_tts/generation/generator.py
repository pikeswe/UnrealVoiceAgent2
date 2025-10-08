"""Text-to-speech generation logic"""

import logging
import time
import warnings
from threading import Thread
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation.streamers import BaseStreamer

from ..config import (
    MODEL_NAME,
    START_OF_HUMAN,
    END_OF_TEXT,
    END_OF_HUMAN,
    END_OF_AI,
    TEMPERATURE,
    TOP_P,
    REPETITION_PENALTY,
    MAX_TOKENS,
)
from ..model_utils import resolve_model_reference


logger = logging.getLogger(__name__)


class TokenIDStreamer(BaseStreamer):
    """Custom streamer that yields token IDs"""
    def __init__(self, callback):
        self.callback = callback

    def put(self, value):
        """Called by model.generate() with token IDs"""
        if len(value.shape) > 1:
            token_ids = value[0].tolist()
        else:
            token_ids = value.tolist()

        for token_id in token_ids:
            self.callback(token_id)

    def end(self):
        """Called when generation is complete"""
        pass


class TTSGenerator:
    def __init__(
        self,
        *,
        model_name: Optional[str] = None,
        torch_dtype: torch.dtype = torch.bfloat16,
        device_map: str = "auto",
    ) -> None:
        self.model_path = model_name or MODEL_NAME
        self.model_path = resolve_model_reference(self.model_path, log=logger)

        warnings.warn(
            "TODO: remove ignore_mismatched_sizes=True once the checkpoint is pinned",
            UserWarning,
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch_dtype,
            device_map=device_map,
            trust_remote_code=True,
            ignore_mismatched_sizes=True,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            trust_remote_code=True,
        )

        if torch.cuda.is_available():
            self.device = 'cuda'
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = 'mps'
        else:
            self.device = 'cpu'

    def prepare_input(self, prompt):
        """Build custom input_ids with special tokens"""
        input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids
        start_token = torch.tensor([[START_OF_HUMAN]], dtype=torch.int64)
        end_tokens = torch.tensor([[END_OF_TEXT, END_OF_HUMAN]], dtype=torch.int64)
        modified_input_ids = torch.cat([start_token, input_ids, end_tokens], dim=1)
        modified_input_ids = modified_input_ids.to(self.device)

        attention_mask = torch.ones(1, modified_input_ids.shape[1], dtype=torch.int64)
        attention_mask = attention_mask.to(self.device)

        return modified_input_ids, attention_mask

    def generate(
        self,
        prompt,
        audio_writer,
        *,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Generate speech tokens from text prompt"""
        modified_input_ids, attention_mask = self.prepare_input(prompt)

        point_1 = time.time()

        # Stream tokens from LLM
        all_token_ids = []

        def on_token_generated(token_id):
            """Callback for each generated token"""
            all_token_ids.append(token_id)
            # print(f"[LLM] Token {len(all_token_ids)}: {token_id}")
            audio_writer.add_token(token_id)

        streamer = TokenIDStreamer(callback=on_token_generated)

        generation_kwargs = dict(
            input_ids=modified_input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_tokens or MAX_TOKENS,
            do_sample=True,
            temperature=temperature if temperature is not None else TEMPERATURE,
            top_p=top_p if top_p is not None else TOP_P,
            repetition_penalty=REPETITION_PENALTY,
            num_return_sequences=1,
            eos_token_id=END_OF_AI,
            streamer=streamer,
        )

        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        thread.join()

        point_2 = time.time()

        print(f"\n[MAIN] Generation complete. Total tokens: {len(all_token_ids)}")

        # Decode generated text from token IDs
        generated_text = self.tokenizer.decode(all_token_ids, skip_special_tokens=True)

        return {
            'generated_text': generated_text,
            'all_token_ids': all_token_ids,
            'generation_time': point_2 - point_1,
            'point_1': point_1,
            'point_2': point_2
        }
