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

### Pass 2 (2026-10-22)

- Downloaded the **desktop app** (macOS 3.5.21 DMG), extracted the ASAR, Wakaru'd `lib/main.js` (63 modules) and the 5 renderer bundles, and ran REA on the main script. The Swift `arcade-agent` was read through strings and symbols only. → arcade-analysis/desktop-app.md, capture/desktop-capture.md (rewritten).
- Analysed the **AI-video recorder extension** (CDP screencast capture, cursor samples, in-browser MP4 transcode with smart zoom, producer chat/brief/wizard API). → arcade-analysis/ai-video-extension.md.
- Capture extension: REA on the Wakaru entries of background, recording-manager, popup and page-editor (each file fully parsed). Popup and page-editor docs now describe decompiled logic, not UI strings. Hotspot rendering math was upgraded from inferred to decompiled.
- Parsed 4 **signed-in HARs** from our own Free workspace with `tools/har-shapes/har_shapes.py`, keeping type shapes only. → arcade-analysis/observed-network.md. Upgraded api-notes, flow-model + flow.schema.json, editor overview/AI/exports, analytics/insights, plans-and-gating and architecture auth (new tag `observed-network`).

## Key findings

- **Capture modes**: `Image` (screenshot), `Video` (tab recording), `Demo` (interactive). Demo = continuous 500 ms `captureVisibleTab` ring buffer (pick the frame just before each click) + continuous VP9 WebM via tabCapture/offscreen MediaRecorder (remuxed with ffmpeg.wasm) + per-click DOM context; optional cleaned-HTML snapshot per click (Enterprise).
- **Hotspot coords**: normalized 0..1 of the tab viewport, computed from frame screen offset + client coords (works across iframes).
- **Step builder**: each click → Image step with one 40×40 pulsating hotspot; a Video step (a time window into the single recording, sped up 1.5×/2.5×) is inserted before a click when scrolling ≥100 ms, dragging ≥50 ms, typing, media, or a ≥3 s pause happened; final screenshot becomes the last hotspot-less step.
- **Data model**: one Flow JSON document (`flows/{id}`) with `steps[]` (Image 1 / Video 2 / Overlay 3 / Empty 4); overlays have variants buttons/form/embeds; branching via `targetId` on hotspots, video end, mobile button, and overlay paths (step/url/crossFlow). Writes are `PATCH /api/flows/{id} {set, unset}`.
- **Player**: standalone runtime loaded by version (`rendererRevision`) for the web component; iframe embed with inline/tab/modal modes; Segment-style events (Step Reached, Hotspot Clicked, Overlay Clicked, CTA Clicked …) also posted to the host page via `postMessage`.
- **API surface**: `/api/extension/*` (demo-start, upload-url, image, scrape, demo-end, demo-status), `/api/flows/*` (CRUD, access, export, translations, merge, duplicate), `/api/ai/*`, `/api/synthetic-voice`, `/api/viewer/form`, insights/leads/integrations, workspace/billing.
- **Desktop app**: Electron shell + native agent over newline-delimited JSON on stdio. Per-click screenshots stream to `/api/upload/{id}/upload-url|image` while recording. On stop, a localhost express server hands the folder to `app…/upload/{id}/desktop/{payload}`, and the **browser** runs the step builder. Auth is a device-style browser flow polling `/api/auth/desktop/{authId}`; the token goes into `safeStorage`. Mac click Y is flipped (bottom-left origin).
- **AI-video extension**: "Smart Zoom and Cursor" records CDP `Page.startScreencast` frames into a canvas, so the real cursor is not in the pixels. It keeps pointer samples and bakes zoom (1.6×, spring-followed, click-grouped) and a drawn cursor into an in-browser MP4 (≤50 MiB).
- **Signed-in reality (observed-network)**: almost all reads are Firestore realtime listeners (flows, user, workspace, team, members, translations, aiCredits, brand kits). REST is used for writes (`POST /api/flows` → `{id}`, `PATCH {set{steps whole}, unset}` → `{modified}`, `set-status` 2 = publish) and jobs (`translations/generate` 202 → listener on `flows/{id}/translations`). Image upload goes straight to Firebase Storage plus a client Firestore write of `images/{id}`. The Free plan is `freePlanType:"singleFlow"` with 250 AI credits. Metered features (image editor, pan-zoom, translations) show a paywall with "continue", and the client increments `users.meteringUsage`.
- **Gating**: per-workspace feature map (109 named flags) + metering counters (`meteringUsage.<key>`) for panAndZoom, forms, translations, imageEditor, branching, trimVideo, menu, watermark, exports, collections, customLinks…; plans Free / Growth / Enterprise.

## Evidence gaps (be careful)

- Signed-in HARs cover create/edit/publish/translate, settings, billing and brand kits. Still unobserved: insights responses (the Free/no-views insights pages render sample data client-side with no request), the export job lifecycle (dialog opened, no export started), `/api/ai/*`, leads, custom links, and collections (paywalled on Free).
- HAR exports strip `Authorization`/`Cookie`, so the REST auth header is decompiled, not observed.
- Server-side logic (AI prompts, step building in `demo-end`, export renderer) is inferred; the client-side step builder is exact and is the reference.
- Player layout details (stage sizing, tooltip placement, mobile layouts) are partly inferred.
- Desktop native agent (Swift) not decompiled: no macOS/Ghidra/IDA on the box. Exact `metadata.json`/event JSON encodings come from the web decoder, and the CapsLock "toggle capture" effect is unknown. Windows build not found.
- Pass-1 "181/235 functions" was REA view items, not functions. In pass 2 each Wakaru entry (background, recording-manager, popup, page-editor) was fully parsed by REA, but semantic coverage stays "partial" (dynamic calls/properties), as REA reports for any bundle.
- AI-video server side (producer prompts, analysis, wizard) is out of reach by design.

## Unfinished / suggested next work

See ARCADE_RE_PLAN.md "Next passes". For implementation, start with the model + player
against fixture flows, then the MV3 extension + step builder (pure function, unit tests).

## Where the raw material is

On the REA box: `/workspace/arcade-rea-research/` (`raw/`, `recovered/`, helper txt/json
files). Never commit it. Hashes in docs/evidence-index.md.
