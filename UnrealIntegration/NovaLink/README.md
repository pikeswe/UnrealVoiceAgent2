# NovaLink – Unreal Engine Integration

> Unreal Engine 5.6 plugin for bridging the local Nova voice stack into your project.

## Quick Start (Unreal Engine 5.6)

1. **Install the plugin**
   * Copy the `UnrealIntegration/NovaLink` folder into your Unreal project’s `Plugins/` directory.
   * Restart the editor and enable **NovaLink** under **Edit → Plugins → Project → NovaLink**.
2. **Verify project settings**
   * Set the project sample rate to 48 kHz (the audio stream is PCM16 @ 48 kHz).
   * Enable **Audio Mixer** in **Project Settings → Audio → Enable Audio Mixer**.
3. **Start the local services**
   * Launch the Nova control panel (`python app.py`).
   * Press **Start Servers** to expose the audio (`/ws/audio`) and emotion (`/ws/emotion`) WebSocket endpoints.
4. **Add Live Link sources**
   * Open **Window → Virtual Production → Live Link**.
   * Click **Add Source → NovaLink: Audio** and confirm the default URL `ws://localhost:5000/ws/audio`.
   * Add **NovaLink: Emotion** and keep the default URL `ws://localhost:5000/ws/emotion` unless you changed it in `config/default_config.json`.
5. **Place the Blueprint receiver**
   * Drag the `BP_NovaLinkReceiver` component (or your own actor) into the level.
   * Assign the Live Link subjects for audio and emotion in the Details panel.
6. **Press Play** – send a message from the Nova control panel to hear audio in Unreal and drive your MetaHuman facial animation.

## Blueprint Setup Notes

* The plugin exposes a **NovaLink Function Library** with helper nodes:
  * `Start Nova Audio Stream`
  * `Start Nova Emotion Stream`
  * `Stop Nova Streams`
  * `Convert Nova Emotion JSON`
* Bind **On Audio Chunk Received** to a **Quartz Subsystem**-backed audio component for low latency playback.
* Drive blend shapes by wiring **On Emotion Update** → `Convert Nova Emotion JSON` → your MetaHuman animation blueprint.
* Use a `Queue Audio` node to pre-buffer 2–3 packets if you notice playback underruns.
* Pair with the **Control Rig** to blend expressive poses based on the incoming emotion weights.

![Screenshot placeholder – Live Link setup](docs/images/novalink-livelink-placeholder.png)

![Screenshot placeholder – Blueprint wiring](docs/images/novalink-blueprint-placeholder.png)

> Replace the placeholders above with captures from your project once available.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Plugin missing after restart | Ensure the plugin folder sits in `YourProject/Plugins/NovaLink/` and rebuild project files. |
| Audio stream stutters | Reduce buffer size in **Project Settings → Audio → Buffer Queue** or check the local server logs. |
| Emotion weights are zero | Confirm the control panel started the emotion WebSocket and Live Link subject shows updates. |
| Live Link source refuses to connect | Verify the Nova server port (`5000` default) is open and not blocked by a firewall. |

## Docs & Support

* [Back to the main Nova README](../../README.md)
* Issues and feature requests: open a ticket in the main repository.
