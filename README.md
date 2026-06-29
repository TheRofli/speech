# Speech

Speech is a local push-to-talk dictation app. Hold a hotkey, speak, release,
and the transcript is pasted into the active input, copied to the clipboard,
and saved in searchable local history.

Speech recognition runs locally on your machine. Optional transcript cleanup
can stay local with SAGE or use an OpenAI-compatible API that you configure.

## Quick Install

### Windows 11

Open PowerShell and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/TheRofli/speech/main/bootstrap.ps1 | iex"
```

Then download the local speech model:

```powershell
speech parakeet install
```

Start Speech:

```powershell
speech
```

The Windows bootstrap downloads the source from GitHub, creates a local virtual
environment, installs dependencies, and adds the `speech` command to your user
PATH. If Python 3.11 is missing, it tries to install it with `winget`.

Default install location:

```text
%LOCALAPPDATA%\Programs\Speech
```

To choose another folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& ([scriptblock]::Create((irm https://raw.githubusercontent.com/TheRofli/speech/main/bootstrap.ps1))) -InstallDir 'E:\Apps\Speech'"
```

### macOS

Open Terminal and run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/TheRofli/speech/main/bootstrap.sh)"
```

Then download the local speech model:

```bash
speech parakeet install
```

Start Speech:

```bash
speech
```

The macOS bootstrap downloads the source from GitHub, creates a local virtual
environment, installs dependencies, and links `speech` into `~/.local/bin`.
If Python 3.11 is missing, it uses `uv` to install a local Python runtime.

Default install location:

```text
~/.speech
```

To choose another folder:

```bash
SPEECH_INSTALL_DIR="$HOME/Applications/Speech" /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/TheRofli/speech/main/bootstrap.sh)"
```

macOS support is source-install support. The Python tray/runtime is the stable
path; packaged signed `.app` builds are still planned.

## Model

Speech uses NVIDIA Parakeet by default:

```text
nvidia/parakeet-tdt-0.6b-v3
```

Parakeet TDT 0.6B v3 is a 600M-parameter multilingual automatic speech
recognition model from NVIDIA. The model card lists 25 supported languages,
including English, Russian, Ukrainian, German, French, Spanish, Portuguese,
Italian, Polish, Dutch, Turkish, Arabic, Chinese, Japanese, and Korean.

Useful capabilities:

- automatic language detection
- punctuation and capitalization
- timestamps
- long audio support
- CPU mode by default, CUDA optional on Windows/Linux systems with a compatible
  NVIDIA setup

Sources:

- [NVIDIA Parakeet TDT 0.6B v3 model card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- [NVIDIA NeMo ASR collection](https://docs.nvidia.com/nemo-framework/user-guide/latest/nemotoolkit/asr/intro.html)

## Optional AI Cleanup

Speech has three cleanup modes:

- `Off`: publish the Parakeet transcript unchanged.
- `Local`: correct Russian spelling, punctuation, and casing on CPU with
  `ai-forever/sage-fredt5-distilled-95m`.
- `API`: send transcript text to a configurable OpenAI-compatible endpoint.

You can switch the cleanup provider directly from the tray through
`Transcript polish > Off / Local / API`. The `Polish style` tray submenu and
the Controls tab provide two editing profiles:

- `Clean`: fix spelling, punctuation, capitalization, obvious recognition
  substitutions, and glossary terms while preserving wording and intent.
- `Refine`: additionally remove accidental repetition and make small wording
  improvements without expanding or answering the transcript.

The local SAGE model supports `Clean`. `Refine` is available in `API` mode.
Changing these options does not restart Parakeet.

The Controls tab also accepts a newline-separated terminology glossary. Use a
canonical term by itself, or map a common recognition error with `->`:

```text
DeepSeek
Deep-Seag -> DeepSeek
Qore-Code
```

API cleanup treats the transcript as untrusted text to edit, requests a small
JSON response, and rejects responses that look like an assistant answer,
Markdown article, or unrelated expansion. If validation fails, Speech safely
publishes the original Parakeet transcript.

Install the optional local corrector:

```powershell
speech ai install
```

SAGE is a 95.6M-parameter Russian correction model released under MIT. Its
checkpoint is about 383 MB. Speech keeps both the original and corrected text
in local history and rejects suspicious corrections that lose numbers, URLs,
email addresses, acronyms, or too much content.

API keys are stored through Windows Credential Manager or macOS Keychain, not
in `settings.json`:

```text
speech ai key set
speech ai key status
speech ai key delete
```

Sources:

- [SAGE distilled 95M model card](https://huggingface.co/ai-forever/sage-fredt5-distilled-95m)
- [SAGE project](https://github.com/ai-forever/sage)

## Requirements

Minimum practical setup:

- Windows 11 or macOS 13+
- Python 3.11, installed automatically by the bootstrap when possible
- working microphone
- 8 GB RAM
- 10 GB free disk space for the app, virtual environment, caches, and model

Recommended:

- 16 GB RAM or more
- modern 4-core CPU or better
- 15-20 GB free disk space
- NVIDIA GPU only if you specifically want CUDA

Notes:

- CPU mode is the stable default.
- CUDA requires a compatible NVIDIA driver and PyTorch CUDA install.
- The model is downloaded only when you run `speech parakeet install` or pass
  the bootstrap download flag.
- Model files, virtual environments, caches, transcripts, and local settings are
  intentionally excluded from Git.

## Controls

Default hotkeys:

- Windows: hold `Ctrl + Win`
- macOS: hold `Control + Command`

Workflow:

1. Hold the hotkey.
2. Speak.
3. Release.
4. Speech transcribes locally, then sends text to the active input, clipboard,
   and local history.

When cleanup is enabled, the overlay changes from transcription dots to pink
cleanup dots before insertion. Any cleanup failure publishes the original text.

The tray menu lets you open the window, copy the last transcript, load/unload
Parakeet, switch CPU/CUDA mode, select the transcript cleanup provider and
style, and quit.

## Commands

Windows PowerShell:

```powershell
speech
speech status
speech stop
speech restart
speech open
speech diagnose
speech parakeet install
speech ai install
speech ai key set
speech foreground
```

macOS Terminal:

```bash
speech
speech status
speech stop
speech restart
speech diagnose
speech parakeet install
speech ai install
speech ai key set
speech foreground
```

`speech` starts the background tray/runtime. `speech foreground` is mainly for
debugging because it keeps logs attached to the terminal.

## Local Data

Speech stores local runtime data inside the install folder:

```text
data/       transcripts, settings, runtime state
models/     Hugging Face and Torch model caches
cache/      package and runtime cache
tmp/        temporary audio files
.venv/      local Python virtual environment
```

Audio is never uploaded by Speech. In `Off` and `Local` modes, transcripts stay
on the device. In `API` mode, transcript text and configured glossary terms are
sent to the endpoint configured in the Controls tab. Hugging Face is contacted
only when downloading models.

## Development

Clone and install locally:

```powershell
git clone https://github.com/TheRofli/speech.git
cd speech
.\install.ps1
```

macOS/Linux shell:

```bash
git clone https://github.com/TheRofli/speech.git
cd speech
./install.sh
```

Python tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s .\tests
```

Frontend checks:

```powershell
cd tauri
npm install
npm run build
cd src-tauri
cargo check
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
- `tauri/src-tauri/gen/`

## Roadmap

- signed Windows installer release
- signed macOS `.app` release
- live Tauri settings bridge for device/backend/output toggles
- optional CUDA install helper
- optional NeMo backend
- optional transcript analysis tab through DeepSeek, OpenAI, or a local model
