"""High level coordination between the LLM, TTS and streaming servers."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from LLM.engine import LLMConfig, LLMEngine
from Server.streaming import StreamConfig, StreamServer, StreamingServer
from TTS.kani_engine import KaniTTSConfig, KaniTTSEngine
from Utils.emotions import EmotionMapper

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    llm: LLMConfig
    tts: KaniTTSConfig
    stream: StreamConfig = field(default_factory=StreamConfig)


class VoiceAgentOrchestrator:
    """Glue object binding all sub systems together."""

    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.llm = LLMEngine(config.llm)
        self.tts = KaniTTSEngine(config.tts)
        self.stream_server = StreamServer(config.stream)
        self._emotion_mapper = EmotionMapper()
        self._streaming_server = StreamingServer(
            self.stream_server.app,
            config.stream.host,
            config.stream.port,
        )
        self._started = False

    async def start(self) -> None:
        if self._started:
            logger.debug("Orchestrator already started")
            return
        logger.info("Starting orchestrator")
        self.llm.load()
        await self.tts.load()
        self._streaming_server.start()
        self._started = True
        logger.info(
            "Stream server running on ws://%s:%s%s",
            self.config.stream.host,
            self.config.stream.port,
            self.config.stream.audio_endpoint,
        )

    async def stop(self) -> None:
        if not self._started:
            return
        await asyncio.to_thread(self._streaming_server.stop)
        self._started = False
        logger.info("Orchestrator stopped")

    async def process_text(self, user_message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, str]:
        """Runs the LLM + TTS pipeline and streams the result."""
        logger.debug("Processing user message: %s", user_message)
        result = self.llm.generate(user_message, chat_history)
        emotion_payload = self._emotion_mapper.to_payload(result["emotion"])
        await self.stream_server.push_emotion(emotion_payload)

        async for chunk in self.tts.synthesize_stream(result["text"]):
            await self.stream_server.push_audio(chunk)

        return result

    async def __aenter__(self) -> "VoiceAgentOrchestrator":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()
