# Plan: Polish Clips, from Descript's public surface

Status: scope locked on 2026-10-19. Desktop shell confirmed. API shapes taken from the staging OpenAPI. No application code in this revision.

Evidence tags used below: **static** (file or spec), **observed** (seen during the session), **inferred** (reasoned from those).

## 1. Product

**Polish Clips** is a transcript-first polish pipeline plus a local editor. It is not a 1:1 Descript clone.

In scope, in order:

1. Import and transcribe with word-level timings.
2. Filler removal with nondestructive **ignore** (strikethrough) semantics.
3. Retake removal / tighten.
4. Studio Sound–class denoise and enhance.
5. Caption cues (SRT / VTT) and a **local** caption style (font, color, position, karaoke). Style is not an OpenAPI field.
6. Clip cutting from a transcript selection.
7. Editor foundation: composition, tracks, layers, mixer, transcript-linked edits, preview. Specs in [docs/pseudocode/editor/](docs/pseudocode/editor/).
8. Caption burn-in into frames, optional on export.
9. Publish / export, secondary.

Eye contact is a research note only. It does not block the MVP. Translate, dub, green screen, Overdub, Rooms, Brand Studio, and collaboration stay later.

## 2. What is already established

### Desktop app is a thin shell (static)

macOS Descript **2.21.1** (`com.descript.beachcube`) at `/Applications/Descript.app` ships `Resources/app.asar` as a thin Electron Forge shell (packaged ~987 KB). The main process `loadURL`s a remote UI:

| Environment | Host |
| --- | --- |
| prod | `https://web.descript.com` |
| staging | `https://staging-web.descript.com`, `https://staging-api-web.descript.com` |
| qa | `https://qa-web.descript.com` |
| local | `https://local-dev.descript.com:3000` |

URL schemes: `descript`, `descriptbc`. Shell dependencies include `@sentry/electron`, `electron-store`, `lodash`, `@electron/notarize`. Dev-dependency names hint at a larger monorepo (`@descript/electron-utils`, recorder, rust-mouse-tracker, sckit-helper); those packages are not inside the shipped ASAR. Main-window security prefs in the bundle: `nodeIntegration: false`, `contextIsolation` set, preload at `.webpack/renderer/main_window/preload.js`, `webSecurity: true`.

Extracted ASAR sha256: `bad2f88655ce569cba1a302fcf97a03fd86bdd26d88c4005e64e8043537a8605`. The Info.plist ElectronAsarIntegrity hash differs because it is the signed package hash.

Polish-clip behaviour lives in the **web app and descriptapi.com**, not in this ASAR. Phase 4 from the old plan is complete: the shell is thin. Further desktop reverse engineering is not a workstream.

A Sentry DSN is present in the shell. Treat it as ops noise and do not copy it into specs.

### REA is on Grok Bot (observed)

The Grok Bot computer already runs REA as MCP: `npx -y rea-agents@6.7.0 mcp` (~207 tools). Node on that machine is 22.x. `rea analyze-javascript-application` on the Mac hit an `xcrun` / Swift ownership-helper failure; static strings and `package.json` were enough to confirm the thin shell. Live CDP or HAR remains optional if an API gap shows up, and deep bundle work still needs an explicit go.

There is no Claude Desktop config, no `/root/.claude.json`, and no Cowork setup in this plan. See [docs/grokbot-rea.md](docs/grokbot-rea.md).

### Public API is the preferred black box (static)

Base URL in the OpenAPI `servers` entry: `https://descriptapi.com/v1`. Human docs: [docs.descriptapi.com](https://docs.descriptapi.com/). This repo's shapes come from `https://staging-docs.descriptapi.com/openapi.yaml` (OpenAPI 3.0, info version `1.2`, fetched 2026-10-19). Summary: [docs/api-notes.md](docs/api-notes.md).

Auth is a Bearer token scoped to one Drive. Import spends **media minutes** and returns HTTP 402 when they run out. Agent edits spend **AI credits** and return HTTP 402 when those run out. Jobs are asynchronous: create, then poll `GET /v1/jobs/{job_id}` until `job_state` is `stopped`, then read `result.status`.

The spec's own agent examples cover filler-word removal, Studio Sound, captions, and highlight clips as **natural-language prompts**, not as separate REST operations. Eye contact does not appear as an operation or schema field. Caption font, color, position, and burn-in are also absent: Polish Clips styles those locally.

## 3. Constraints that still apply

1. **Clean-room split.** Specs and pseudocode here; implementation later, from those specs. Do not paste Descript source into the new codebase.
2. **Terms.** A third-party tracker reports that Descript's terms prohibit decompiling the app and uncovering source or trade secrets. That page was not re-read for this revision, so the report stays unverified. Public docs, the OpenAPI summary, and building from pseudocode proceed. Decompiling `web.descript.com` bundles does not, until someone reads the current terms and says go.
3. **REA's own rules.** No copying proprietary code or assets, and no bypassing authentication or access controls.
4. **Own account and content only.** No scripted use beyond what the documented API allows.
5. **Captures are sensitive.** HARs hold session tokens and media URLs. They stay out of git. Redact, then rotate the session when finished.

## 4. Phases

### Phase 0 — locked

Answered: the desktop app in this session is macOS; the feature list is the polish pipeline above; REA runs on Grok Bot; the goal is Polish Clips inside our own product, using Descript as a behavioural and API reference. Interoperability (import/export of Descript projects) is a side effect of the API, not the product goal.

### Phase 1 — fixtures (still open, no reverse engineering)

On a paid account you control, run each in-scope feature once and keep inputs and outputs **outside git**. Suggested fixtures: clean speech, speech with fillers and retakes, noisy audio. Time each run. Latency is the cheapest clue to local versus server work.

Inventory table: [docs/feature-inventory.md](docs/feature-inventory.md). Fill the "observed cost" column when a token probe happens. The table is the inventory; a CSV can be generated from it later if a spreadsheet is useful.

### Phase 2 — documented API (spec done; live probe optional)

[docs/api-notes.md](docs/api-notes.md) records request and response shapes, job states, 402 versus 429, and the gaps (no word-level JSON, no filler-ignore field, no Studio Sound intensity, no eye-contact operation).

Optional next measurement, with a test-Drive token that is never committed:

- `POST /v1/jobs/import/project_media` on one fixture, poll until `stopped`.
- `POST /v1/jobs/agent` with a filler + Studio Sound + captions prompt, poll, record `result.agent_response`, `ai_credits_used`, and `media_seconds_used`.
- `POST /v1/export/transcript` with `format: srt`.
- Note whether the transcript still contains the filler words (ignore) or has dropped them (hard delete). That single observation decides how faithfully the API backend can match our ignore semantics.

Anything the API already does does not need bundle analysis.

### Phase 3 — web app (optional, needs an explicit go)

Only if Phase 2 shows a gap the product cannot accept (for example, ignore-versus-delete, or eye contact). Passive observation and HAR inspection are the first tools. Bundle decompilation waits on the terms check in section 3. Grok Bot can inspect a **redacted** HAR or an exported script directory you choose to upload. It does not see a logged-in browser on your Mac unless you attach one.

### Phase 4 — desktop shell (done)

Confirmed thin shell, section 2. Do not schedule ASAR diffing, Electron scenario capture, or native add-on work unless a future product requirement actually lives in the shell (file dialogs, URL schemes, updates).

### Phase 5 — synthesis (this revision)

Behavioural specs with build options:

- [docs/pseudocode/polish-pipeline.md](docs/pseudocode/polish-pipeline.md)
- [docs/pseudocode/transcript-model.md](docs/pseudocode/transcript-model.md)
- [docs/pseudocode/filler-removal.md](docs/pseudocode/filler-removal.md)
- [docs/pseudocode/retake-removal.md](docs/pseudocode/retake-removal.md)
- [docs/pseudocode/studio-sound.md](docs/pseudocode/studio-sound.md)
- [docs/pseudocode/captions.md](docs/pseudocode/captions.md)
- [docs/pseudocode/caption-style.md](docs/pseudocode/caption-style.md)
- [docs/pseudocode/caption-burnin.md](docs/pseudocode/caption-burnin.md)
- [docs/pseudocode/clip-cut.md](docs/pseudocode/clip-cut.md)
- [docs/pseudocode/underlord-agent-job.md](docs/pseudocode/underlord-agent-job.md)
- [docs/pseudocode/editor/](docs/pseudocode/editor/) — timeline, layers, mixer, edits, render, UI wires

### Phase 6 — build and verify (later PR)

Implement from the pseudocode only. Run the same fixtures through the open-source stack and, if a token exists, through one Underlord job. Compare word timings, which fillers were ignored versus deleted, cut points, loudness, and caption timing. Differences become tickets or accepted gaps.

## 5. Build hypothesis

A Descript API job plus a rescript-like transcript editor is a better MVP than cloning `web.descript.com`. The editor owns the word model and ignore flags. The API is an optional backend for import, transcription, Studio Sound, and publish. [docs/reuse-rescript.md](docs/reuse-rescript.md) explains why the current rescript tree is a reference, not a vendored dependency: its `LICENSE` is PolyForm Noncommercial 1.0.0 (GitHub displays that as "Other").

## 6. Where to continue

[README.md](README.md) is the operator index. [docs/grokbot-rea.md](docs/grokbot-rea.md) is the REA connection note. Implementation starts at [docs/pseudocode/polish-pipeline.md](docs/pseudocode/polish-pipeline.md).
