# Upload and finalize

Evidence: **decompiled** (background API client + web upload page).

## HTTP client (extension)

axios-style client, `withCredentials: true` (session cookie on the app domain),
timeout 20 min, 3 retries with exponential backoff, no retry on 400/403.
Image uploads limited to 5 concurrent.

## Direct-upload path (flag `mayUseDirectUpload`)

```
finalizeDemo(flowId, capture):
  for each click (and "final"):
      {uploadUrl, contentType, publicUrl} = POST /api/extension/upload-url {flowId, type:"image", resumable:false}
      PUT uploadUrl (png)
      analysis = POST /api/extension/image {
          flowId, hasHTML, useAI: useAvery && clicks <= 50,
          assetId: clickId (or flowId for "final"), url: publicUrl,
          x, y, pageContext, rectContext }          → { blurhash, size, aspectRatio, … }
      on failure: analysis = offscreen.analyseImage(dataUrl)   # local blurhash
  if captureHTML: upload html pages; POST /api/extension/scrape {...}
  if needsVideo:
      upload video (upload-url type "video", resumable if uploadInChunks)
      POST /api/mux/create-asset {source:"extension-record-demo", sourceUrl: publicUrl,
                                  uploadId: flowId, flowId, stepId}
  POST /api/extension/demo-end {
      flowId, type:"demo", hasHTML, useAI, tone,
      videoBlobUrl: publicVideoUrl, tabs, capturedEvents,
      screenshots: { [clickId]: { dataUrl: publicUrl, blurhash, size } },
      pageContexts, clickContexts, links, capturedHTML: {},
      videoTimestampWindows, aspectRatio, captureFullVideo,
      recordInterestingEventsAsVideos, chromeExtensionVersion,
      uploadId, endedRecordingAt, endedAt }
  open tab  <app>/upload/<flowId>/flow       # editor shows processing, then the flow
```

The server is expected to run the same step builder as the web fallback
([step-builder.md](step-builder.md)) and, if `useAI`, write hotspot labels,
title and description (inferred from field names `hotspotLabels`, `processedAI`).

## Fallback path (no direct upload)

```
openFallbackUpload(capture):
  json = JSON.stringify(capture with dataUrls)
  chunks = split(json, 5 MB); each → offscreen JsonToUrl → blob URL; store list in session storage
  open <app>/upload/flow  (or /upload/media for a plain video)
  app page: window.postMessage({name:"arcade-request-recorded-data"})
  content script: RequestRecordedData → background → forward chunk blobs back (ForwardRecordingData)
  app page:
      flow = { ...defaults, createdWith: chromeExtensionVersion, aspectRatio,
               capturedEvents, steps: parseExtensionCapture(capture).steps,
               name: title of first clicked tab, uploadId }
      upload video + image blobs + HTML → URLs
      write flow doc; navigate to /flows/<id>/view
```

## Image mode

Single screenshot (+ HTML if enabled) → `/upload/flow` with payload
`{type:"screenshot", …}` → one Image step without hotspots.
