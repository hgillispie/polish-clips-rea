# Evidence index

All artifacts below live **only** on the REA box under `/workspace/arcade-rea-research/`
(not committed). Hashes let a later operator confirm they are reading the same build.
Captured 2026-10-22 (America/New_York).

## Sources

| Id | Artifact | sha256 | Method |
| --- | --- | --- | --- |
| CRX-DEMO | Extension `gagidkjllbdgggpboolfmmdpeagghjlm` v1.9.33 (.crx) | `29dcf2ee…bace09` | Chrome Web Store update URL → unzip → Wakaru per script (`recovered/crx-<id>/<script>/`) → REA `analyze_javascript_application` |
| CRX-VIDEO | Extension `plbpmcliejllllhnalcbmggjkchokpbg` v1.0.26 (.crx) | `9fe2d426…4b39a5` | same; **not analysed** |
| WEB-MANIFEST | `_buildManifest.js` (build `build-TfctsWXpff2fKS`) | `414ebf76…2e67b5` | public fetch |
| WEB-CHUNKS | 3,095 app chunks (83 MB) | per file | crawl of manifest + referenced chunks → Wakaru (`recovered/web/<chunk>/`, 3,077 dirs) |
| WEB-TYPES | chunk `0m7xwbybecy9z` (shared enums, step helpers, embed code, translations) | `713f5150…4c2527` | Wakaru modules 5477783, 5113004 |
| WEB-CAPTURE | chunk `3b8hl8wiv0aq3` (flow doc mapper, step builder, extension bridge) | `77f841e5…5e97` | Wakaru modules 5359430, 5320411 |
| WEB-SCHEMAS | chunk `40adxs6wx5j4s` (flow write zod schemas, flows SDK) | `e4d6e77c…6eee7` | Wakaru module 4842764 |
| WEB-ANALYTICS | chunk `2x9c9bqxe30w3` (viewer analytics publisher) | `e30a81da…70274` | Wakaru module 9850660 |
| EMBED-LOADER | `demo…/embed/v1/loader.js` | `999883dd…14c6f3` | public fetch, prettified |
| EMBED-RUNTIME | `initial-LaT5BJ19.js` (standalone player) | `c28f502d…f0919d` | Wakaru → `recovered/embed-runtime-initial.js` (158k lines) |
| PUBLIC-FLOWS | `_next/data/…/share/{id}.json` for 2 public demos + embed payload | — | public fetch; only key shapes used |
| HELP | docs.arcade.software KB (plans), arcade.software/pricing, /pricing-interactive-demos | — | WebFetch/WebSearch |
| REA-1 | `ev_22bdf6a96ecaf766badfe673830c5c65b207eaef164f34b3d95055b8d38f676f` | dir sha `5cda3b14…c9408b` | REA analysis of manifest, offscreen, embed-diagnostics |
| REA-2 | `ev_0da20ae5ae686ad24f7d5453dc1a0e48562b7ab1c71b044c82d8d7183250c9f7` | — | REA analysis of background.js (181/235 functions examined; partial) |

Local helper outputs: `api-paths-raw.txt` (270 `/api` strings), `export-names.txt` (968
Turbopack export names), `sdk-surface.json|txt` (SDK method → verb/path), `fwt.txt`
(`fetchWithToken` call sites), `flow-shape.txt`.

## Doc → evidence

| Doc | Main evidence |
| --- | --- |
| arcade-analysis/extension.md | CRX-DEMO manifest + background/recording-manager/popup/page-editor, REA-1, REA-2 |
| arcade-analysis/build-and-hosts.md | WEB-MANIFEST, EMBED-LOADER, EMBED-RUNTIME, PUBLIC-FLOWS |
| arcade-analysis/plans-and-gating.md | HELP, PUBLIC-FLOWS (`features`), WEB-CHUNKS (metering transaction, flags) |
| capture/recording-session.md, click-and-event-capture.md, screenshot-loop.md, video-recording.md, html-capture.md, upload-and-finalize.md | CRX-DEMO (background ~L16400–27600 of Wakaru entry, recording-manager, offscreen) |
| capture/hotspot-coordinates.md | CRX-DEMO `getClickPos`; WEB-CAPTURE tab-size fix |
| capture/step-builder.md, desktop-capture.md | WEB-CAPTURE module 5320411 |
| model/flow-model.md | WEB-CAPTURE 5359430 (`getFlowFromDoc`), WEB-SCHEMAS 4842764, PUBLIC-FLOWS |
| model/steps.md, hotspots-and-callouts.md | WEB-TYPES 5113004 (`oldStepToStep`, guards), PUBLIC-FLOWS |
| model/overlays-branching-forms.md | WEB-TYPES (`getNextNonEmptyAutoStep`), EMBED-RUNTIME (navigation hook), WEB-CHUNKS (`/api/viewer/form`) |
| model/pan-zoom-and-image-edits.md | EMBED-RUNTIME zoom hook, WEB-CHUNKS `update-step` |
| model/variables-translations-voice.md | WEB-TYPES, WEB-SCHEMAS flows SDK, synthetic-voice SDK, PUBLIC-FLOWS translations |
| player/* | EMBED-RUNTIME (tracker class, `report(...)` call sites), WEB-TYPES `getEmbedCode`, WEB-ANALYTICS, EMBED-LOADER |
| editor/* | WEB-CHUNKS SDK factories and call sites, WEB-SCHEMAS |
| api-notes.md | CRX-DEMO API client, `sdk-surface.txt`, `fwt.txt`, `api-paths-raw.txt` |

## Tag counts policy

Every table row or pseudocode block in `docs/pseudocode/**` names its evidence in the
file header or inline. "inferred" marks anything not directly seen in code or a response.
