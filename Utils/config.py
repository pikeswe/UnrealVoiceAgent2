"""Helper utilities to load project configuration objects from JSON."""
from __future__ import annotations

import json
from pathlib import Path

from LLM.engine import LLMConfig
from Server.streaming import StreamConfig
from TTS.kani_engine import KaniTTSConfig
from Utils.orchestrator import OrchestratorConfig


def load_orchestrator_config(config_path: Path) -> OrchestratorConfig:
    data = json.loads(config_path.read_text(encoding="utf-8"))

    llm_cfg = LLMConfig(**data["llm"])

    tts_section = data["tts"].copy()
    model_dir = Path(tts_section.pop("model_dir"))
    tts_cfg = KaniTTSConfig(model_dir=model_dir, **tts_section)
    stream_cfg = StreamConfig(**data.get("stream", {}))

    return OrchestratorConfig(llm=llm_cfg, tts=tts_cfg, stream=stream_cfg)
