## ⚠️ Disclaimer
 
This project is a **personal experiment** and is not affiliated with, endorsed by, or associated with Anthropic, Riot Games, Netflix, or any other company or rights holder.
 
The AI persona (Jinx from Arcane) is used purely for experimental, non-commercial creative exploration. All character rights belong to their respective owners.
 
This project uses **dolphin-llama3**, an uncensored LLM fine-tune. The outputs of this model are unpredictable and may be offensive, inappropriate, or harmful. The system prompt is intentionally configured for roleplaying. This setup is ntended for experimental use only — not a production application, not a product, and not something to be distributed or used in any context involving vulnerable individuals.
 
**Use entirely at your own risk.** 
 
---

# CompanionAI — Jinx Desktop Companion

A fully local, privacy-first AI desktop companion built with Electron, Python, and local models. No cloud, no API keys, no data leaves your machine.

---

## What It Does

A desktop companion (Jinx from Arcane) that sits on your screen, watches what you're doing via periodic screenshots, reacts to your screen content, responds to chat input, and speaks in a cloned voice — all running locally.

---

## Architecture

```
Electron (main.ts)
├── pythonUI/Jinx_ui.py       — Tkinter Widget window, animations, TTS
└── AI/agent.py               — AI brain, vision loop, dialogue loop
    ├── AI/vision_logic.py    — Screenshot + vision model
    └── AI/dialogue_logic.py  — Chat with LLM via Ollama
```

Electron spawns both Python processes and pipes messages between them via stdin/stdout.

---

## Local Models Used

### LLM — Ollama
- **Model:** `dolphin-llama3:latest`
- **Purpose:** Main dialogue and screen commentary
- **Runs on:** Ollama local server at `http://localhost:11434`
- **Install:** https://ollama.com → then `ollama pull dolphin-llama3`

### Vision — Ollama
- **Model:** Vision model via `vision_logic.py` (e.g. `llava` or similar)
- **Purpose:** Describes screenshots for Jinx to react to
- **Runs on:** Same Ollama instance
- **Install:** `ollama pull llava` (or whichever model is configured in `vision_logic.py`)

### TTS — Coqui XTTS v2
- **Model:** `tts_models/multilingual/multi-dataset/xtts_v2`
- **Purpose:** Text-to-speech with Jinx voice cloning
- **Runs on:** Local GPU (NVIDIA recommended)
- **Voice sample:** `AI/jinxVoice.wav` — clean Jinx dialogue clip used to generate `jinx_voice.pth`
- **License:** Coqui CPML (non-commercial use only) — https://coqui.ai/cpml

---

## Dependencies

### Node / Electron
```
electron
@electron-forge/plugin-vite
typescript
vite
```
Install with:
```bash
npm install
```

### Python
```
TTS                  # Coqui XTTS v2
torch==2.4.0         # MUST be this version — see note below
torchaudio==2.4.0
transformers==4.37.2 # MUST be this version — see note below
tokenizers==0.15.2
sounddevice
soundfile
numpy
Pillow
requests
ollama (or requests to localhost:11434)
pyscreenshot / mss   # whichever vision_logic.py uses
jieba
```

Install with:
```bash
pip install TTS torch==2.4.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu121
pip install transformers==4.37.2 tokenizers==0.15.2
pip install sounddevice soundfile numpy Pillow requests
```

---

## ⚠️ Critical Dependency Version Notes

### PyTorch must be 2.4.0
PyTorch 2.6 changed `torch.load` to `weights_only=True` by default, which breaks Coqui TTS model loading. **Do not upgrade PyTorch** past 2.4.x or TTS will fail with an `UnpicklingError`.

### Transformers must be 4.37.2
Newer versions of `transformers` removed `BeamSearchScorer`, which Coqui TTS depends on. **Do not upgrade transformers** or TTS will fail with an `ImportError`.

If either package gets accidentally upgraded, reinstall:
```bash
pip install torch==2.4.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu121
pip install transformers==4.37.2 tokenizers==0.15.2
```

### ⚠️ C++ Build Tools Required for TTS on Windows
Coqui TTS requires Microsoft C++ Build Tools to install on Windows. If you get errors like `error: Microsoft Visual C++ 14.0 or greater is required` during `pip install TTS`:

1. Download **Visual Studio Build Tools** from https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. In the installer, select **"Desktop development with C++"**
3. Install, then retry `pip install TTS`

---

## GPU Setup (Strongly Recommended)

XTTS v2 on CPU takes ~15 seconds per line. On an NVIDIA GPU it drops to ~2-3 seconds.

Verify CUDA is available:
```bash
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

If it prints `False`, you likely have the CPU-only PyTorch build. Reinstall with the `cu121` index URL above.

Requires an NVIDIA GPU with CUDA support. Tested on RTX 3070 (8GB VRAM).

---

## First-Time Setup

### 1. Generate the voice embedding
Run once to create `jinx_voice.pth` from your voice sample:
```bash
cd AI
python tts.py
```
This reads `AI/jinxVoice.wav` and saves the voice embedding. You only need to do this once — the `.pth` file is reused on every launch.

`jinx_voice.pth` is gitignored and must be regenerated on new machines.

### 2. Start Ollama
```bash
ollama serve
```
Make sure your models are pulled (`ollama pull dolphin-llama3`, etc.)

### 3. Run the app
```bash
npm start
```

---

## Project Structure

```
CompanionAI/
├── AI/
│   ├── agent.py              # Main AI loop (vision + dialogue)
│   ├── dialogue_logic.py     # Ollama chat wrapper
│   ├── vision_logic.py       # Screenshot + vision model
│   ├── tts.py                # One-time voice embedding generator
│   └── jinxVoice.wav         # Voice clone source (gitignored)
├── pythonUI/
│   ├── Jinx_ui.py            # Tkinter Widget + XTTS playback
│   ├── expressionsV2/        # Jinx expression PNGs
│   └── transitionalgifs/     # Jinx animation GIFs
├── src/
│   ├── main.ts               # Electron main process
│   ├── preload.ts            # IPC bridge
│   └── renderer.ts           # Frontend logic
├── index.html                # Chat overlay UI
└── jinx_voice.pth            # Generated voice embedding (gitignored)
```

---

## Gitignored Files

These are excluded from the repo and must be set up locally:
- `jinx_voice.pth` — regenerate with `python AI/tts.py`
- `AI/jinxVoice.wav` — provide your own clean voice sample
- `node_modules/`
- `__pycache__/`

---

## License Notes

- **Coqui XTTS v2** is licensed under CPML — free for non-commercial personal use only. Do not use in a commercial product without purchasing a license from Coqui.
- **dolphin-llama3** is an uncensored model fine-tune — use responsibly.
