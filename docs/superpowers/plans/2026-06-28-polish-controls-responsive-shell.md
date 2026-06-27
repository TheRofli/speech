# Polish Controls And Responsive Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add convenient tray polish controls, safe Clean/Refine API editing, a terminology glossary, and a fixed-height responsive Tauri shell without changing the local model.

**Architecture:** Provider selection and polish profile remain separate settings. `SpeechApp` owns hot-switch lifecycle, `TrayController` only exposes commands, and the post-processing layer owns glossary application and profile-specific validation. The Tauri frontend keeps the viewport fixed and scrolls only the active content region.

**Tech Stack:** Python 3.11, unittest, pystray, urllib/OpenAI-compatible chat completions, React 19, TypeScript, CSS, Tauri 2/Rust, Playwright screenshots.

---

### Task 1: Tray provider and profile controls

**Files:**
- Create: `tests/test_tray.py`
- Modify: `speech_app/tray.py`
- Modify: `speech_app/app.py`
- Modify: `speech_app/settings.py`

- [ ] **Step 1: Write failing application-state tests**

Add tests proving `set_ai_mode("off")` persists settings and unloads only the corrector, `set_ai_mode("local")` schedules background loading, and `set_ai_profile("refine")` is rejected unless API mode is active.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `D:\Speech\.venv\Scripts\python.exe -m unittest tests.test_app_state tests.test_tray`

Expected: failures for missing AI mode/profile methods and tray protocol members.

- [ ] **Step 3: Implement hot-switch lifecycle**

Add `ai_profile: str = "clean"` and `ai_glossary: str = ""` to `AppSettings`. Add these `SpeechApp` methods:

```python
def current_ai_mode(self) -> str: ...
def current_ai_profile(self) -> str: ...
def set_ai_mode(self, mode: str) -> None: ...
def set_ai_profile(self, profile: str) -> None: ...
```

Off and API call `postprocessor.unload()`. Local persists first, posts a loading notice, and starts a daemon worker that calls `postprocessor.load(self.settings)`. Every path refreshes window, tray, and runtime state without restarting Parakeet.

- [ ] **Step 4: Add tray radio menus**

Add `Transcript polish` with Off/Local/API and `Polish style` with Clean/Refine. Refine is enabled only in API mode. Checked state is read from the application protocol.

- [ ] **Step 5: Run focused and full Python tests**

Run: `D:\Speech\.venv\Scripts\python.exe -m unittest discover -s tests`

Expected: all tests pass.

### Task 2: Glossary and safe API profiles

**Files:**
- Create: `speech_app/glossary.py`
- Create: `tests/test_glossary.py`
- Modify: `speech_app/api_corrector.py`
- Modify: `speech_app/postprocess.py`
- Modify: `tests/test_correctors.py`
- Modify: `tests/test_postprocess.py`

- [ ] **Step 1: Write failing glossary and API contract tests**

Cover canonical lines (`DeepSeek`), alias lines (`Deep-Seag -> DeepSeek`), malformed-line skipping, profile-specific instructions, JSON extraction, and rejection of an assistant response containing headings, a numbered list, or an emoji.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `D:\Speech\.venv\Scripts\python.exe -m unittest tests.test_glossary tests.test_correctors tests.test_postprocess`

Expected: failures for the missing parser, non-JSON API response handling, and profile validator.

- [ ] **Step 3: Implement glossary parsing**

Define:

```python
@dataclass(frozen=True, slots=True)
class GlossaryTerm:
    alias: str
    canonical: str

def parse_glossary(value: str) -> list[GlossaryTerm]: ...
def apply_glossary(text: str, terms: list[GlossaryTerm]) -> str: ...
```

Apply explicit aliases case-insensitively on word-like boundaries. Canonical-only entries are prompt context and are not fuzzy-replaced locally.

- [ ] **Step 4: Harden the API request**

The system message identifies the transcript as untrusted document data and forbids answering it. The user message wraps text in `<transcript>` delimiters and requests:

```json
{"corrected_text":"..."}
```

Include `response_format: {"type": "json_object"}` while retaining fallback parsing for providers that return fenced JSON text.

- [ ] **Step 5: Implement profile validators**

Clean uses length ratio `0.80..1.25` and at least 75% normalized source-token retention. Refine uses `0.65..1.45` and at least 55% retention. Reject newly introduced Markdown headings/lists, assistant preambles, or emojis. Existing protected entity checks remain mandatory.

- [ ] **Step 6: Run focused and full Python tests**

Run: `D:\Speech\.venv\Scripts\python.exe -m unittest discover -s tests`

Expected: all tests pass and the recorded MiMo-style response is rejected.

### Task 3: Tauri settings bridge and controls

**Files:**
- Modify: `tauri/src-tauri/src/main.rs`
- Modify: `tauri/src/main.tsx`
- Modify: `tauri/src/styles.css`

- [ ] **Step 1: Extend the Rust settings bridge**

Return and persist `aiProfile` and `aiGlossary` alongside existing AI fields. Preserve all unknown Python settings during writes.

- [ ] **Step 2: Add profile and glossary controls**

In the Transcript polish panel, add a Clean/Refine segmented control and glossary textarea. Disable Refine in Local mode and show the concise reason `Refine uses API`.

- [ ] **Step 3: Build frontend and Rust bridge**

Run:

```powershell
cd D:\Speech\tauri
npm run build
cargo check --manifest-path src-tauri\Cargo.toml
```

Expected: both commands succeed without TypeScript or Rust errors.

### Task 4: Fixed viewport and adaptive rail

**Files:**
- Modify: `tauri/src/styles.css`
- Modify: `tauri/src/main.tsx`
- Modify: `tauri/src-tauri/tauri.conf.json`

- [ ] **Step 1: Fix ownership of scrolling**

Set `html`, `body`, `#root`, and `.app-shell` to the available viewport height. Set global overflow to hidden. Make `.stage` a `min-height: 0` flex column and `.page` the single `overflow-y: auto` content owner.

- [ ] **Step 2: Keep sidebar full-height**

Set `.shelf` to `height: 100%`, `min-height: 0`, and `overflow: hidden`. Keep the model ticket pinned to the bottom with `margin-top: auto`.

- [ ] **Step 3: Replace top navigation breakpoint with rail**

At `max-width: 980px`, keep two columns and shrink the shelf to 92px. Hide brand text, nav secondary labels, and model ticket. Center compact nav labels without moving navigation above content.

- [ ] **Step 4: Compact content at supported sizes**

At narrow widths, stack control and history grids, reduce panel padding, keep text wrapping, and preserve independent history scrolling. Lower Tauri `minWidth` only if the 760px screenshot remains coherent.

- [ ] **Step 5: Rebuild frontend**

Run: `cd D:\Speech\tauri; npm run build`

Expected: successful Vite build.

### Task 5: Rendered QA, release, and publication

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/plans/2026-06-28-polish-controls-responsive-shell.md`

- [ ] **Step 1: Start the Vite surface for screenshot QA**

Run: `cd D:\Speech\tauri; npm run dev -- --host 127.0.0.1`

The flow under test is: app loads -> Controls and History render -> navigation remains fixed while only page content scrolls.

- [ ] **Step 2: Capture Playwright screenshots**

Capture 1120x760, 900x650, and 760x560 screenshots outside the repository. Assert `document.documentElement.scrollHeight === document.documentElement.clientHeight`, sidebar bottom stays within the viewport, and the active page has internal overflow when required.

- [ ] **Step 3: Update public documentation**

Document tray switching, Clean/Refine behavior, glossary syntax, Local Clean limitation, and API privacy behavior.

- [ ] **Step 4: Run final checks**

Run Python tests, `npm run build`, `cargo check`, `git diff --check`, and `npm run tauri:build`.

Expected: all checks and Windows bundles succeed.

- [ ] **Step 5: Restart and verify runtime**

Run `D:\Speech\speech.ps1 restart`, wait for `data/runtime_state.json` to report Parakeet loaded and the configured AI state, then open the rebuilt UI.

- [ ] **Step 6: Commit and push**

Commit implementation with `Add polish profiles and responsive controls` and push `main` to `origin` after confirming the worktree contains no model files, user data, or API keys.
