# Desktop capture format (web side only)

Evidence: **decompiled** web module `desktopCaptureToSteps`; enums static-bundle.
The desktop app binary was **not** downloaded or analysed (gap).

```
DesktopCapture {
  metadata: { startUptime, endUptime (seconds), recordArea {x,y,width,height},
              cameraStartUptime?, hasAudio }
  mouseclicks: [{ type: "leftMouseDown" | "leftMouseUp" | "rightMouseDown" | …, timestamp, x, y }]
  keystrokes:  [{ timestamp, … }]
  mousedrags:  [{ timestamp, … }]
  scrollwheel: [{ timestamp, phase: "began" | "changed" | "ended" | … }]
  videoUrl, cameraUrl?, screenshotUrls: Map<"screenshot-<ts with . → _>", url>
}
event types: mouseMoved, left/right/otherMouseDown|Up|Dragged, scrollWheel, keyDown, keyUp
```

Builder differs from the extension one:

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
