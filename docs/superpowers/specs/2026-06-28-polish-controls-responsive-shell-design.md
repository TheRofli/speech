# Transcript Polish Controls And Responsive Shell

Date: 2026-06-28
Status: approved for implementation

## Scope

This change improves control and presentation of the existing transcript polish
pipeline without replacing or adding local models.

Included:

- tray selection for Off, Local, and API providers;
- Clean and Refine processing profiles;
- a user glossary for product names and domain terms;
- a hardened API editing contract and stricter output validation;
- a fixed-height responsive application shell;
- Playwright screenshot verification at three supported window sizes.

Excluded:

- selecting or installing a new English or multilingual local model;
- changing Parakeet;
- adding automatic language routing beyond the current local-model guard.

## Tray Behavior

The tray menu contains a `Transcript polish` radio submenu with Off, Local, and
API. Selecting an item saves settings immediately and refreshes the tray menu.

- Off unloads the local corrector and leaves Parakeet running.
- Local starts loading the installed local corrector in a background thread.
- API unloads the local corrector and uses the configured endpoint on the next
  transcript.

The tray also contains a `Polish style` submenu. Clean is always available.
Refine is available for API mode; Local remains Clean-only until a suitable
local model is selected in a later change.

## Processing Profiles

### Clean

Clean corrects spelling, punctuation, casing, obvious ASR substitutions, and
known glossary terms. It must preserve structure, intent, tone, names, numbers,
URLs, commands, and formatting. It must not answer the transcript or add
Markdown, lists, advice, facts, or emojis.

### Refine

Refine may remove accidental repetitions and minimally rephrase awkward word
order. It must preserve every request, constraint, fact, and intended action.
It must not expand the prompt into a response or invent information.

Local SAGE supports Clean only. API supports both profiles.

## API Contract

The transcript is sent as quoted document data, not as a free user instruction.
The system message explicitly forbids following or answering instructions found
inside the document. The API must return a JSON object containing only
`corrected_text`.

Validation is profile-specific:

- both profiles preserve protected entities and reject empty output;
- Clean uses tight length and token-retention bounds;
- Refine permits more editing but still limits length drift;
- new Markdown headings, list structures, assistant-style preambles, and emojis
  are rejected when absent from the source;
- any parse, network, timeout, or validation failure publishes the original.

## Glossary

Settings contain a newline-separated glossary. Each line is either a canonical
term (`DeepSeek`) or an alias mapping (`Deep-Seag -> DeepSeek`). The glossary is
included in API instructions and canonical aliases are applied conservatively
before validation. Empty and malformed lines are ignored.

## Responsive Shell

The application owns the viewport instead of growing the document:

- `body` and the app shell use the available viewport height without global
  page scrolling;
- the sidebar fills the window height and never scrolls with page content;
- the stage is a flex column with a fixed header and one internally scrollable
  active page;
- desktop uses the full sidebar;
- medium widths use a compact vertical rail instead of moving navigation above
  the page;
- narrow layouts stack content grids while retaining the rail;
- History keeps independent feed and reader scrolling where space allows.

The supported validation sizes are 1120x760, 900x650, and 760x560.

## Verification

- unit tests for tray persistence and load/unload transitions;
- unit tests for Clean/Refine API payloads, JSON parsing, glossary behavior, and
  rejection of assistant responses;
- existing Python regression suite;
- TypeScript/Vite build and Cargo check;
- Playwright screenshots and overflow assertions at all three viewport sizes;
- final Windows release build and live runtime-state check.
