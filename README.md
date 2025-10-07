# Nova – Local Unreal AI Companion

Nova is a fully offline voice companion designed to drive a MetaHuman inside Unreal Engine 5.6. It combines a local LLM (tested with Qwen3-4B-Instruct-2507), Kani-TTS for streaming speech synthesis, and a low-latency WebSocket bridge that feeds audio plus emotion weights directly into Live Link.
codex/develop-local-ai-voice-companion-for-unreal-r86qn0

The repository is structured so creative developers can launch the control panel, connect Unreal, and start iterating without touching Python code. Every dependency is open source and commercially usable.

**Next: [Unreal Integration](UnrealIntegration/NovaLink/README.md)**

## Project Layout

```
├── Interface/             # PyQt6 control panel
├── LLM/                   # Local language model wrapper
├── TTS/                   # Kani-TTS streaming wrapper
├── Server/                # FastAPI WebSocket broadcast server
├── Utils/                 # Orchestration helpers + emotion mapping
├── config/                # JSON configuration profiles
├── scripts/               # Optional setup scripts (model downloads, etc.)
├── app.py                 # GUI entry point
└── requirements.txt       # Python dependencies
```

## 1. System Requirements

* **OS**: Windows 11 (developed cross-platform, but optimised for Windows)
* **GPU**: RTX 4080 Super (16 GB) recommended. Quantised models (INT4/AWQ) allow use on 8 GB cards.
* **Storage**: ~12 GB for the LLM + 2 GB for Kani-TTS models.
* **Python**: 3.10 or 3.11 (64-bit). Install from [python.org](https://www.python.org/downloads/).

## 2. Quick Architecture Tour

If you want a high-level explanation before diving in, start here:

1. **You type or speak** using the control panel.
2. **`VoiceAgentOrchestrator`** (in `Utils/orchestrator.py`) forwards the text to the local LLM.
3. **`LLMEngine`** (in `LLM/engine.py`) generates the reply and an emotion label in JSON form.
4. **`EmotionMapper`** (in `Utils/emotions.py`) converts that label into slider weights for Unreal.
5. **`KaniTTSEngine`** (in `TTS/kani_engine.py`) immediately begins streaming audio chunks as the sentence is decoded.
6. **`StreamingServer`** (in `Server/streaming.py`) relays audio + emotion data to WebSocket clients (Unreal Live Link).
7. The control panel (`Interface/control_panel.py`) keeps everything in sync, shows logs, and lets you start/stop the stack.

Every piece is modular. Swap to a different LLM or TTS by updating the corresponding wrapper and the config file—no UI changes required.

## 3. Installation

1. **Clone the repo**
   ```powershell
   git clone https://github.com/your-org/NovaVoiceAgent.git
   cd NovaVoiceAgent
   ```

2. **Create a virtual environment** (optional but recommended)
   ```powershell
   py -3.11 -m venv .venv
   .venv\Scripts\activate
   ```


3. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```
   > Optional: install NVIDIA's NeMo stack with `pip install nemo_toolkit[tts]` to enable the high-fidelity audio decoder bundled with Kani-TTS.

4. **Download the models**
   * **LLM (Qwen3-4B-Instruct-2507)**
     ```powershell
     python scripts/download_models.py --output models
     ```
     Update `config/default_config.json` → `llm.model_name_or_path` to the local folder (default `models/llm/Qwen3-4B-Instruct-2507`).

   * **Kani-TTS** – the synthesiser code is vendored inside this repository; you only need the checkpoint weights. Use the helper script to grab them from Hugging Face:
     ```powershell
     python scripts/download_models.py --tts nineninesix/kani-tts-370m-MLX
     ```
     The files land in `models/kani_tts`. Update `config/default_config.json` → `tts.model_dir` if you choose a different path.
     Install `nemo_toolkit[tts]` if you haven't already to run the high-fidelity decoder.


## Unreal Engine Setup

The Unreal plugin is optional; the Python control panel works without it. When you want Unreal to mirror Nova’s speech and
emotions, follow these steps:

1. Copy the entire `UnrealIntegration/NovaLink/` folder from this repository into your Unreal project’s `Plugins/` directory
   (create the folder if it does not exist).
2. Launch Unreal Engine 5.6, open **Edit → Plugins**, and enable **NovaLink**. Restart the editor if prompted.
3. Open the **Live Link** panel and add the **NovaLink: Audio** source.
4. Add a second Live Link source named **NovaLink: Emotion** and point it to `ws://localhost:5000/ws/emotion`.
5. In your Blueprint graph, bind the **OnAudioChunkReceived** and **OnEmotionUpdate** events to your MetaHuman or other animation
   controllers. The plugin’s Blueprint function library includes helpers for quickly spawning the receivers.
6. If you notice playback lag, reduce the audio buffer in **Project Settings → Audio → Buffer Queue** to tighten latency.


5. **Configure the app**
   * Edit `config/default_config.json` to match your hardware and preferred voices.
   * Optional: save additional profiles in `config/` and load them via `python app.py --config config/my_setup.json`.

### Using Anaconda instead of `venv`

If you prefer Anaconda/Miniconda, you can follow the same steps inside a Conda environment:

```powershell
conda create -n nova python=3.11
conda activate nova
pip install -r requirements.txt
```

Conda installs Python and core scientific libraries, while `pip` pulls the exact packages listed in `requirements.txt`. The rest of the instructions (model downloads, configuration, running the control panel) stay identical.

## 3. Running the Control Panel

```powershell
python app.py
```

1. Click **Start Servers** to load the LLM + TTS and expose the WebSocket endpoints.
2. Type into the chat bar or edit the personality prompt before starting.
3. As soon as you send a message, Nova replies while streaming audio to Unreal.

The status panel displays:
* `Audio Stream`: `ws://<host>:<port>/ws/audio` – connect this in Live Link.
* `Emotion Stream`: `ws://<host>:<port>/ws/emotion` – optional metadata channel.

## 4. Unreal Engine Integration

1. After enabling the NovaLink plugin, open **Window → Virtual Production → Live Link**.
2. Click **Add Source → NovaLink: Audio** and confirm the default URL `ws://localhost:5000/ws/audio` matches your control panel.
3. Add **NovaLink: Emotion** and leave the default URL (`ws://localhost:5000/ws/emotion`) unless you changed the server host.
4. Create a Blueprint (Actor or Component) and use the **NovaLink Function Library** nodes to spawn Audio/Emotion receivers. Bind
   **OnAudioChunkReceived** to an audio component or MetaHuman Animator, and **OnEmotionUpdate** to the blend shape logic of your
   character.
5. Start the UnrealVoiceAgent servers, press play, and send a message. You should hear audio immediately while the Live Link
   subject animates from the emotion JSON stream.

> **Tip:** Unreal 5.6 can buffer a few frames of audio. Reduce the buffer size in the audio device settings or tweak the
> Blueprint audio queue if latency exceeds ~1 second.

## 5. How It Works

1. **LLM Engine (`LLM/engine.py`)** – loads Qwen3-4B-Instruct-2507 locally via `transformers`, instructs it to always answer with `{ "emotion": ..., "text": ... }`, and parses the output.
2. **Emotion Mapper (`Utils/emotions.py`)** – converts the textual emotion into slider weights for MetaHuman.
3. **Kani-TTS (`TTS/kani_engine.py`)** – streams PCM16 chunks as soon as they are generated.
4. **Stream Server (`Server/streaming.py`)** – FastAPI WebSocket broadcaster that Unreal connects to.
5. **Orchestrator (`Utils/orchestrator.py`)** – glues everything together, feeding audio + emotion into the broadcast queues.
6. **Control Panel (`Interface/control_panel.py`)** – PyQt6 UI for creatives. Run/stop servers, adjust prompts, chat, and monitor logs.

All components are modular. Swap the LLM or TTS by editing the respective wrapper and config.

## 6. Latency Optimisation

* Enable **CUDA** by installing `torch` with GPU support (`pip install torch --index-url https://download.pytorch.org/whl/cu121`).
* Use quantised checkpoints (`AWQ`, `INT4`) for faster decoding on 8 GB GPUs.
* Lower `max_new_tokens` in `config/default_config.json` for shorter responses.
* Adjust `tts.chunk_size` to 512 or 768 for earlier playback start (with minor CPU overhead).
* Run the control panel and Unreal on the same machine to avoid network hops.

## 7. Troubleshooting

| Symptom | Fix |
| --- | --- |
| GUI hangs on start | Ensure GPU drivers are up-to-date and the model path in the config exists. Check the log panel for Python exceptions. |
| No audio in Unreal | Confirm Live Link is bound to the correct WebSocket URL and the firewall allows local connections. |
| Distorted speech | Increase `tts.chunk_size` or confirm the sample rate matches Unreal’s audio project settings. |
| Emotions not moving | Open the emotion WebSocket in a browser (`wscat`) to verify JSON payloads. Map the keys to your blend shapes. |

## 8. Extending the System

* **Voice cloning** – train a new Kani-TTS speaker and change `tts.voice`.
* **ZenBlink / ZenDyn** – extend `EmotionMapper` to emit preset IDs alongside slider values.
* **Speech input** – add a Whisper model and pipe transcripts into `VoiceAgentOrchestrator.process_text()`.
* **Scripting** – reuse the orchestrator module inside other Python tools or batch scripts.

## 9. License
codex/develop-local-ai-voice-companion-for-unreal-r86qn0

All dependencies used are open-source and compatible with commercial projects. Please review their individual licences (Qwen, Kani-TTS, FastAPI, etc.) to ensure compliance with your distribution model.

The directory `TTS/kani_tts` vendors the upstream [Kani-TTS](https://github.com/nineninesix-ai/kani-tts) implementation under the terms of the Apache 2.0 licence included in that folder.


---

Happy building, and enjoy bringing Nova to life inside Unreal!
