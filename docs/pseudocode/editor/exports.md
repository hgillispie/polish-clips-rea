# Exports (GIF / MP4)

Evidence: **decompiled** (export request zod schema, export modal, metering transaction),
**static-bundle** (flags "Remotion Export", "RemotionLambda"), **static-help** (plan gate:
Growth "MP4 & GIF exports").

```
POST /api/flows/{id}/export {
  type: "gif" | "mp4",
  fps?: 15 | 24 | 30 | 60,
  sizeConstraint?: 480 | 640 | 800 | 1280 | 1920 | 3840,     # max dimension
  language?: string,                                          # translated export
  opts?: { disableHotspotCursor?: bool, includeCaptions?: bool }
} → { exportId }
```
- Export doc in collection `exports`: `{ status: suggesting|suggested|pending|generating|succeeded|failed, url, type, fps, sizeConstraint, … }`; the modal subscribes and downloads `arcade_export.<type>` via the proxy when succeeded.
- Rendering is server-side; flags point at Remotion (likely Remotion Lambda) rendering the
  player timeline: each step held for its read/voice time, animated cursor moving to the
  hotspot and clicking (unless `disableHotspotCursor`), video segments played, captions burned
  in if `includeCaptions`. (inferred)
- Metering: user doc `meteringUsage.exportToGIF|exportToVideo` incremented in a transaction;
  `meteringLimitHit.<key>` stamped when the limit is reached; usage is rolled back if the
  export fails (`meteringUsageRolledBackAt`). Plan-limit keys include `exportToGIF`, `exportToVideo`, `trimVideo`, `splitVideo`.
- Presets UI: by type the resolution list and fps list differ (`TYPE_RES`, `TYPE_FPS`).

Observed-network: opening the export dialog in the editor made **no** request, and no
export was started, so the job lifecycle is still decompiled-only. The flow doc carries
`gifUrl:""` and `videoUrl:""` placeholders. The only `exports` listener seen was
`promptVideoGenerations/{id}/exports` ordered by `requestedAt` (AI-video product). This
suggests demo exports also live in an `exports` subcollection of the parent doc
(inferred).

Our build: render with a headless browser driving our own player in "export mode"
(deterministic clock) + ffmpeg (palettegen/paletteuse for GIF), or Remotion.
