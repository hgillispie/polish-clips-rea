# Capture pipeline specs

| File | Covers |
| --- | --- |
| [recording-session.md](recording-session.md) | Modes (Screenshot / Video / Demo), state machine, start/stop/pause/cancel, countdown, badge. |
| [click-and-event-capture.md](click-and-event-capture.md) | Content-script listeners, click context, CSS selector, frame geometry, interesting events, typo correction. |
| [hotspot-coordinates.md](hotspot-coordinates.md) | Normalized click position across iframes and devicePixelRatio. |
| [screenshot-loop.md](screenshot-loop.md) | 500 ms captureVisibleTab ring buffer and click→screenshot matching. |
| [video-recording.md](video-recording.md) | tabCapture → offscreen MediaRecorder → ffmpeg remux; pause windows. |
| [html-capture.md](html-capture.md) | Cleaned DOM snapshot per click, iframes, scroll and form state. |
| [upload-and-finalize.md](upload-and-finalize.md) | Direct-upload API sequence and the fallback upload page. |
| [step-builder.md](step-builder.md) | Captured events → steps (Image + inserted Video clips), final step. |
| [desktop-capture.md](desktop-capture.md) | Desktop app capture format → steps (web side only). |
