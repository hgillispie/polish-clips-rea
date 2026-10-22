# Video recording (tab capture)

Evidence: **decompiled** (background + offscreen bundles).

```
startVideo(tab, mode):
  streamId = chrome.tabCapture.getMediaStreamId({targetTabId: tab.id})
  ensureOffscreenDocument(reasons: USER_MEDIA)
  offscreen.start({streamId, tabWidth, tabHeight, mic, camera, mode})

offscreen.start:
  video = getUserMedia({ video: { mandatory: { chromeMediaSource:"tab", chromeMediaSourceId: streamId,
              minWidth/maxWidth = 2*tabWidth, minHeight/maxHeight = 2*tabHeight, maxFrameRate: 30 }},
                         audio: mode != Demo ? tab audio : none })
  if mic: mix mic (+ tab audio) through an AudioContext destination
  rec = MediaRecorder(stream, { mimeType:"video/webm; codecs=vp9",
                                audioBitsPerSecond: hasAudio ? default : 0 })
  rec.start(100)                       # 100 ms chunks
  windows = [[now, null]]
  pause → rec.pause(); close window   resume → rec.resume(); open window

offscreen.stop:
  blob = concat(chunks)
  # remux so the WebM has duration/cues and sane timestamps + bt709 tags
  ffmpeg.wasm: -i in.webm -c copy -avoid_negative_ts 1
               -color_primaries bt709 -color_trc bt709 -colorspace bt709 out.webm
  if saveLocally: IndexedDB.put(out)
  return { data: URL.createObjectURL(out), videoTimestampWindows: windows }
```

Notes:
- Capture at 2× CSS size so the video is sharp on retina.
- Tab audio is **not** recorded in Demo mode (only mic, if enabled).
- Video upload: `POST /api/extension/upload-url {flowId, type:"video", resumable}` → PUT; then `POST /api/mux/create-asset {source:"extension-record-demo", sourceUrl, uploadId: flowId, flowId, stepId}` to transcode to HLS.
- Resumable chunked upload when `uploadInChunks`; treat as stuck after 3 consecutive chunks that do not advance the server offset.
