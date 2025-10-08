# External Dependencies

This directory is reserved for third-party source trees that are cloned at
runtime.  When the Hugging Face snapshot for Kani-TTS is unavailable, the
project will clone https://github.com/nineninesix-ai/kani-tts into
`external/kani-tts` and stream the checkpoint weights directly from that
checkout.

To manage the repository manually you can run:

```bash
git clone https://github.com/nineninesix-ai/kani-tts.git external/kani-tts
```

or add it as a git submodule if your workflow prefers tracked externals:

```bash
git submodule add https://github.com/nineninesix-ai/kani-tts.git external/kani-tts
```

The runtime automatically detects `external/kani-tts/models/kani_tts` when the
primary `models/kani_tts` directory is missing or incomplete.
