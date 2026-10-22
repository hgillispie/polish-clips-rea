# Desktop capture (producer + web builder)

Evidence: **decompiled**. The producer side comes from the desktop app 3.5.21 main
process (DESKTOP-ASAR, pass 2). The consumer side is the web module
`desktopCaptureToSteps` (pass 1). Native-agent internals come from strings/symbols only.
App architecture, auth and the agent protocol are in
[../../arcade-analysis/desktop-app.md](../../arcade-analysis/desktop-app.md).

## 1. Producer: one recording session

```
start(kind ∈ {interactive, video}, target ∈ {area, screen, window, device}, opts):
  require perms (agent `perms check`: screen, accessibility for input, camera/mic)
  if auth.mayNotRecord (from the sign-in response; pushed to the selection window) → UI blocks recording
  meta = { recordKind: kind, recordArea (points, top-left origin from the overlay),
           recordScreen: displayId, screens[{id,x,y,width,height,backingScaleFactor}],
           platform, hasCamera: kind == video && camera chosen }
  uploadId = client-generated 20-char id
  POST /api/upload/init {uploadId, createdWith: appVersion, useAI: averyAiEnabled (default true),
        assets{<file>: {size, contentType}} for metadata + event JSONs + video (+ camera),
        sourceFlowId?, insertIndex?}                     # add-steps-to-existing-flow context
     → {assets{<file>: {url (signed PUT), publicUrl}}}
  agent ← {type:"record-screen" | "record-device", outputDir, area, screen, camera?, mic?,
           systemAudio? (video kind only), interactive: kind == interactive}
  agent ← {type:"start"}
  for every agent message {type:"screenshot", name, x, y} (interactive only; queued until init returns):
      url = POST /api/upload/{uploadId}/upload-url {name} → PUT png
      POST /api/upload/{uploadId}/image {name, …desktopEventPositionToCoords({x,y}, meta)}
  on hotkey (default Command+E) / tray / overlay stop:
      agent ← {type:"stop"} … wait {type:"finish"}
      read outputDir/metadata.json; if endUptime − startUptime < 0.5 s → cancelled
      handoff(uploadId, outputDir, meta)
```
Shortcuts: `Command+E` start/stop (global). `CapsLock` is the default for "toggle capture",
but the main-process handler is a no-op, so its effect lives elsewhere (renderer or
agent; not recovered).

## 2. Output folder (written by the native agent)

```
metadata.json   { startUptime, endUptime (s, system uptime), recordArea{x,y,width,height},
                  cameraStartUptime?, hasAudio, hasCamera }
mouseclicks.json [{ type: leftMouseDown|leftMouseUp|rightMouseDown|rightMouseUp|otherMouseDown|…,
                    timestamp (uptime s), x, y (screen points) }]
mousemoves.json, mousedrags.json [{ type, timestamp, x, y }]
keystrokes.json  [{ type: keyDown|keyUp, timestamp }]          # interactive only
scrollwheel.json [{ timestamp, phase: began|changed|ended|… }] # interactive only
video.mov (mac) | video.mp4 (win); camera.mov|mp4 when a camera was used
screenshot-<timestamp with "." → "_">.png per click            # interactive only
```
The field names come from the web decoder and the app's readers, plus agent strings
(`MouseClickEvent`, `KeystrokeEvent`, `ScrollWheelEvent`). The Swift encoders were not
decompiled.

## 3. Coordinates

```
desktopEventPositionToCoords(evt, meta):
  screen = meta.screens.find(id == meta.recordScreen)   # throws if missing
  dx = evt.x − screen.x − meta.recordArea.x
  dy = evt.y − screen.y − meta.recordArea.y
  return { x: dx / recordArea.width,
           y: platform == "win32" ? dy / recordArea.height
                                  : 1 − dy / recordArea.height }   # mac events are bottom-left origin
```

## 4. Handoff to the browser

```
handoff(uploadId, dir, meta):
  server = express on 127.0.0.1:<random>, static dir, CORS = FLOW_BUILDER_URL,
           header Access-Control-Allow-Private-Network: true, GET /complete → 1×1 SVG + shutdown,
           auto-close after 1 h
  payload = base64url(JSON{localServerUrl, uploadId, sourceFlowId?, insertIndex?})
  open browser {FLOW_BUILDER_URL}/upload/{uploadId}/desktop/{payload}
  PUT video.* and camera.* to their signed URLs
  POST /api/mux/create-asset {source:"desktop-video-recording"|"desktop-camera-recording", uploadId, …}
  POST /api/upload/{uploadId}/end {flowId: uploadId, useCase, language, mode: recordKind, averyAiEnabled}
  device + interactive → open /flows/{id}/edit?action=video-to-arcade instead (server smart split)
  failure → keep in "recent recordings"; retry = new uploadId, screenshots re-sent 5 at a time
```

## 5. Consumer: web builder (`desktopCaptureToSteps`)

The web page loads the JSON files from the local server, with the screenshots mapped to
their uploaded URLs. Its builder differs from the extension one:

```
interesting(a, b):                    # seconds relative to start
  if videoUrl and b - a >= 3: true
  any keystroke in [a,b): true
  ≥3 mousedrags within 0.5 s of each other in [a,b): true
  a scroll gesture (began/changed) lasting ≥ 0.1 s in [a,b): true

for each mouse-down click at time b (≥0.5 s after last, ≥0.5 s before end, has screenshot):
   if b - last ≥ 0.5 and interesting(last, b): push Video step [last/D, b/D], muted
   push Image step (hotspot 40×40 pulsating at desktopEventPositionToCoords(click, metadata))
   last = b
tail: if interesting(last, D) or no steps: Video step to the end, with cameraRecording
      { url: cameraUrl, placement (default bottom-left), shape: circle, size: medium,
        offsetStartTimeFrac from cameraStartUptime }
aspect ratio = recordArea.height / recordArea.width
```

## Our build

Use the same split. A native helper produces a folder (events JSON + per-click PNG +
video), and the pure `buildSteps(capture)` function runs in the browser or worker for
both desktop and extension inputs. Normalise coordinates once at the producer
(top-left origin) so the builder never needs the platform flag.
