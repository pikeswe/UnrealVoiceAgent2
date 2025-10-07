"""PyQt6 control panel for the Unreal Voice Agent."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from Utils.config import load_orchestrator_config
from Utils.orchestrator import OrchestratorConfig, VoiceAgentOrchestrator

logger = logging.getLogger(__name__)


class BackendWorker(QtCore.QThread):
    """Runs the orchestrator inside a dedicated thread."""

    ready = QtCore.pyqtSignal()
    response_ready = QtCore.pyqtSignal(str, str)
    error_occurred = QtCore.pyqtSignal(str)
    log_event = QtCore.pyqtSignal(str)

    def __init__(self, config: OrchestratorConfig) -> None:
        super().__init__()
        self.config = config
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.orchestrator: Optional[VoiceAgentOrchestrator] = None
        self._shutting_down = False

    def run(self) -> None:  # type: ignore[override]
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.orchestrator = VoiceAgentOrchestrator(self.config)
            self.loop.run_until_complete(self.orchestrator.start())
            self.ready.emit()
            self.log_event.emit("Backend started. Listening for requests.")
            self.loop.run_forever()
        except Exception as exc:  # pragma: no cover - GUI path
            logger.exception("Backend crashed: %s", exc)
            self.error_occurred.emit(str(exc))
        finally:
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)

    def submit_text(self, text: str) -> None:
        if not self.loop or not self.orchestrator:
            self.error_occurred.emit("Backend not ready")
            return

        async def _task() -> None:
            try:
                result = await self.orchestrator.process_text(text)
                self.response_ready.emit(result["emotion"], result["text"])
            except Exception as exc:  # pragma: no cover
                logger.exception("Failed to process text: %s", exc)
                self.error_occurred.emit(str(exc))

        asyncio.run_coroutine_threadsafe(_task(), self.loop)

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        if not self.loop or not self.orchestrator:
            return

        self._shutting_down = True

        async def _shutdown() -> None:
            if self.orchestrator:
                await self.orchestrator.stop()
                self.orchestrator = None
            if self.loop:
                self.loop.stop()

        future = asyncio.run_coroutine_threadsafe(_shutdown(), self.loop)
        try:
            future.result(timeout=10)
        except Exception as exc:  # pragma: no cover - GUI path
            logger.exception("Backend shutdown failed: %s", exc)
        finally:
            self._shutting_down = False


class ControlPanel(QtWidgets.QMainWindow):
    """Main window for controlling the local AI companion."""

    def __init__(self, config_path: Path, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nova Companion Control Panel")
        self.resize(720, 480)

        self.config = load_orchestrator_config(config_path)
        self.backend: Optional[BackendWorker] = None
        self._closing = False
        self._create_backend()

        self._setup_ui()

    def _setup_ui(self) -> None:
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        self.prompt_box = QtWidgets.QPlainTextEdit()
        self.prompt_box.setPlaceholderText("Enter or tweak Nova's personality prompt here…")
        self.prompt_box.setFixedHeight(120)
        layout.addWidget(QtWidgets.QLabel("Personality Prompt"))
        layout.addWidget(self.prompt_box)

        self.input_box = QtWidgets.QLineEdit()
        self.input_box.setPlaceholderText("Type something for Nova…")
        self.input_box.returnPressed.connect(self.on_send_clicked)

        input_layout = QtWidgets.QHBoxLayout()
        input_layout.addWidget(self.input_box)
        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self.on_send_clicked)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(QtWidgets.QLabel("System Log"))
        layout.addWidget(self.log_view)

        control_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("Start Servers")
        self.start_button.clicked.connect(self.on_start_clicked)
        control_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton("Stop Servers")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)

        self.status_label = QtWidgets.QLabel("Status: Offline")
        control_layout.addWidget(self.status_label)
        control_layout.addStretch()

        layout.addLayout(control_layout)

        info_box = QtWidgets.QGroupBox("Connection Info")
        info_layout = QtWidgets.QFormLayout(info_box)
        stream_cfg = self.config.stream
        base_url = f"ws://{stream_cfg.host}:{stream_cfg.port}"
        self.audio_endpoint_label = QtWidgets.QLabel(f"{base_url}{stream_cfg.audio_endpoint}")
        self.emotion_endpoint_label = QtWidgets.QLabel(f"{base_url}{stream_cfg.emotion_endpoint}")
        info_layout.addRow("Audio Stream:", self.audio_endpoint_label)
        info_layout.addRow("Emotion Stream:", self.emotion_endpoint_label)
        layout.addWidget(info_box)

        self.setCentralWidget(central)

    def _create_backend(self) -> None:
        if self.backend and self.backend.isRunning():
            return
        self.backend = BackendWorker(self.config)
        self.backend.ready.connect(self.on_backend_ready)
        self.backend.response_ready.connect(self.on_response_ready)
        self.backend.error_occurred.connect(self.on_error)
        self.backend.log_event.connect(self.append_log)

    # Slots -----------------------------------------------------------------
    def on_start_clicked(self) -> None:
        self.append_log("Spinning up backend…")
        prompt_override = self.prompt_box.toPlainText().strip()
        if prompt_override:
            self.backend.config.llm.system_prompt = prompt_override
        if self.backend is None:
            self._create_backend()
        elif self.backend.isRunning():
            self.append_log("Backend already running.")
            return
        elif self.backend.isFinished():
            self._create_backend()

        assert self.backend is not None
        self.backend.start()
        self.start_button.setEnabled(False)

    def on_stop_clicked(self) -> None:
        self.append_log("Stopping backend…")
        if self.backend:
            self.backend.shutdown()
            self.backend.wait(2000)
            self.backend = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Status: Offline")

    def on_send_clicked(self) -> None:
        text = self.input_box.text().strip()
        if not text:
            return
        self.append_log(f"You: {text}")
        if self.backend:
            self.backend.submit_text(text)
        self.input_box.clear()

    def on_backend_ready(self) -> None:
        self.append_log("Backend ready. Connect Unreal Live Link to the audio endpoint.")
        self.status_label.setText("Status: Online")
        self.stop_button.setEnabled(True)

    def on_response_ready(self, emotion: str, text: str) -> None:
        self.append_log(f"Nova ({emotion}): {text}")

    def on_error(self, message: str) -> None:
        self.append_log(f"Error: {message}")
        QtWidgets.QMessageBox.critical(self, "Backend Error", message)

    def append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        if self._closing:
            super().closeEvent(event)
            return

        self._closing = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.send_button.setEnabled(False)
        self.input_box.setEnabled(False)

        try:
            if self.backend:
                self.backend.shutdown()
                # Wait until the backend thread exits so the streaming server stops cleanly.
                self.backend.wait(5000)
                self.backend = None
        finally:
            super().closeEvent(event)


def launch_gui(config_path: Path) -> None:
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = ControlPanel(config_path)
    window.show()
    sys.exit(app.exec())
