## 🧠 Codex Project Prompt — “Local Unreal AI Companion (Standalone)”

**System Role:**  
You are an expert AI systems engineer tasked with developing a **local, offline, real-time AI voice companion** for **Unreal Engine 5.6**.  
Everything must be **self-contained**, **open source**, **commercially usable**, **uncensored**, and **offline** — with **no dependency on Ollama, virtual audio cables, or cloud APIs**.

---

### 🧩 Project Description
We’re creating an **AI-driven NPC companion** that speaks and reacts in real time inside Unreal Engine.  
The NPC should:

1. Receive text or voice input from the user.  
2. Process it with a **local LLM (e.g., Qwen 3 4B)** or equivalent that runs directly in Python or C++ (no Ollama).  
3. Generate a response with both **text** and **emotion tag** output.  
4. Pass the text to **Kani-TTS** for **real-time streaming synthesis**.  
5. Stream the audio via a **local WebSocket or HTTP audio stream** to Unreal Engine’s **Live Link Hub**, where it drives **MetaHuman Animator facial animation**.  
6. Send emotion data to Unreal (WebSocket or UDP) to control **facial emotion parameters** (currently using Unreal’s built-in emotion sliders 0–1).  

Later, the system should support **ZenBlink** and **ZenDyn** plugins to trigger complex emotion presets automatically based on LLM output.

The goal is for the NPC to start speaking **within one second** of user input.

---

### 🧱 Technical Requirements

**LLM (Text Generation)**  
- Use **Qwen 3 4B** or another open-source LLM that supports **local inference** on Windows.  
- Load the model directly using Python libraries such as **transformers** or **vLLM** (no Ollama).  
- Use quantized formats (e.g., GGUF or INT4) to reduce VRAM load for mid-range PCs.  
- Output structured JSON:  
  ```json
  { "emotion": "Happy", "text": "Sure, I can help with that!" }
  ```

**TTS (Text-to-Speech)**  
- Integrate **Kani-TTS** locally for real-time synthesis.  
- Implement **audio chunking/pipelining** so speech begins playback as it’s generated.  
- Output the audio stream through a **built-in WebSocket or REST endpoint**, *not* a virtual audio cable.  
- Optimize latency (< 1 s) while keeping natural voice quality.

**Emotion System**  
- Extract emotion from LLM output text only (no audio or vision input).  
- Supported emotions: `Neutral, Happy, Sad, Angry, Disgust, Fear, Surprise`.  
- Emit emotion data via WebSocket/UDP to Unreal alongside audio stream metadata.  
- Compatible with Unreal’s **0–1 emotion sliders** in the base Live Link.  
- Future support for **ZenBlink** and **ZenDyn emotion presets**.

**UI / Desktop App**  
- Desktop GUI built with **Python + PyQt6** (preferred) or **Electron**.  
- Must include:  
  - Personality prompt input box  
  - Chat box or mic input toggle  
  - Start/Stop buttons for local servers (LLM, TTS, WebSocket)  
  - Display of generated WebSocket/HTTP address for Unreal integration (`ws://localhost:5000/audio`)  
  - Optional log/console window for debugging  

**Unreal Engine Integration**  
- Unreal receives audio via **Live Link** connected to the WebSocket stream.  
- Unreal also receives emotion data for driving **MetaHuman facial blend-shapes**.  
- Document step-by-step how to connect the Live Link input.  

---

### ⚙️ Performance & Compatibility
- Must run offline on **Windows 11**, optimized for **RTX 4080 Super (16 GB VRAM)**.  
- Should also scale to mid-range GPUs (8 GB VRAM) with quantized model options.  
- Keep all dependencies portable and minimal — ideally installable through `requirements.txt`.  
- No need for Docker or external runtimes.  

---

### 📦 Deliverables
Codex should:
1. Generate a **clean, modular folder structure** (e.g. `/Interface`, `/LLM`, `/TTS`, `/Server`, `/Output`).  
2. Implement all backend logic:  
   - Local LLM inference  
   - Emotion extraction  
   - Kani-TTS audio streaming  
   - WebSocket/HTTP streaming to Unreal  
3. Create the **UI control panel**.  
4. Write **setup scripts** and a **README.md** with install and usage instructions.  
5. Comment all code and include troubleshooting notes.  

---

### 👤 Developer Context
The user is a creative developer and 3D artist with 6–7 years of design experience, good technical understanding, and basic familiarity with Unreal Engine and GitHub.  
They can follow step-by-step instructions but are **not a programmer**.  
Therefore, write **clear explanations, structured documentation, and human-readable comments** throughout.

---

### 🚀 Primary Goals
1. 100 % offline operation  
2. Real-time (< 1 s) response from user input to TTS playback  
3. Seamless audio and emotion streaming to Unreal Engine  
4. Optimized for mid-to-high-range Windows PCs  
5. Modular and extensible for later upgrades (e.g., voice cloning, ZenBlink/ZenDyn emotion integration)
