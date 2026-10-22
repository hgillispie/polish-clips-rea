# Recording session (service worker)

Evidence: **decompiled** (extension background bundle) unless tagged.

## Modes

| Mode | Output | Notes |
| --- | --- | --- |
| `Image` (popup "Screenshot", Ctrl+Shift+Y) | One PNG + optional HTML snapshot | Opens the app `/upload/flow` with payload type `screenshot`. |
| `Video` (popup "Record video") | Screen recording of the tab (tab audio + optional mic, optional camera) | Becomes a single Video step. |
| `Demo` (popup "Record with Avery", main shortcut) | Per-click screenshots + click metadata + continuous tab video (+ optional per-click HTML) | The interactive-demo path. Video is used only for "interesting" segments. |

## State machine

```
idle ──start(mode)──► countdown(3s) ──► recording ◄──► paused
  ▲                       │                │
  │                   cancel             stop / main shortcut / toolbar
  │                       ▼                ▼
  └──────────── canceled ◄── cancel_requested      finalize → idle
```

Badge text shows the number of captured clicks while recording.

## startDemo(tab)

```
startDemo(tab):
  focus tab; sessionId = uuid()
  settings = storage.get(userSettings)            # see arcade-analysis/extension.md
  flowId = null
  if storage.mayUseDirectUpload:
      flowId = POST /api/extension/demo-start {
          chromeExtensionVersion: "extension/<ver>",
          name: tab.url or tab.title,
          useAI: settings.useAvery,
          uploadInChunks: settings.uploadInChunks } .id
  showCountdown(tab, seconds=3, hints=[shortcuts], selectiveClickCapture, waitForDismount)
  status = recording
  broadcast to all frames: AddEventListeners          # content scripts start listening
  record tab geometry: tabScreenX/Y, tabWidth/Height (innerWidth/innerHeight)
  startScreenshotLoop(tab)                            # screenshot-loop.md
  startVideo(tab, mode=Demo)                          # video-recording.md
```

## stopDemo()

```
stopDemo():
  status = idle; broadcast RemoveEventListeners
  final = { screenshot: captureVisibleTab(), pageContext, links (if autoLink),
            html (if captureHTML) }            # becomes the last step, no hotspot
  { videoBlobUrl, videoTimestampWindows } = await offscreen.stop()
  events = mergeAndCorrect(capturedEvents)      # click-and-event-capture.md
  if flowId: uploadAndFinalize(...) else: openFallbackUpload(...)   # upload-and-finalize.md
```

## pause / resume / cancel

- Pause stops the screenshot loop and pauses MediaRecorder; resume restarts both. The offscreen doc keeps `videoTimestampWindows = [[startMs,endMs], …]` (wall-clock windows that were actually recorded). All later time math maps event wall-clock times into "recording time" through these windows.
- Cancel: stop everything, discard; if a flowId exists, `POST /api/extension/demo-status {id, status:"deleted"}`. On fatal errors the same call with `status:"error", description`.
- The content script pings `arcade-keep-service-worker-alive` so the MV3 worker is not suspended mid-recording.

## Gating (decompiled + static-help)

- `mayNotRecord` (server flag in storage) blocks recording (plan / account state).
- Free plan can record unlimited but publish 1 demo (static-help). HTML capture is Enterprise-only (static-help); the extension simply honours `captureHTML`.
