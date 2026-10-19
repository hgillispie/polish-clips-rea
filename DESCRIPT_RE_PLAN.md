# Plan: Polish Clips, from Descript's public surface

Status: scope locked on 2026-10-19. Desktop shell confirmed. API shapes taken from the staging OpenAPI. No application code in this revision.

Evidence tags: **static** (a file or the OpenAPI), **observed** (seen during a session), **inferred** (reasoned from those), and for the 2026-10-19 web bundle: **decompiled** (Wakaru modules), **static-bundle** (string or slice of minified JS), **static-help** (a help URL embedded in the client or a help page). Recovered JavaScript is not committed.

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
10. Editor additions, after the single-camera canvas: voiceover (punch-in), image/video/GIF overlays, optional stock search, self-record with a local matte, waveform alignment for two clips.
11. Later AI, now specified from the public web bundle as well as help: skin smoothing (`beautifyRequested`, 5 AI credits on first apply), image object removal (video inpainting off by default), and a consented voice clone. Punch-in voiceover is the default way to replace a line.
12. Later, specified from that bundle, not a polish-pipeline stage: Eye Contact (`com.descript.eyeContact`, `POST /projects/{id}/eye_gaze_correction`, 10 AI credits, no UI params), the Look Good suite sharing `background_removal` → `background_mask`, Center active speaker (`face_tracking`), Video Regenerate (`lip_sync` variant `imputation`), and Publish AI (`suggest-title`, `youtube-description-v2`, `show-notes-v2`, skill `prepare-for-publish`).

Eye Contact is not skin smoothing. Translate/dub is the same `lip_sync` endpoint with variant `translation` and stays out of the default build. Kebab `generate-video` is a different action and stays out. Rooms, Brand Studio, and collaboration stay later. A voice that sounds like a person is out of the default build until [docs/pseudocode/voice-consent.md](docs/pseudocode/voice-consent.md) is satisfied. Video Regenerate adds a second, visual confirmation before the imputation POST.

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

### Public web bundle (decompiled, 2026-10-19)

Hunter authorized a clean-room decompile of the public `web.descript.com` bundles for this workstream. Build `react19/9a29d61183bce669600a9dd9a1f8588d708becac`. Source maps returned HTTP 404. Wakaru 1.14.0 unpacked effect chunks 1445, 1356, and 8630 (314 modules). Chunk `88.fc0ea62a7f115f3adca9.js` was sliced rather than fully unpacked. REA `analyze_javascript_application` evidence id `ev_7f2cc1e5aaf2e49b4b1c2bbf8e82b01d74d8689a63f6258c5ee19766604782cd`.

Login-walled editor routes were not fetched. No weights were committed. Specs cite HD ids, endpoints, flags, and parameter vectors. They do not contain recovered modules. That authorization is not a license to paste proprietary source, bypass auth, or commit a HAR.

### Public API is the preferred black box (static)

Base URL in the OpenAPI `servers` entry: `https://descriptapi.com/v1`. Human docs: [docs.descriptapi.com](https://docs.descriptapi.com/). This repo's shapes come from `https://staging-docs.descriptapi.com/openapi.yaml` (OpenAPI 3.0, info version `1.2`, fetched 2026-10-19). Summary: [docs/api-notes.md](docs/api-notes.md).

Auth is a Bearer token scoped to one Drive. Import spends **media minutes** and returns HTTP 402 when they run out. Agent edits spend **AI credits** and return HTTP 402 when those run out. Jobs are asynchronous: create, then poll `GET /v1/jobs/{job_id}` until `job_state` is `stopped`, then read `result.status`.

The spec's own agent examples cover filler-word removal, Studio Sound, captions, and highlight clips as **natural-language prompts**, not as separate REST operations. Eye contact does not appear as an operation or schema field on that OpenAPI. The web client posts it to `api.descript.com` instead (`eye_gaze_correction`). Caption font, color, position, and burn-in are also absent from the OpenAPI: Polish Clips styles those locally.

## 3. Constraints that still apply

1. **Clean-room split.** Specs and pseudocode here; implementation later, from those specs. Do not paste Descript source into the new codebase.
2. **Terms and this workstream.** A third-party tracker reports that Descript's terms prohibit decompiling the app and uncovering source or trade secrets. That page was not re-read here, so the report stays unverified. Hunter authorized clean-room notes from the public web bundles already collected (section 2). That removes "do not decompile" as a blocker for writing these specs. It does not authorize pasting recovered JavaScript, minified bundles, or Wakaru output into git, and it does not authorize authenticated scraping or a login bypass.
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

[docs/api-notes.md](docs/api-notes.md) records public OpenAPI shapes, job states, and 402 versus 429, and the separate `api.descript.com` project routes for eye gaze, background removal, face tracking, lip sync, and speech enhancement. The public spec still has no word-level JSON and no filler-ignore field.

Optional next measurement, with a test-Drive token that is never committed:

- `POST /v1/jobs/import/project_media` on one fixture, poll until `stopped`.
- `POST /v1/jobs/agent` with a filler + Studio Sound + captions prompt, poll, record `result.agent_response`, `ai_credits_used`, and `media_seconds_used`.
- `POST /v1/export/transcript` with `format: srt`.
- Note whether the transcript still contains the filler words (ignore) or has dropped them (hard delete). That single observation decides how faithfully the API backend can match our ignore semantics.

Anything the API already does does not need bundle analysis.

### Phase 3 — web app (public bundle done for this set)

Hunter's go covers the public entry bundles. Specs for Eye Contact, the Look Good suite, Video Regenerate (imputation), Publish AI, skin smoothing, and Studio Sound's `speech_enhancement` payload are written from that pass. Further bundle work is for gaps those specs still mark unknown (lip-sync score, `ActiveSpeakerFramesEncodedSchema` fields, skin-smoothing HTTP if one exists, Helland vs Linear). Authenticated HAR capture is still optional and stays out of git. Grok Bot does not see a logged-in browser on your Mac unless you attach one.

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
- [docs/pseudocode/editor/](docs/pseudocode/editor/) — timeline, layers, mixer, edits, render, UI wires, voiceover, overlays, stock providers, self-record, waveform align
- [docs/descript-analysis/](docs/descript-analysis/) — bundle-backed notes for Eye Contact, the enhance suite, Video Regenerate, Publish AI, and skin smoothing; object removal and voice clone remain thinner
- [docs/pseudocode/visual-effects-model.md](docs/pseudocode/visual-effects-model.md), [eye-contact.md](docs/pseudocode/eye-contact.md), [enhance-video-suite.md](docs/pseudocode/enhance-video-suite.md), [green-screen.md](docs/pseudocode/green-screen.md), [portrait-lighting.md](docs/pseudocode/portrait-lighting.md), [uplighting.md](docs/pseudocode/uplighting.md), [blur-speaker-background.md](docs/pseudocode/blur-speaker-background.md), [chroma-key.md](docs/pseudocode/chroma-key.md), [color-adjustments.md](docs/pseudocode/color-adjustments.md), [center-active-speaker.md](docs/pseudocode/center-active-speaker.md)
- [docs/pseudocode/video-regenerate.md](docs/pseudocode/video-regenerate.md), [youtube-titles-descriptions.md](docs/pseudocode/youtube-titles-descriptions.md)
- [docs/pseudocode/skin-smoothing.md](docs/pseudocode/skin-smoothing.md), [studio-sound.md](docs/pseudocode/studio-sound.md), [object-removal.md](docs/pseudocode/object-removal.md), [voice-consent.md](docs/pseudocode/voice-consent.md)

### Phase 6 — build and verify (later PR)

Implement from the pseudocode only. Run the same fixtures through the open-source stack and, if a token exists, through one Underlord job. Compare word timings, which fillers were ignored versus deleted, cut points, loudness, and caption timing. Differences become tickets or accepted gaps.

## 5. Build hypothesis

A Descript API job plus a rescript-like transcript editor is a better MVP than cloning `web.descript.com`. The editor owns the word model and ignore flags. The API is an optional backend for import, transcription, Studio Sound, and publish. [docs/reuse-rescript.md](docs/reuse-rescript.md) explains why the current rescript tree is a reference, not a vendored dependency: its `LICENSE` is PolyForm Noncommercial 1.0.0 (GitHub displays that as "Other").

## 6. Where to continue

[README.md](README.md) is the operator index. [docs/grokbot-rea.md](docs/grokbot-rea.md) is the REA connection note. Implementation starts at [docs/pseudocode/polish-pipeline.md](docs/pseudocode/polish-pipeline.md).
