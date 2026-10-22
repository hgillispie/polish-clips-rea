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
| popup | Record (Demo), Record video, Screenshot, camera/mic/tab-audio pickers, window size, AI toggle, embed diagnostics. See "Popup logic" below (decompiled, pass 2). |
| page-editor | In-page editing of the live page before capture. See "Page editor logic" below (decompiled, pass 2). |
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

## Popup logic (decompiled, pass 2)

```
on open:
  read chrome.storage.local {user, plan, loggedInAs, mayUsePageEditor, mayUseDomCapture,
       mayUseAutoLink, mayUseDirectUpload, mayUseTypoCorrection, mayNotRecord}
  loginStatus: unknown → (stored user) logged_in
             | (host permission for the app origin missing) insufficient_permissions
             | POST /api/extension-cookie-login {chromeExtensionVersion} (same-origin cookie)
                  → {user,…}: logged_in, send SetUser to background, persist user
             | else logged_out ("Log in to record")
  a different user id from the app replaces the stored user
  isPageRestricted = URL not http(s) or Chrome Web Store → record buttons disabled,
                     "Recording is not available on this page"
  mayNotRecord → Record disabled, "You do not have permission to record…"
buttons → message background {name: StartRecordingDemo | StartRecordingVideo | TakeScreenshot, tabId}
          then window.close()
devices: enumerateDevices → camera list, microphone list (labels without "(…)" suffix);
         camera/mic permission is asked in a helper page (CameraStatusResponse,
         MicrophonePermissionGranted); tab audio toggle is stored as tabAudioEnabled
settings toggles write user settings (useAvery, captureHTML, tone, …; table below)
window size: shows the current window width against a chosen preset (system.display)
embed diagnostics: ReloadAndScanForEmbeds → list of issues {type, severity: error|warning, …}
```

## Page editor logic (decompiled, pass 2)

- Started by the "edit page" command or popup. It mounts a shadow-DOM panel and an
  overlay, and turns off page spellcheck while editing.
- **Modes**: `edit` (text) | `replace` | `remove` | `hide` | image replace (click an
  `<img>`, choose a file; it is read as a data URL).
- **Text editing**: each edited text node is wrapped in a custom element
  `<arcade-editable data-edit-id data-initial-value>` and made contentEditable.
  If the live text no longer matches the recorded `previousContent`, the edit records
  `actualPreviousContent`.
- **Edit record**: `{id (random base36), createdAt ISO, pageUrl, type: replace|remove|hide|image|<text>,
  cssPath, childNodeIndex, previousContent, newContent}`. `cssPath` is `//*[@id="…"]`
  when the element has an id, otherwise a positional path. Paths starting with `/` are
  resolved with XPath, the rest with `querySelector`.
- **Persistence**: `localStorage["arcade-page-editor-edits"]` per origin, plus an
  `arcade-page-editor-state` key. A `MutationObserver` re-applies the edits for the
  current URL when nodes are added or the SPA route changes, so edits survive
  re-renders during capture.
- **Undo/redo**: Cmd/Ctrl+Z and Shift+Cmd/Ctrl+Z; each edit has an inverse.
- **Frame protocol** (`window.postMessage`, used when the page is inside the Arcade
  HTML editor iframe): `ArcadeRequestHtml` → `ArcadeResponseHtml {html: doctype +
  outerHTML with form values baked into attributes, edits}`, `ArcadeChangeEditMode {mode}`,
  `ArcadeRegisteredChange {edits}`, `ArcadeUndoEdit/RedoEdit`, `ArcadeUndo/RedoShortcutEdit`,
  `ArcadeHtmlResetScroll`, `ArcadeInitHtmlReplaceMessage {html, cssPath, childNodeIndex, pageUrl}`,
  `ArcadeRequestHtmlFromIframe` / `ArcadeSendHtmlFromIframe`.
- Inside the Arcade-hosted HTML capture page (`*.html` with `arcade-html`), storage is
  disabled and edits go only to the parent editor. On a live page, the background
  message `arcade-save-html-edits` triggers save.

## Second extension (AI video recorder)

Analysed in pass 2: [ai-video-extension.md](ai-video-extension.md).
