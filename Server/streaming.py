"""Realtime WebSocket streaming servers for audio and metadata."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    host: str = "0.0.0.0"
    port: int = 5000
    audio_endpoint: str = "/ws/audio"
    emotion_endpoint: str = "/ws/emotion"


class BroadcastQueue:
    """A small helper to fan out audio or metadata frames to multiple listeners."""

    def __init__(self) -> None:
        self._listeners: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def register(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=4)
        async with self._lock:
            self._listeners.add(queue)
        return queue

    async def unregister(self, queue: asyncio.Queue) -> None:
        async with self._lock:
            self._listeners.discard(queue)

    async def broadcast(self, payload: bytes) -> None:
        async with self._lock:
            listeners = list(self._listeners)
        for queue in listeners:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.debug("Dropping stale payload for listener %s", id(queue))


class StreamServer:
    """FastAPI application bundling the audio and emotion streaming endpoints."""

    def __init__(
        self,
        config: StreamConfig,
        *,
        on_audio_client_count_changed: Optional[Callable[[int], None]] = None,
        on_emotion_client_count_changed: Optional[Callable[[int], None]] = None,
    ):
        self.config = config
        self.app = FastAPI(title="Unreal Voice Agent Stream Server")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.audio_broadcast = BroadcastQueue()
        self.emotion_broadcast = BroadcastQueue()

        self._audio_client_count = 0
        self._emotion_client_count = 0
        self._on_audio_client_count_changed = on_audio_client_count_changed
        self._on_emotion_client_count_changed = on_emotion_client_count_changed

        self.app.websocket(self.config.audio_endpoint)(self._audio_handler)
        self.app.websocket(self.config.emotion_endpoint)(self._emotion_handler)

    async def _audio_handler(self, websocket: WebSocket) -> None:
        await websocket.accept()
        listener_queue = await self.audio_broadcast.register()
        logger.info("Audio client connected: %s", websocket.client)
        self._audio_client_count += 1
        self._emit_audio_client_count()
        try:
            while True:
                chunk = await listener_queue.get()
                await websocket.send_bytes(chunk)
        except WebSocketDisconnect:
            logger.info("Audio client disconnected: %s", websocket.client)
        finally:
            await self.audio_broadcast.unregister(listener_queue)
            self._audio_client_count = max(0, self._audio_client_count - 1)
            self._emit_audio_client_count()

    async def _emotion_handler(self, websocket: WebSocket) -> None:
        await websocket.accept()
        listener_queue = await self.emotion_broadcast.register()
        logger.info("Emotion client connected: %s", websocket.client)
        self._emotion_client_count += 1
        self._emit_emotion_client_count()
        try:
            while True:
                payload = await listener_queue.get()
                await websocket.send_text(payload.decode("utf-8"))
        except WebSocketDisconnect:
            logger.info("Emotion client disconnected: %s", websocket.client)
        finally:
            await self.emotion_broadcast.unregister(listener_queue)
            self._emotion_client_count = max(0, self._emotion_client_count - 1)
            self._emit_emotion_client_count()

    async def push_audio(self, chunk: bytes) -> None:
        await self.audio_broadcast.broadcast(chunk)

    async def push_emotion(self, payload: Dict[str, float]) -> None:
        message = json.dumps(payload)
        await self.emotion_broadcast.broadcast(message.encode("utf-8"))

    def _emit_audio_client_count(self) -> None:
        if self._on_audio_client_count_changed:
            try:
                self._on_audio_client_count_changed(self._audio_client_count)
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Audio client count callback failed")

    def _emit_emotion_client_count(self) -> None:
        if self._on_emotion_client_count_changed:
            try:
                self._on_emotion_client_count_changed(self._emotion_client_count)
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Emotion client count callback failed")


async def serve(app: FastAPI, host: str, port: int) -> None:
    """Launches the uvicorn server inside the current asyncio loop."""
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
