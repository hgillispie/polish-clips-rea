# Capture extension: manifest, scripts, messages, settings

Source: CRX for extension id `gagidkjllbdgggpboolfmmdpeagghjlm`, version 1.9.33
("Arcade: AI Interactive Product Demos"), fetched through the Chrome Web Store
update URL, unpacked and Wakaru-decompiled locally. Webpack bundles. Nothing from
the CRX is committed. Tag: **decompiled** unless noted.

## Manifest summary

| Key | Value |
| --- | --- |
| manifest_version | 3 |
| permissions | `storage`, `activeTab`, `tabCapture`, `tabs`, `system.display`, `offscreen`, `scripting`, `webNavigation`, `unlimitedStorage`, `webRequest` |
| optional_permissions | `cookies`, `nativeMessaging` |
| host_permissions | `<all_urls>` |
| externally_connectable | `*.arcade.software` (app ⇄ extension messaging) |
| content scripts | `recording-manager.js` on `<all_urls>`, `all_frames: true`; `link-expander.js` on Gmail / Outlook / Superhuman / GitHub (turns pasted demo links into previews) |
| commands | main action (Ctrl+Y / Cmd+E), take-screenshot (Ctrl+Shift+Y), cancel (Ctrl+J), pause-resume (Ctrl+H), resize-window, edit-page |
| bundled | `ffmpeg-core.wasm` (~32 MB) for remuxing the recording |
| pages | popup, settings, offscreen, page-editor ("edit page" / HTML editing), frame-wrapper, embed-diagnostics, camera helpers |

## Scripts and their jobs

| Script | Job |
| --- | --- |
| background (service worker) | Recording state machine, screenshot loop, tabCapture stream id, uploads, API calls, opening the editor tab, keyboard commands, badge counter. |
| recording-manager (content, all frames) | Event listeners, click context (selector, text, element type, headings, element rect), frame geometry, countdown overlay, HTML snapshot, keep-alive pings, relays recorded data to the app page. |
| offscreen | `getUserMedia` on the tab stream, mic mixing, `MediaRecorder`, ffmpeg remux, IndexedDB save, blurhash/aspect analysis of images, JSON→blob URL. |
| popup | Buttons "Record with Avery" (Demo), "Record video", "Screenshot"; camera picker ("No Camera"), "System Audio", "Change size" (window size), "Log in to record", "Recording is not available on this page", media-permission prompt, Settings link, embed-diagnostics report view. (static-bundle UI strings) |
| page-editor | In-page text editing of the live page before capture ("edit page" command): "Edit mode", per-element "Original text was …", "Edit History", Save/Cancel; edits saved via `arcade-save-html-edits`. (static-bundle UI strings + decompiled message name) |
| embed-diagnostics | Injected into a customer page to find why an embed is blocked (CSP `frame-src` etc.). |

## Message vocabularies (names are the protocol; values are strings)

- **Recording type**: `Image` (single screenshot), `Video` (screen recording only), `Demo` (interactive demo: screenshots per click + video).
- **Recording status**: `idle`, `countdown`, `recording`, `paused`, `cancel_requested`, `canceled`.
- **Content → background events**: `arcade-click-event`, `arcade-drag-event`, `arcade-scroll-event`, `arcade-keypress-event`, `arcade-input-event`, `arcade-frame-info-report`, `arcade-keep-service-worker-alive`, `arcade-show-recording-countdown`, `arcade-request-html`, `arcade-save-html-edits`, `arcade-scan-page-for-embeds`, …
- **Background → offscreen**: start/stop recording, analyse image (blurhash), JSON→URL, save screenshot.
- **Popup/commands → background**: TakeScreenshot, StartRecordingVideo, StartRecordingDemo, CreateArcade, RetryRecording, RunEmbedDiagnostics, ReloadAndScanForEmbeds.
- **App (external) → extension**: `GetVersion`, `GetDesktopVersion`, `UserFromApp`, `LastEditedFlow`, `OpenSettings`; the AI-video extension also answers `OpenVideoRecorder`, `GetVideoRecording`, `AcceptVideoRecording`, `ReadyForPreflight`.
- **App page ⇄ content script (window.postMessage)**: `arcade-request-recorded-data` → recorded payload chunks forwarded back.

## Default user settings (stored in `chrome.storage`)

| Setting | Default | Effect |
| --- | --- | --- |
| captureHTML | false | Also snapshot cleaned DOM per click (enterprise "HTML capture"). |
| useAvery | true | Ask server AI ("Avery") to write hotspot copy. |
| autoLink | false | Record visible link rects per click (for auto-linking hotspots). |
| embedArcadesInBrowser | true | Link expander feature. |
| replaceLinksWithPreviewInEmailComposer | false | Link expander in email composers. |
| recordInterestingEventsAsVideos | true | Insert video steps for scroll/typing/drag/long pauses. |
| saveLocally | true | Keep a copy of the recording in IndexedDB. |
| selectiveClickCapture | false | Clicks with CapsLock on are not captured. |
| uploadInChunks | false | Resumable chunked video upload. |
| tone | "promotional" | AI copy tone (promotional / educational / sales / custom). |
| waitForDismount | false | Countdown option. |
| default window size | height 768 | Used by "resize window" command. |

Server-controlled gates read from storage: `mayUseDirectUpload`,
`mayUseTypoCorrection`, `mayNotRecord`.

## Second extension (AI video recorder) — gap

Id `plbpmcliejllllhnalcbmggjkchokpbg`, v1.0.26. Uses `sidePanel` and `debugger`
permissions, has producer-recorder, camera-bubble and cursor-tracker scripts.
Unpacked and Wakaru'd locally but **not analysed**. It belongs to the AI-video
product, which is out of scope for the demo builder v1.
