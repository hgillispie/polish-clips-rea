# Screenshot loop

Evidence: **decompiled**.

Why: `captureVisibleTab` is slow (~100 ms+) and a click often navigates, so
capturing *after* the click would show the wrong page. Arcade captures
continuously and picks the frame from just before the click.

```
startScreenshotLoop(tab):
  ring = []                            # keep the 4 newest
  every 500 ms while status == recording and mode == Demo:
      png = chrome.tabs.captureVisibleTab(tab.windowId, {format:"png"})
      ring.push({dataUrl: png, capturedAtMs: now}); if ring.len > 4: ring.shift()

onClick(click):
  shot = latest in ring with capturedAtMs <= click.timeMs   (fallback: oldest)
  screenshots[click.clickId] = { dataUrl: shot.dataUrl }
  badge = count(clicks)
```

After capture each screenshot is analysed (server `/api/extension/image` or local
offscreen fallback): `blurhash` (4×4 components computed on a ≤64 px downscale),
`size {width,height}`, `aspectRatio = height/width`.

Our implementation note: rate-limit is Chrome's (about 2 captures/s per window),
so 500 ms is close to the ceiling. Consider capturing on `pointerdown` as well
(our idea, not Arcade's).
