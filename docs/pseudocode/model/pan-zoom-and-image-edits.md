# Pan-and-zoom, blur, crop

Evidence: **decompiled** (player zoom hook, image-editor update call, step helpers).

## Image step pan-and-zoom

```
panAndZoom { enabled, zoomLevel (default 1.5), position: {x,y} (0..1 or px) | {left,top} (fractions) }
```
Step builder auto-enables it when consecutive clicks stay on the same URL and the
`autoPanAndZoom` feature is on; the editor centres it on the hotspot.

Zoom box computation (player):
```
zoomIn(container W×H, zoomLevel z, position):
  vw = W / z; vh = H / z                      # visible window
  if position has x,y:
     cx = x <= 1 ? x*W : x;  cy = y <= 1 ? y*H : y
     dx = (cx - vw/2) * z;   dy = (cy - vh/2) * z
     clamp so the window stays inside the image (right/bottom overflow corrected), then max(0, …)
     box = { left: -dx, top: -dy, width: vw, height: vh, z }
  else (left/top fractions): box = { left: left*W, top: top*H, width: vw, height: vh, z }
render: transform = translate3d(left px, top px, 0) scale(z), origin 0 0
easing presets (cubic-bezier 0.4,0,0.2,1):
  Gentle  duration = min(0.8*z, 2) / playbackRate
  Quick   duration = min(0.4*z, 1) / playbackRate
  (third) duration = min(1.5*z, 3) / playbackRate
zoomOut → box = full container, z = 1
```
Hotspot dots counter-scale by 1/z. Plan-limit key `panAndZoom`.

## Video step zooms

`videoPanAndZooms[]: { enabled, position, zoomLevel, startTimeFrac, endTimeFrac }` —
same transform, active while playback time is inside the window.

## Blur (redaction) and crop

```
imageEditorState { redaction: Rect[] (blur boxes; BlurLevel small|medium|large), crop: {x,y,width,height} }
```
Edits are applied to `originalImageUrl`, the result uploaded as a new image, then:
`POST /api/flows/{id}/update-step { stepId, action:"updateEditedImage", url, blurhash, size, imageEditorState }`.
The editor offers to apply the same blur to other matching image steps; `POST /api/flows/blur-all`
exists for that (body not recovered). Metering: adding the first blur increments the
`imageEditor` usage counter; removing the last decrements it. "Blur Video" flag exists for videos.
