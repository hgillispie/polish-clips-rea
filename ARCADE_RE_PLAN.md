# Arcade RE plan

Goal: enough clean-room spec to build an Arcade-style interactive demo builder.
Scope: the **interactive demo** product (extension capture, editor, player, share/embed,
analytics, AI copy/voice/translation, exports). The AI-video / prompt-video product is
out of scope except where it touches flows.

## Sources and method

| Source | How obtained | Tooling | Status |
| --- | --- | --- | --- |
| Capture extension CRX v1.9.33 | Web Store update URL | unzip → Wakaru (webpack unpack) → REA `analyze_javascript_application` (format directory, ≤50 s timeout per batch, record-and-continue) → targeted reading | **Done** for background, recording-manager, offscreen, popup, page-editor (pass 2: REA on Wakaru entries) |
| AI-video extension CRX v1.0.26 | same | Wakaru + REA (background/cursor-tracker/recorder) + reading sidepanel | **Done** (pass 2): capture + AI pipeline |
| Web app bundles | `_buildManifest.js` crawl, 3,095 chunks | Wakaru `--unpack=auto` (Turbopack) for all chunks; `rg` over raw chunks for strings/call shapes; SDK extractor script | **Done** for shared types, flow model, step builder, schemas, SDK surface, embed code, analytics |
| Standalone player runtime | embed loader → runtime → `initial-*.js` | Wakaru single file | **Done** for tracker, navigation, pan-zoom; other components skimmed |
| Public share JSON / embed payload | 2 public demos | key-shape listing only | Done |
| Help center / pricing | public pages | WebFetch | Done for plans |
| Desktop app 3.5.21 (mac) | `/desktop/download` DMG | 7z → asar extract → Wakaru main + renderers → REA on `lib/main.js`; agent strings | **Done** (pass 2) for main/renderer; native agent strings only |
| Authenticated traffic | 4 HARs from our own Free workspace | `tools/har-shapes/har_shapes.py` (type shapes only, local outputs) | **Done** (pass 2) for home/editor/translate/publish/settings/billing/brand kits |

REA tips that worked: do not analyse the whole extension in one call (MCP timeout); pass
a few `source_paths` with `analysis_timeout_ms` ≤ 50000. Use `rg -o '.{0,N}needle.{0,M}'`
on minified chunks; `grep -E` with long context hung. Turbopack keeps export names
(`e.s(["name",0,value])`), so search by export name first.

## Status by area

| Area | Depth | Doc |
| --- | --- | --- |
| Capture modes & state machine | detailed (decompiled) | capture/recording-session.md |
| Click/event capture, selector, frame geometry | detailed (decompiled) | capture/click-and-event-capture.md |
| Hotspot coordinates | exact (decompiled; render + clamp decompiled in pass 2) | capture/hotspot-coordinates.md |
| Desktop capture + upload/handoff | detailed (decompiled; agent static-binary) | arcade-analysis/desktop-app.md, capture/desktop-capture.md |
| AI-video extension capture + AI pipeline | detailed (decompiled) | arcade-analysis/ai-video-extension.md |
| Signed-in network (routes, Firestore, page props) | detailed (observed-network) | arcade-analysis/observed-network.md |
| Screenshot loop, video, ffmpeg remux | detailed (decompiled) | capture/screenshot-loop.md, video-recording.md |
| HTML capture | detailed (decompiled) | capture/html-capture.md |
| Upload/finalize API sequence | detailed (decompiled) | capture/upload-and-finalize.md |
| Step builder | exact algorithm (decompiled) | capture/step-builder.md |
| Flow/step/hotspot model + write API | detailed (decompiled + observed + observed-network; schema validated on 7 real docs) | model/*.md, schemas/flow.schema.json |
| Branching resolution | exact (decompiled) | model/overlays-branching-forms.md |
| Forms submit | exact payload (static-bundle) | model/overlays-branching-forms.md |
| Pan-zoom math | exact (decompiled) | model/pan-zoom-and-image-edits.md |
| Variables, translations, voice | detailed (decompiled + observed) | model/variables-translations-voice.md |
| Player runtime | medium (decompiled; layout math partly inferred) | player/runtime.md |
| Embed/share | detailed (decompiled + observed) | player/embed-and-share.md |
| Analytics events & transport | detailed (decompiled) | player/analytics-events.md |
| Editor UI | medium (routes + SDK + observed save/upload sequence) | editor/overview.md |
| AI features | API shapes only (prompts are server-side) | editor/ai-features.md |
| Exports | request schema + job states; renderer inferred | editor/exports.md |
| Insights/leads/integrations | routes only; insights confirmed client-side sample data on Free | api-notes.md, player/analytics-events.md |
| Pricing gates | static-help + flags + observed metering/paywall/prices | arcade-analysis/plans-and-gating.md |

## Next passes (if more RE is wanted)

1. Insights: publish a demo, generate real views (or use a Growth trial), and HAR the team/flow insights pages to get `/api/insights/*` shapes.
2. Exports: start a GIF and an MP4 export on a trial, and HAR the `exports` doc lifecycle.
3. AI hotspot/copy (`/api/ai/flow-hotspots`, `/api/arcade-ai`) and record-with-AI: HAR one extension capture with Avery on, including `/api/extension/*` uploads.
4. Player layout: read the stage-dimension hook and callout placement in the runtime to replace "inferred" in player/runtime.md.
5. Editor components: hotspot drag/resize constraints, video trimmer, overlay editor, Script View.
6. Desktop agent: decompile the arm64 slice with Ghidra on a box that has Java, or REA native on macOS, to pin the event JSON encoders and the CapsLock behaviour.
7. Custom links and collections: doc shapes (collections are paywalled on Free; needs a trial).
