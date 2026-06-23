# Speech

Speech is a local push-to-talk dictation app for Windows. Hold a hotkey, speak,
release, and the transcript is pasted into the active input, copied to the
clipboard, and saved in local history.

The default recognition model is NVIDIA Parakeet:

```text
nvidia/parakeet-tdt-0.6b-v3
```

## Install

Open PowerShell and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/TheRofli/speech/main/bootstrap.ps1 | iex"
```

Then download the speech model:

```powershell
speech parakeet install
```

Start Speech:

```powershell
speech
```

By default Speech installs to:

```text
D:\Speech
```

The installer does not download Parakeet automatically unless you pass
`-DownloadParakeet`, because the model cache is about 4.67 GB.

## What You Get

- tray app
- `Ctrl + Win` push-to-talk
- local Parakeet transcription
- active input paste
- clipboard copy
- local transcript history
- load / unload model from RAM
- CPU by default, CUDA optional
- polished Tauri UI for status, controls, history, setup, and future analysis

## Requirements

Minimum practical setup:

- Windows 11
- Python 3.11
- 8 GB RAM
- 12 GB free disk space on `D:`
- working microphone

Recommended:

- Windows 11
- 16 GB RAM or more
- 20 GB free disk space on `D:`
- modern 4-core CPU or better
- 80 GB RAM is very comfortable for large local-model workflows
- NVIDIA GPU is optional

Notes:

- CPU mode is the stable default.
- CUDA mode requires a CUDA-compatible PyTorch install.
- macOS and Ubuntu/Linux are planned, but not supported yet.
- No model files, venvs, caches, transcripts, or local data are meant to be
  committed to Git.

## Commands

```powershell
speech
speech status
speech stop
speech restart
speech open
speech diagnose
speech parakeet install
speech foreground
```

`speech` starts detached in the tray. `speech open` opens the Tauri UI. Use
`speech foreground` only when debugging.

## Controls

- Hold `Ctrl + Win` to record.
- Release to transcribe.
- The hotkey is suppressed while held so the active app can keep normal mouse
  wheel scrolling instead of receiving `Ctrl + wheel`.
- Right-click the tray icon for controls.
- Use `Open Speech` from the tray, or run `speech open`, to open the Tauri UI.

## Local Data

Speech keeps local data here:

```text
D:\Speech\data
D:\Speech\models
D:\Speech\cache
D:\Speech\tmp
```

The app does not send audio or transcripts to an online service. Hugging Face is
used only when you run `speech parakeet install`.

## Tauri UI

The stable runtime is still the Python tray app. The Tauri UI is now the primary
window for status, controls, history, setup, and future analysis experiments.
If a packaged Tauri executable exists, `speech open` launches it. Otherwise it
falls back to Tauri dev mode when Node dependencies are installed.

```powershell
cd D:\Speech\tauri
npm install
npm run tauri:dev
```

Build checks:

```powershell
cd D:\Speech\tauri
npm run build
cd src-tauri
cargo check
```

## Development

Python tests:

```powershell
D:\Speech\.venv\Scripts\python.exe -m unittest discover -s D:\Speech\tests
```

PowerShell install scripts:

```powershell
.\install.ps1
speech diagnose
```

Keep these out of commits:

- `.venv/`
- `models/`
- `data/`
- `cache/`
- `tmp/`
- `tauri/node_modules/`
- `tauri/dist/`
- `tauri/src-tauri/target/`

## Parakeet Modes

Parakeet v3 is one 0.6B checkpoint, not a Whisper-style
Tiny/Base/Medium/Large family.

Supported model capabilities include:

- dictation
- automatic language detection
- punctuation and capitalization
- timestamp support
- long-form / streaming later through NeMo support

## Roadmap

- live Tauri settings bridge for device/backend/output toggles
- optional transcript/personality analysis tab through DeepSeek, OpenAI, or a
  local model
- Tauri tray replacement
- signed Windows release
- CUDA install helper
- optional NeMo backend
- macOS support
- Ubuntu/Linux support
