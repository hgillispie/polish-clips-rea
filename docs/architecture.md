# Architecture

Polish Clips reads Descript as three layers. Only the first two matter for the pipeline. Claims are tagged **static**, **observed**, or **inferred**.

```text
┌──────────────────────────┐
│ macOS Descript 2.21.1    │  thin Electron shell (static)
│ app.asar ~1 MB JS        │  loadURL → web host
└────────────┬─────────────┘
             │
┌────────────▼─────────────┐
│ web.descript.com         │  product UI (not in the ASAR)
└────────────┬─────────────┘
             │
┌────────────▼─────────────┐
│ descriptapi.com/v1       │  documented jobs: import, agent, publish
└──────────────────────────┘

Polish Clips MVP (inferred recommendation)
┌──────────────────────────┐     optional      ┌─────────────────────┐
│ Transcript editor        │ ────────────────► │ POST /v1/jobs/agent │
│ word model + ignore flags│ ◄──────────────── │ poll job, credits   │
└────────────┬─────────────┘                   └─────────────────────┘
             │ local enhance / captions / cut
             ▼
        exported clip
```

## Desktop shell (static)

| Fact | Value |
| --- | --- |
| Path | `/Applications/Descript.app` |
| Bundle id | `com.descript.beachcube` |
| Version | 2.21.1 |
| URL schemes | `descript`, `descriptbc` |
| Package | Electron Forge, `productName` Descript, main `.webpack/main` |
| Packaged ASAR | ~987 KB; extracted JS ~1 MB |
| Extracted sha256 | `bad2f88655ce569cba1a302fcf97a03fd86bdd26d88c4005e64e8043537a8605` |
| Runtime deps in the shell | `@sentry/electron`, `electron-store`, `lodash`, `@electron/notarize` |
| Security prefs | `nodeIntegration: false`, `contextIsolation` present, `webSecurity: true`, preload `.webpack/renderer/main_window/preload.js` |

`loadURL` targets:

- prod `https://web.descript.com`
- staging `https://staging-web.descript.com` and `https://staging-api-web.descript.com`
- qa `https://qa-web.descript.com`
- local `https://local-dev.descript.com:3000`

Monorepo package names appear as devDependencies (`@descript/electron-utils`, a recorder, rust-mouse-tracker, sckit-helper). They are not shipped inside this ASAR (static). The Sentry DSN in the shell is ops configuration; ignore it for product specs.

**Implication (inferred from the static shell):** filler removal, retakes, Studio Sound, captions, and clip cutting are web and API behaviour. Re-analyzing the ASAR will not specify them.

Info.plist `ElectronAsarIntegrity` does not equal the extracted-tree sha256. That is the signed package hash (static observation of the mismatch; the exact plist hash is not needed here).

## Web app

The prod UI origin is `https://web.descript.com` (static, from the shell's host list and from `project_url` examples in the OpenAPI). Project links look like `https://web.descript.com/{project_id}` and sometimes gain a composition short-id suffix.

How the web client stores edits (operation log, CRDT, or snapshot) is **unknown**. The public API does not expose an edit log. Do not block the MVP on that question.

## API

Server URL: `https://descriptapi.com/v1` (static, OpenAPI 1.2 snapshot, 2026-10-19). Details and error tables: [api-notes.md](api-notes.md).

The job lifecycle every feature shares:

1. `POST` a job (`/jobs/import/project_media`, `/jobs/agent`, or `/jobs/publish`).
2. Receive `job_id` immediately, plus `project_id` and `project_url`.
3. Poll `GET /jobs/{job_id}` or receive the same payload on `callback_url`.
4. Stop when `job_state` is `stopped` or `cancelled`.
5. Branch on `result.status`: `success`, `partial` (import only), or `error`.

Transcript export (`POST /export/transcript`) is synchronous. It returns a file body, not a job.

## Polish Clips process

Two backends, one pipeline. The orchestrator is specified in [pseudocode/polish-pipeline.md](pseudocode/polish-pipeline.md).

| Backend | Owns | Limit |
| --- | --- | --- |
| Open stack | Word model, ignore flags, retake marks, local enhance, caption cues, caption style, optional burn-in, the editor timeline | Quality of the chosen ASR and denoiser |
| Descript API | Import + server transcription, Underlord prompt, publish URL | No word-level JSON, no ignore flag, and no caption-style schema (static). Prompt wording is the only control |

Eye contact sits beside the pipeline as a research note ([feature-inventory.md](feature-inventory.md)). It is not a stage.

The local editor (tracks, layers, mixer, transcript-linked edits) is specified under [pseudocode/editor/](pseudocode/editor/). It is our canvas, not a clone of the Descript window.

## Out of scope for this architecture

- Cloning the Descript web UI.
- Recovering native add-ons from the desktop app.
- Credential capture or auth bypass.
- Translate / dub, Rooms, Brand Studio.
- A voice clone without the consent gate in [pseudocode/voice-consent.md](pseudocode/voice-consent.md). Punch-in voiceover does not need that gate.
- Video object removal as an MVP stage. The later spec is [pseudocode/object-removal.md](pseudocode/object-removal.md).
