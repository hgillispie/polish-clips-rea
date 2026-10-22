# Handoff — branch `arcade-rea`

Date: 2026-10-22 (America/New_York). Author: Grok Bot (REA box).

## What this branch is

Clean-room reverse-engineering notes and implementable pseudocode for an
**Arcade-style interactive product demo builder**. The Descript / Polish Clips docs were
removed from this branch; they are intact on `claude/compassionate-pascal-apg87s`.

## What was done

- Fetched and unpacked both Arcade Chrome extensions via the Web Store update URL; Wakaru-decompiled every script; REA analysis of the capture extension (manifest, offscreen, embed-diagnostics, background — partial function coverage, see evidence index).
- Crawled the Next.js build manifest and downloaded all 3,095 app chunks; Wakaru-unpacked all of them (Turbopack); extracted the typed SDK surface (method → verb/path) and `fetchWithToken` call sites.
- Fetched the public embed loader and standalone player runtime; decompiled the runtime (tracker, navigation, pan-zoom).
- Sampled two public demos' share JSON and embed payload for key shapes.
- Read pricing + KB pages for plan gating.
- Wrote: architecture, feature inventory with plan gates and priorities, API notes, evidence index, extension/build/plans analysis, and pseudocode for capture (9 files), model (6 + JSON Schema validated against both public flows), player (3), editor (3).

## Key findings

- **Capture modes**: `Image` (screenshot), `Video` (tab recording), `Demo` (interactive). Demo = continuous 500 ms `captureVisibleTab` ring buffer (pick the frame just before each click) + continuous VP9 WebM via tabCapture/offscreen MediaRecorder (remuxed with ffmpeg.wasm) + per-click DOM context; optional cleaned-HTML snapshot per click (Enterprise).
- **Hotspot coords**: normalized 0..1 of the tab viewport, computed from frame screen offset + client coords (works across iframes).
- **Step builder**: each click → Image step with one 40×40 pulsating hotspot; a Video step (a time window into the single recording, sped up 1.5×/2.5×) is inserted before a click when scrolling ≥100 ms, dragging ≥50 ms, typing, media, or a ≥3 s pause happened; final screenshot becomes the last hotspot-less step.
- **Data model**: one Flow JSON document (`flows/{id}`) with `steps[]` (Image 1 / Video 2 / Overlay 3 / Empty 4); overlays have variants buttons/form/embeds; branching via `targetId` on hotspots, video end, mobile button, and overlay paths (step/url/crossFlow). Writes are `PATCH /api/flows/{id} {set, unset}`.
- **Player**: standalone runtime loaded by version (`rendererRevision`) for the web component; iframe embed with inline/tab/modal modes; Segment-style events (Step Reached, Hotspot Clicked, Overlay Clicked, CTA Clicked …) also posted to the host page via `postMessage`.
- **API surface**: `/api/extension/*` (demo-start, upload-url, image, scrape, demo-end, demo-status), `/api/flows/*` (CRUD, access, export, translations, merge, duplicate), `/api/ai/*`, `/api/synthetic-voice`, `/api/viewer/form`, insights/leads/integrations, workspace/billing.
- **Gating**: per-workspace feature map (109 named flags) + metering counters (`meteringUsage.<key>`) for panAndZoom, forms, translations, imageEditor, branching, trimVideo, menu, watermark, exports, collections, customLinks…; plans Free / Growth / Enterprise.

## Evidence gaps (be careful)

- No authenticated calls: response bodies for insights, leads, custom links, collections, exports list, AI endpoints are unknown or inferred from client reads.
- Server-side logic (AI prompts, step building in `demo-end`, export renderer) is inferred; the client-side step builder is exact and is the reference.
- Player layout details (stage sizing, tooltip placement, mobile layouts) are partly inferred.
- Desktop app not downloaded/analysed. AI-video extension unpacked but not analysed.
- REA background.js analysis covered 181/235 functions; the rest was read manually from Wakaru output.
- Popup and page-editor documented from UI strings, not full decompiled logic.

## Unfinished / suggested next work

See ARCADE_RE_PLAN.md "Next passes". For implementation, start with the model + player
against fixture flows, then the MV3 extension + step builder (pure function, unit tests).

## Where the raw material is

On the REA box: `/workspace/arcade-rea-research/` (`raw/`, `recovered/`, helper txt/json
files). Never commit it. Hashes in docs/evidence-index.md.
