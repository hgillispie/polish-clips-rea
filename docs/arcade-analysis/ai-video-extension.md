# AI-video recorder extension ("Arcade AI Video Generator and Screen Recorder")

Evidence: **decompiled** (Wakaru per script + reading; CRX-VIDEO in evidence-index.md).
Pass 2. It belongs to the AI-video ("Producer") product, but it reuses the capture
extension's upload path, so it shows how recordings flow into Arcade's AI pipeline.
Everything here is our own description; no code was copied.

## Manifest (v1.0.26)

- MV3 service worker. Pages: `sidepanel.html` (main UI), `producer-recorder.html`
  (recorder page), `camera-bubble.html` (web-accessible, injected), settings,
  producer-media-permissions.
- Permissions: `storage, activeTab, tabs, scripting, unlimitedStorage, sidePanel,
  offscreen, debugger`; optional `cookies`; host `<all_urls>`.
- Command `stop-producer-recording`: Ctrl+Shift+E (mac Cmd+Shift+E), "stop and open Producer".
- `externally_connectable`: `arcade.software`, `app.arcade.software`, `*.arcade.software`.
- No static content scripts. `cursor-tracker.js` is registered at runtime, only while a
  recording is active.

## Components

| Part | Role |
| --- | --- |
| background (SW) | Opens the side panel, holds recording state in `chrome.storage.session` (`producerRecordingState`), routes `Producer*` messages, owns the CDP session for "Smart Zoom and Cursor", injects the camera bubble. It also bundles the older tabCapture recorder shared with the capture extension. |
| sidepanel | Chat-style "strategist" UI: reads pages, interviews the user, drafts a brief, manages recordings, starts the video wizard. |
| producer-recorder | Captures screen, camera and mic, keeps chunks in IndexedDB, and transcodes to MP4 in the page with smart zoom + cursor baked in. |
| cursor-tracker | Content script. Sends pointer samples to background. |
| camera-bubble | Draggable camera preview on the recorded page. |

Message vocabulary (runtime messages): `ProducerOpenPanel, ProducerClosePanel,
ProducerPrepareRecording, ProducerRecorderReady, ProducerMediaPermissionAnswered,
ProducerBeginRecording, ProducerStopRecording, ProducerCancelRecording,
ProducerRecordingState, ProducerTakeRecording, ProducerRecordingConsumed`.

## Recording state machine

```
idle → Prepare (open recorder page, ask camera/mic permission in a helper page)
     → RecorderReady → Begin (countdown, start MediaRecorder + optional cursor session)
     → recording ⇄ (Stop | Cancel | tab closed | debugger detached)
     → finalizing (transcode, size check) → ready (stored in IndexedDB)
     → Take (sidepanel pulls the recording) → Consumed (IDB entry deleted)
```
State is mirrored into `chrome.storage.session`, so a restarted service worker can
resume it. Stop comes from the keyboard command, the panel or the bubble.

## Capture pipeline

1. **Screen source**
   - Default: `getDisplayMedia` restricted to browser tabs, with self-tab, surface
     switching, system audio and monitor surfaces excluded, at a capped frame rate
     (max 30).
   - With **Smart Zoom and Cursor** on (`settings.cursorAndZooms`, http(s) tab only), the
     recorder skips display capture:
     - Background attaches `chrome.debugger` (protocol 1.3) to the tab.
     - It takes a PNG `Page.captureScreenshot` first frame, then runs
       `Page.startScreencast` (PNG, ≤3840×2160, every frame) and acks each frame.
     - The recorder page decodes each frame into a canvas (scaled to fit 3840×2160) and
       records `canvas.captureStream(30)`, redrawing at 30 fps.
   - So the browser's own cursor is never in the pixels; the cursor is drawn at export.
2. **Cursor samples**: the content script posts `{t, type, x, y, width, height, buttons,
   visible}`. `x, y` are 0..1 of the viewport, `t` is epoch ms from
   `performance.timeOrigin + now()`, and type is move, pointerdown, pointerup or
   navigation. Background forwards only top-frame samples whose token matches. The
   recorder rebases `t` to recording start and caps the list at 30,000 samples.
3. **Camera + mic**: separate `getUserMedia` streams. The camera is recorded as its own
   track/file with a `cameraOffsetMs`. If the browser cannot encode the mic as AAC
   (192 kbps), recording refuses to start.
4. **MediaRecorder**: WebM (VP9) with 1 s timeslices, stored in IndexedDB
   `arcade-producer-recordings` v1.
5. **Transcode to MP4 in the browser** (Mediabunny conversion: WebM in → MP4 out, AVC +
   AAC, fast-start in memory). The bitrate budget keeps screen + camera under **50 MiB**
   with 5 MiB headroom:
   `bitrate = clamp(8·(50MiB − camera − 5MiB)/seconds − 192k, 250k, 24M)`. Without zoom,
   the default is 2.5 Mbps (×0.6 in one mode). If it is still too big, it fails with "The
   enhanced recording is too large". On failure, the original WebM is offered for
   download.
6. **Smart zoom + cursor render** (runs per decoded frame during transcode):
   - Sample the cursor track at 120 Hz.
   - Group clicks into zoom segments. A segment starts 750 ms before a click and ends
     2.4 s after the last click; clicks less than 3.15 s apart merge.
   - Zoom eases in to 1.6× and eases out about 1.4 s after the last click.
   - The zoom centre follows the cursor with a damped spring and is clamped to
     0.3125..0.6875 of the frame.
   - The cursor sprite is drawn at its position in the zoomed frame, sized to the frame
     width. It gets a small tilt from the movement direction (spring, ±30°), a brief
     scale "pulse" on click (0.78..1.12) and a short overshoot nudge after quick moves.
   - Clicks with jitter (>4 px between down and up, or up >200 ms later) do not count as
     clean clicks for the nudge.

   Output: one MP4 that already contains the zooms. There is no separate zoom data for an
   editor.
7. Result object: `{id, settings, screen: File|null, camera: File|null, cameraRequested,
   microphone: bool, cameraOffsetMs, durationMs, audioSource: "none"|…, exportError?}`.

## AI pipeline (sidepanel → server)

```
read page(s)  ── DOM text/images/links (Google Docs via export), video pages → /api/producer/read-video
      │          extra tabs → /api/producer/classify-page {pages, candidate} → {relationship, options}
      ▼
interview     ── /api/producer/chat {messages, pages, recordings?, answers?, brief?, flags}
      │          → {reply, options, questions, amendsBrief, settles, readyToWrite, asksVisuals}
      ▼
record (opt.) ── recording above → upload (demo-start / upload-url / PUT / mux create-asset)
      │          → /api/producer/analyze-recording {recording, pages, preference, conversation, otherRecordings}
      │          → analysis {recommendation (layouts), uses}; user confirms a use/layout
      ▼
brief         ── /api/producer/draft {pages, recordings?, answers?, conversation}
      │          → {topic, audience, objective, format, keyMessage, tone, narrativeArc,
      │             mustHitMoments[], keyFacts[], recommendedLength}
      ▼
generate      ── targetLength = smallest of 15/30/45/60/90/120 s ≥ (video mode: longest recording + 6 s;
                 otherwise max(longest recording, brief.recommendedLength)), else 120 s
                 /api/wizard/prompt-video/session {action:"start", prompt (brief rendered as text ≤20k),
                   brandKitId, targetLength, aspectRatio:"16:9", attachments, extensionVideoContext?
                   {source:"chrome-extension", version:1, recordings}} → {sessionId}
                 → opens the web wizard for that session (Firestore `wizardSessions/{id}`; observed-network)
```
- Limits: ≤ 20 video tracks per video. Conversation text is trimmed from the oldest turn
  until it fits 50,000 chars. Answers are capped at 2,000 chars each.
- `/api/producer/capabilities` gates the newer request fields (`extensionVideoContext`,
  `recordingLayouts`, `followUpsAfterInterview`, `templateMediaRecording`). For
  compatibility, chat retries without the new flags on HTTP 400.
- Attachments: page images → `/api/producer/upload-image` (re-encoded to JPEG if too big);
  documents → `/api/producer/upload-file`.
- Auth: cookie (`credentials:"include"`) and `/api/extension-cookie-login`.

## What it means for our build

Only two parts matter for the interactive-demo builder:
- **CDP screencast + cursor samples + zoom-at-render**: a capture design that keeps the
  real cursor out of the pixels and keeps zoom procedural. We can use the same idea for
  Video steps: store cursor samples next to the video and render zoom and cursor in the
  player instead of baking them in.
- The **upload path** is the same `/api/extension/*` + Mux flow as the capture extension.

The chat/brief/wizard flow is AI-video product scope.
