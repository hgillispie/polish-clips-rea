# Step builder: captured events → steps

Evidence: **decompiled** (web module exporting `parseExtensionCapture`,
`getRecordingDurationMs`, `getTimeSinceRecordingStartMs`). This is the heart of
"record once, get a click-through demo". Implement as a pure function with fixtures.

## Inputs

```
Capture {
  tabs: { [tabId]: { tabScreenX, tabScreenY, tabWidth, tabHeight, tabTitle,
                     frames: { [frameId]: { frameScreenX, frameScreenY, … } } }, final?: … }
  capturedEvents: (ClickEvent | Interesting)[]
  screenshots: { [clickId | "final"]: { dataUrl, blurhash, size } }
  pageContexts, clickContexts, links, capturedHTML, hotspotLabels?: { [clickId]: string }
  videoBlobUrl?, videoTimestampWindows: [startMs, endMs][]
  captureFullVideo?: bool, recordInterestingEventsAsVideos?: bool (default true)
}
theme: { textColor, backgroundColor }          # hotspot colours from team/theme
features: { autoPanAndZoom?: bool }
```

## Time helpers

```
recordingDuration(windows) = Σ (end - start)

toRecordingTime(t, windows):          # wall-clock → time inside the recorded video
  acc = 0
  for [s, e] in windows:
      if t < s: return acc            # NOTE: decompiled code returns s here; acc is what is meant
      if t <= e: return acc + (t - s)
      acc += e - s
  return acc
```

## Algorithm

```
build(capture):
  D = recordingDuration(windows)
  muted = no event of type media with audio
  sort events by (click ? timeMs : startTimeMs)
  steps = []; lastT = 0; pendingVideo = captureFullVideo
  minClip = captureFullVideo ? 1000 : 500
  allowVideo = recordInterestingEventsAsVideos != false
  prevUrl = null

  videoStep(endFrac, prevStep, prevEvent) = {
      id: uuid, type: Video, url: videoBlobUrl,
      startTimeFrac: lastT / D, endTimeFrac: endFrac,
      duration: D/1000, playbackRate: speedFor(prevEvent),
      videoProcessing: true, muted,
      videoThumbnailUrl: prevStep is Image ? prevStep.url : shimmer placeholder }

  speedFor(e) = e.type == scrolling ? 1 : e.type == typing ? 2.5 : 1.5

  for i, e in events:
    switch e.type:
      click:
        shot = screenshots[e.clickId]; tab = tabs[e.tabId]; frame = tab?.frames[e.frameId]
        if !shot or !tab or !frame: continue
        t = toRecordingTime(e.timeMs, windows)
        if videoBlobUrl and allowVideo and t - lastT >= 3000: pendingVideo = true   # long pause
        if pendingVideo and t - lastT >= minClip:
            steps.push(videoStep(t / D, last(steps), events[i-1]))
        page = pageContexts[e.clickId]; ctx = clickContexts[e.clickId]
        isCanvasDrag = ctx?.cssSelector contains "canvas" and events[i+1]?.type == dragging
        if not isCanvasDrag:                       # canvas drags are better as video only
            steps.push({
              id: e.clickId, type: Image, url: shot.dataUrl, originalImageUrl: shot.dataUrl,
              blurhash: shot.blurhash, size: shot.size, hasHTML: capturedHTML has e.clickId,
              hotspots: [{ id: uuid, width: 40, height: 40, style: "pulsating", defaultOpen: true,
                           label: hotspotLabels[e.clickId] ?? "", textColor, bgColor,
                           ...getClickPos(e, fixTab(tab, page), frame) }],
              panAndZoom: (features.autoPanAndZoom and page.url == prevUrl) ? {enabled:true} : absent,
              pageContext: page, clickContext: ctx })
        lastT = t; prevUrl = page?.url; pendingVideo = captureFullVideo
      media, typing:  pendingVideo = true
      scrolling:      if duration(e) >= 100 ms: pendingVideo = true
      dragging:       if duration(e) >= 50 ms:  pendingVideo = true

  if videoBlobUrl and allowVideo and D - lastT >= 3000: pendingVideo = true
  if pendingVideo and D - lastT >= minClip: steps.push(videoStep(1, last(steps), last(events)))

  if screenshots.final:
      steps.push({ id: uuid, type: Image, url: final.dataUrl, hotspots: [], hasHTML, size, blurhash,
                   pageContext: pageContexts.final })
  return { steps, imageHTML: map stepId → html }
```

Observations:
- **Every video step references the same uploaded recording**; it is a window
  `[startTimeFrac, endTimeFrac]` into it. Trimming = editing fracs. (decompiled)
- Video steps play the segment *leading up to* the next click, sped up 1.5× (2.5× for typing).
- The final "after" screenshot becomes a hotspot-less last step; the editor
  usually turns it into / follows it with a Final overlay (inferred).
- Default autoplay rules then decide whether video steps advance automatically
  (see [../player/runtime.md](../player/runtime.md)).
