# Arcade RE plan

Goal: enough clean-room spec to build an Arcade-style interactive demo builder.
Scope: the **interactive demo** product (extension capture, editor, player, share/embed,
analytics, AI copy/voice/translation, exports). The AI-video / prompt-video product is
out of scope except where it touches flows.

## Sources and method

| Source | How obtained | Tooling | Status |
| --- | --- | --- | --- |
| Capture extension CRX v1.9.33 | Web Store update URL | unzip → Wakaru (webpack unpack) → REA `analyze_javascript_application` (format directory, ≤50 s timeout per batch, record-and-continue) → targeted reading | **Done** for background, recording-manager, offscreen; popup/page-editor by UI strings |
| AI-video extension CRX v1.0.26 | same | unpacked + Wakaru | Not analysed (out of scope) |
| Web app bundles | `_buildManifest.js` crawl, 3,095 chunks | Wakaru `--unpack=auto` (Turbopack) for all chunks; `rg` over raw chunks for strings/call shapes; SDK extractor script | **Done** for shared types, flow model, step builder, schemas, SDK surface, embed code, analytics |
| Standalone player runtime | embed loader → runtime → `initial-*.js` | Wakaru single file | **Done** for tracker, navigation, pan-zoom; other components skimmed |
| Public share JSON / embed payload | 2 public demos | key-shape listing only | Done |
| Help center / pricing | public pages | WebFetch | Done for plans |
| Desktop app | — | — | **Not fetched** (gap) |
| Authenticated API responses | — | — | **Not exercised** (no account used) |

REA tips that worked: do not analyse the whole extension in one call (MCP timeout); pass
a few `source_paths` with `analysis_timeout_ms` ≤ 50000. Use `rg -o '.{0,N}needle.{0,M}'`
on minified chunks; `grep -E` with long context hung. Turbopack keeps export names
(`e.s(["name",0,value])`), so search by export name first.

## Status by area

| Area | Depth | Doc |
| --- | --- | --- |
| Capture modes & state machine | detailed (decompiled) | capture/recording-session.md |
| Click/event capture, selector, frame geometry | detailed (decompiled) | capture/click-and-event-capture.md |
| Hotspot coordinates | exact (decompiled) | capture/hotspot-coordinates.md |
| Screenshot loop, video, ffmpeg remux | detailed (decompiled) | capture/screenshot-loop.md, video-recording.md |
| HTML capture | detailed (decompiled) | capture/html-capture.md |
| Upload/finalize API sequence | detailed (decompiled) | capture/upload-and-finalize.md |
| Step builder | exact algorithm (decompiled) | capture/step-builder.md |
| Flow/step/hotspot model + write API | detailed (decompiled + observed) | model/*.md, schemas/flow.schema.json |
| Branching resolution | exact (decompiled) | model/overlays-branching-forms.md |
| Forms submit | exact payload (static-bundle) | model/overlays-branching-forms.md |
| Pan-zoom math | exact (decompiled) | model/pan-zoom-and-image-edits.md |
| Variables, translations, voice | detailed (decompiled + observed) | model/variables-translations-voice.md |
| Player runtime | medium (decompiled; layout math partly inferred) | player/runtime.md |
| Embed/share | detailed (decompiled + observed) | player/embed-and-share.md |
| Analytics events & transport | detailed (decompiled) | player/analytics-events.md |
| Editor UI | medium (routes + SDK; UI not walked) | editor/overview.md |
| AI features | API shapes only (prompts are server-side) | editor/ai-features.md |
| Exports | request schema + job states; renderer inferred | editor/exports.md |
| Insights/leads/integrations | routes only | api-notes.md |
| Pricing gates | static-help + flags | arcade-analysis/plans-and-gating.md |

## Next passes (if more RE is wanted)

1. Player layout: read the stage-dimension hook and callout placement in the runtime to replace "inferred" in player/runtime.md (stage sizing, tooltip placement algorithm, mobile layouts).
2. Editor components: hotspot drag/resize constraints, video trimmer, overlay editor, Script View — from `/flows/[pid]/edit` chunks.
3. Insights: response shapes via a test workspace we own (observed), plus the insights page chunk.
4. Custom links and collections: doc shapes from their editor chunks.
5. Desktop app: download from `/desktop/download`, unpack (likely Electron or native macOS), document capture + native messaging protocol.
6. AI-video extension (`plbpm…`) only if the AI-video product comes into scope.
