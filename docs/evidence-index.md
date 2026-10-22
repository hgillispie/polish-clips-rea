# Evidence index

All artifacts below live **only** on the REA box under `/workspace/arcade-rea-research/`
(not committed). Hashes let a later operator confirm they are reading the same build.
Captured 2026-10-22 (America/New_York).

## Sources

| Id | Artifact | sha256 | Method |
| --- | --- | --- | --- |
| CRX-DEMO | Extension `gagidkjllbdgggpboolfmmdpeagghjlm` v1.9.33 (.crx) | `29dcf2ee…bace09` | Chrome Web Store update URL → unzip → Wakaru per script (`recovered/crx-<id>/<script>/`) → REA `analyze_javascript_application` |
| CRX-VIDEO | Extension `plbpmcliejllllhnalcbmggjkchokpbg` v1.0.26 (.crx) | `9fe2d426…4b39a5` | same; analysed in pass 2 (REA-5, reading of `recovered/crx-plbpm…/{background,sidepanel,producer-recorder,cursor-tracker}`) |
| DESKTOP-DMG | `Arcade-3.5.21.dmg` (macOS, 262 MB) | `fa31e3a4…4691b01b` | `/desktop/download` → 7z extract |
| DESKTOP-ASAR | `Arcade.app/Contents/Resources/app.asar` | `3314c59a…e8cb0fc1` | asar extract → `raw/desktop/asar/`; `lib/main.js` Wakaru → `recovered/desktop/main/module-*.js`; REA-4 |
| DESKTOP-AGENT | `agent/arcade-agent` (universal Mach-O x86_64+arm64, Swift) | `8c40cfbf…c1d7819e` | `strings`/symbol listing only (no native decompiler on this box) |
| HAR-1..4 | Signed-in HARs `01-home`, `02-editor`, `03-insights`, `04-settings-billing-collections` (own Free workspace) | `16a600b1…2f68ba6e`, `4938ad5f…e669616f`, `1b6b05e1…26a2eeb0`, `37c97437…16bb240a` | `tools/har-shapes/har_shapes.py` → type skeletons in `har-analysis/` (local). **Contain tokens, cookies and PII; never commit** |
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
| REA-2 | `ev_0da20ae5ae686ad24f7d5453dc1a0e48562b7ab1c71b044c82d8d7183250c9f7` | — | REA analysis of raw background.js. "181/235" is the analysis-view item count (view `ev_ded1657d…`, status complete-within-view): graph items, not functions. 24 unselected files explain the remainder |
| REA-3 | `ev_2c2c05f03674b056d9aca1a12141a0ece0190d2665bfc86c45b4630471561f26` | entry `f07664081b30…` | Pass 2: Wakaru background `entry.js`. Whole file parsed (122k AST nodes, 0 parse failures) |
| REA-3b | `ev_9f64577305ea5b3724bab81850d39c30fed4e068fb819a06e12b81aa697527c6` | `4235b82fc4b6…` | Wakaru recording-manager `entry.js`, whole file parsed. The raw-file run timed out (partial `ev_b4831580…`) |
| REA-3c | `ev_19d585e7cd0fc5dd8cb1e2274f507a21db03b24fa3f63d1831c6782119d4cf5d` | `f916e8e8d54f…` | Wakaru popup `entry.js` (121k AST nodes) |
| REA-3d | `ev_4688d461ff6d324db102ef43cdebdca0e53baacaccad2409e8a2d14e5e0c76f3` | `f5592c3f4302…` | Wakaru page-editor `entry.js` (49k AST nodes) |
| REA-4 | `ev_0ea89bc4f6c01f4f1d15b5966a3ac59613e0a0adc25ebb1257d6c5541250d474` | asar `3314c59a…` | Desktop `lib/main.js`: 62 modules, 6 BrowserWindows, 53 `ipcMain` handlers on 43 literal channels, 15 explicit webPreferences |
| REA-5 | `ev_ee29dcabff7935d2a4aaa84dd3c47d3ad96ae7b295f1819b5a26e12c1677f4a7` | dir `fd13e8e1…` | AI-video extension manifest + background + cursor-tracker + producer-recorder (183 modules, 273k AST nodes) |

Local helper outputs: `api-paths-raw.txt` (270 `/api` strings), `export-names.txt` (968
Turbopack export names), `sdk-surface.json|txt` (SDK method → verb/path), `fwt.txt`
(`fetchWithToken` call sites), `flow-shape.txt`.

## Doc → evidence

| Doc | Main evidence |
| --- | --- |
| arcade-analysis/extension.md | CRX-DEMO manifest + background/recording-manager/popup/page-editor, REA-1, REA-2, REA-3c/d |
| arcade-analysis/desktop-app.md, capture/desktop-capture.md | DESKTOP-DMG, DESKTOP-ASAR (main modules 21, 2732, 5736, 6688, 6910, 6921, 2103, 7858), DESKTOP-AGENT strings, REA-4; WEB-CAPTURE 5320411 (builder) |
| arcade-analysis/ai-video-extension.md | CRX-VIDEO, REA-5 |
| arcade-analysis/observed-network.md | HAR-1..4 |
| arcade-analysis/build-and-hosts.md | WEB-MANIFEST, EMBED-LOADER, EMBED-RUNTIME, PUBLIC-FLOWS |
| arcade-analysis/plans-and-gating.md | HELP, PUBLIC-FLOWS (`features`), WEB-CHUNKS (metering transaction, flags) |
| capture/recording-session.md, click-and-event-capture.md, screenshot-loop.md, video-recording.md, html-capture.md, upload-and-finalize.md | CRX-DEMO (background ~L16400–27600 of Wakaru entry, recording-manager, offscreen) |
| capture/hotspot-coordinates.md | CRX-DEMO `getClickPos`; WEB-CAPTURE tab-size fix |
| capture/step-builder.md | WEB-CAPTURE module 5320411 |
| model/flow-model.md, schemas/flow.schema.json | WEB-CAPTURE 5359430 (`getFlowFromDoc`), WEB-SCHEMAS 4842764, PUBLIC-FLOWS, HAR-2/3 (Firestore + SSR + REST flow docs; schema validates all 7 observed docs) |
| model/steps.md, hotspots-and-callouts.md | WEB-TYPES 5113004 (`oldStepToStep`, guards), PUBLIC-FLOWS |
| model/overlays-branching-forms.md | WEB-TYPES (`getNextNonEmptyAutoStep`), EMBED-RUNTIME (navigation hook), WEB-CHUNKS (`/api/viewer/form`) |
| model/pan-zoom-and-image-edits.md | EMBED-RUNTIME zoom hook, WEB-CHUNKS `update-step` |
| model/variables-translations-voice.md | WEB-TYPES, WEB-SCHEMAS flows SDK, synthetic-voice SDK, PUBLIC-FLOWS translations |
| player/* | EMBED-RUNTIME (tracker class, `report(...)` call sites), WEB-TYPES `getEmbedCode`, WEB-ANALYTICS, EMBED-LOADER |
| editor/* | WEB-CHUNKS SDK factories and call sites, WEB-SCHEMAS, HAR-2/3 |
| api-notes.md | CRX-DEMO API client, `sdk-surface.txt`, `fwt.txt`, `api-paths-raw.txt`, DESKTOP-ASAR, CRX-VIDEO, HAR-1..4 |
| arcade-analysis/plans-and-gating.md (pass 2 section), player/analytics-events.md (insights + ingest) | HAR-1..4 |
| capture/hotspot-coordinates.md (rendering) | WEB-CHUNKS `2w_dfrdgx6a_7` module 5758354 (`getElementStagePosition`, `getPositionAndBounds`) |

## Tag counts policy

Every table row or pseudocode block in `docs/pseudocode/**` names its evidence in the
file header or inline. "inferred" marks anything not directly seen in code or a response.
"observed-network" claims cite only field names, types and non-identifying enum literals.
No token, cookie, email or id value from the HARs is quoted anywhere.
