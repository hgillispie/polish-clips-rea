# Desktop app (macOS build 3.5.21)

Evidence: **decompiled** for the main process (Wakaru on `lib/main.js`, 63 modules)
and renderer bundles. REA `analyze_javascript_application` on the ASAR (evidence
REA-4 in [../evidence-index.md](../evidence-index.md)) confirms the structure.
The native helper `arcade-agent` is a Swift Mach-O. It could **not** be decompiled on
this Linux box (REA's native providers need macOS, Ghidra or IDA), so agent internals
are tagged **static-binary**: symbol, type and source-file names plus literal strings.
Nothing from the DMG/ASAR is committed.

## How it was obtained

- `https://www.arcade.software/desktop/download` redirects, without login, to a DMG at
  `cdn.arcade.software/desktop/dmg/<version>/Arcade.dmg`. Every user agent gets the mac
  build. (observed)
- `package.json` scripts reference Windows `msix`/`exe` packaging and
  `agent/windows/*.cpp`. No public Windows URL was found. (static-bundle)
- Extraction: 7z → `Arcade.app/Contents/Resources/app.asar` → `@electron/asar extract`
  → Wakaru `--unpack=auto` per bundle.

## Shape

| Piece | What it is |
| --- | --- |
| Shell | Electron, package `desktop`, bundle id `software.arcade.desktop`, macOS ≥ 12. Built universal with electron-forge; Squirrel auto-update. URL scheme `arcade://`. |
| Main process | One webpack bundle with Sentry release `arcade-desktop@<ver>`. Deps: express, electron-store, @napi-rs/canvas, blurhash, pngjs, promise-retry, Segment analytics-node, zod. |
| Renderer windows | `settings`, `onboarding`, `recording-selection`, `selection-overlay`, `device-instructions`, all served by `static/main.html`. Each window loads its bundle as the **preload** with `sandbox: false`. There is no contextBridge (REA: 0 context-bridge APIs). Renderers talk to main through `ipcMain` (REA-4: 53 main-process handlers on 43 literal channels, 6 BrowserWindows). |
| Native agent | `Resources/arcade-agent`, a universal (x86_64 + arm64) Swift CLI built with swift-argument-parser and ScreenCaptureKit / AVFoundation. On Windows: `arcade-agent-<arch>.exe` (C++). |
| Tray + menu | Tray items: Sign in / Sign out / Record / Open / Quit. Application menu. |
| Store | electron-store named `config` (`config.dev` on localhost, `config.<host-slug>` on other hosts). Keys: `token` (encrypted with `safeStorage`, base64), `userId`, `email`, `mayNotRecord`, `averyAiEnabled`, `useCase`, `language`, shortcut overrides, `enableDevTools`, add-step context. |

`FLOW_BUILDER_URL` comes from the env var, else `https://app.arcade.software` when
packaged, else `http://localhost:3000`. An optional `VERCEL_PROTECTION_BYPASS` env
adds the Vercel bypass query/header for preview deployments. (decompiled)

## Auth (device-style browser sign-in, decompiled)

```
signIn():
  deliveryId = randomUUID()                         # per sign-in attempt
  { authId } = POST {FLOW_BUILDER_URL}/api/auth/desktop
  openExternal({FLOW_BUILDER_URL}/auth/desktop/{authId})   # user approves in browser
  poll every 1 s for up to 5 min (DESKTOP_AUTH_EXPIRATION_MS = 300000):
     r = POST /api/auth/desktop/{authId}  { deliveryId }
     r.status: "authenticated" → persist {token, userId, email, mayNotRecord}; done
               "expired" → error 410
               "claimed-by-other-client" → error 409 (another deliveryId took it)
               else (pending) → keep polling
     give up after 5 consecutive request errors
checkToken():  GET /api/auth/check-token  (header authorization: <token>)
               ok → store mayNotRecord; not ok → clear stored auth
               result cached for 60 s
```

Every later API call sends `authorization: <token>`. That is a raw token, not
`Bearer`, the same convention the web app uses with Firebase ID tokens. The browser
page `/auth/desktop/[authId]` is the web side; it was documented in pass 1.

## Recording UX (decompiled)

- **Kinds**: `interactive` (an interactive demo: screenshots per click plus video)
  and `video` (plain screen video). The recording-selection window toggles between
  them. "Record with Avery" maps to `averyAiEnabled`, default on.
- **Targets** (`recordingMode`):
  - `area`: drag a rectangle on a full-screen selection overlay.
  - `screen`: the agent's `select-screen` subcommand.
  - `window`: the agent's `select-window [--ignore-pid]`; records only that window
    via `targetWindow`.
  - `device`: a USB-attached mobile device from `get-mobile-devices`; instructions say
    "Allow accessories to connect". iOS-via-AVFoundation is **inferred**.
- **Camera, microphone and system audio** are offered only for `video` and device
  recordings. For `interactive` they are forced off.
- **Shortcuts** (global):
  - `START_STOP` defaults to `Command+E` (`Control` on Windows).
  - `TOGGLE_CAPTURE` defaults to `CapsLock`. It is registered as a no-op in main;
    selective capture is presumably handled by the agent's key monitor (inferred).
  - `Escape` is bound only while a selection is active.
- **Start/stop**:
  - `startStop` opens the selection UI. If it is already open, it prepares; if a
    recording is in progress, it stops.
  - `prepare-recording` spawns the agent and waits for `ready`.
  - `record` sends `start`. Restart and cancel both send `stop {canceled: true}`.
- **Capture exclusion**: Arcade's own windows are protected and their CG window ids are
  passed as `excludeWindow`, so the UI never appears in the capture.
- **Coordinates**: on macOS the selected area is flipped to a bottom-left origin
  (`y = display.height − y − h`) before it is sent to the agent. Negative x/y are
  clamped to 0, shrinking the size to match. On Windows, `displayBounds` and a DIP→
  screen `displayLookupPoint` (the display centre) are sent as well.
- **Deep link** `arcade://…?sourceFlowId=&insertIndex=` stores an "add step" context.
  The next upload inserts the recording into that existing flow at that index.
- **Gate**: if `mayNotRecord` (server flag) is set, every record entry point is a no-op.

## Agent protocol (decompiled from the main-process client)

Spawned as `arcade-agent interactive` with env `ARCADE_USER_ID`. Messages are
newline-delimited JSON on stdin/stdout, and every message has a `type`.

| Direction | Message | Fields |
| --- | --- | --- |
| agent → app | `ready` | — |
| app → agent / reply | `ping` / `pong` | heartbeat every 60 s; no pong in 30 s → kill and respawn |
| app → agent | `get-devices` | → cameras, microphones |
| app → agent | `get-mobile-devices` | → attached devices |
| app → agent | `record-screen` | `outputPath` (temp dir `arcade-*`), `displayId`, `recordKind`, `area{x,y,width,height}`, `displayBounds?`, `displayLookupPoint?`, `camera?`, `microphone?`, `systemAudio?`, `excludeWindow[]`, `targetWindow?` |
| app → agent | `record-device` | `outputPath`, `deviceId`, `recordKind`, `camera?`, `microphone?`, `systemAudio?` |
| app → agent | `start` | — |
| agent → app | `start` | recording began |
| agent → app | `screenshot` | `{name, x, y}`: one PNG per click (interactive only) |
| agent → app | `error` | `{error}` |
| app → agent | `stop` | `{canceled}` |
| agent → app | `finish` | files are flushed |

- Prepare timeout: 20 s.
- Spawn retries back off `min(5000·2^(n−1), 60000)` ms, up to 10 attempts.
- After `finish`, `video.mov` (mac) or `video.mp4` (win) must exist with size > 0.

One-shot subcommands:

| Subcommand | Result |
| --- | --- |
| `perms check` | `{capture, a11y}` |
| `perms request-capture` / `perms request-a11y` | asks for the permission |
| `select-window [--ignore-pid]` | the picked window |
| `select-screen` | the picked screen |
| `get-app-icon <pid>` | the app's icon |

Accessibility permission is needed for the global input monitor that writes the event
JSON files. (decompiled call sites + static-binary names)

Agent internals (static-binary):

| Part | Names seen |
| --- | --- |
| Source files | `InteractiveCommand`, `RecordScreenCommand`, `RecordDeviceCommand`, `ScreenRecorder(Manager)`, `ScreenCaptureKitScreenRecorder`, `CameraRecorder(Manager)`, `AudioRecorder`, `DeviceRecorderManager`, `ActivityRecorder`, `CursorIdentifier`, `RecordingDataDelegate`, `VideoColorProperties`, `FileWriter`, `LineIO`, `jsonInteractiveProtocol`, `jsonTypes` |
| Event types | `MouseClickEvent`, `MouseMoveEvent`, `MouseDragEvent`, `KeystrokeEvent`, `ScrollWheelEvent` (+ `ScrollWheelPhase`), `CursorProps` |
| Metadata types | `ScreenRecorderMeta`, `ScreenMeta`, `DeviceRecorderMeta`, `RecordArea` |

Screenshots are taken through `SCScreenshotManager`, with a legacy display-screenshot
fallback, and written as PNG. Video is written with `AVAssetWriter` from an
`SCStream`. Input comes from `NSEvent` global monitors. The agent exits after
5 minutes with no activity and no recording.

## Output folder (one recording)

| File | interactive | video | device |
| --- | --- | --- | --- |
| `metadata.json` | ✓ | ✓ | ✓ |
| `mouseclicks.json`, `mousemoves.json`, `mousedrags.json` | ✓ | ✓ | — |
| `keystrokes.json`, `scrollwheel.json` | ✓ | — | — |
| `video.mov` / `video.mp4` | ✓ | ✓ | ✓ |
| `camera.mov` / `camera.mp4` | if camera | if camera | if camera |
| `<name>.png` per click | ✓ | — | — |

- `metadata.json` is written by the **agent**. The app reads these fields from it:
  - `startUptime` and `endUptime`: seconds of system uptime. Their difference is the
    duration, and a recording under 500 ms counts as cancelled.
  - `hasCamera`: checked against what the app requested.

  The web builder also reads `recordArea`, `cameraStartUptime` and `hasAudio` (pass 1,
  decompiled web).
- The app keeps a separate in-memory `RecordingMetadata` and uses it for the upload
  asset list and coordinate maths:
  - screen recordings: `{recordArea, recordScreen, recordKind, hasCamera, platform, screens[{id,x,y,width,height,backingScaleFactor}]}`;
  - device recordings: `{deviceId, recordKind, hasCamera}`.

  `hasCamera` is true only for `video` kind with a camera selected.
- Event JSON shapes are given in [../pseudocode/capture/desktop-capture.md](../pseudocode/capture/desktop-capture.md).

## Upload and handoff (decompiled)

The full sequence is in [../pseudocode/capture/desktop-capture.md](../pseudocode/capture/desktop-capture.md).
In short:

1. **Init.** The app generates the `uploadId` itself (a 20-char Firestore-style auto id
   that later becomes the flow id). It registers it with `POST /api/upload/init
   {uploadId, createdWith, useAI, assets{file:{size, contentType}}, sourceFlowId?, insertIndex?}`,
   which returns `{assets{file:{url, publicUrl}}}` signed PUT URLs for the fixed assets.
2. **Screenshots** stream up during recording:
   - `POST /api/upload/{id}/upload-url` to get a signed URL, then PUT the PNG;
   - `POST /api/upload/{id}/image` with click coordinates normalized by the
     `desktopEventPositionToCoords` formula.
3. **Local server.** On stop, the app starts an express server on `127.0.0.1:<random>`
   that serves the temp folder. CORS is limited to `FLOW_BUILDER_URL`, plus
   `Access-Control-Allow-Private-Network: true`.
4. **Browser handoff.** The app opens
   `{FLOW_BUILDER_URL}/upload/{uploadId}/desktop/{base64url(JSON{localServerUrl, uploadId, sourceFlowId?, insertIndex?})}`.
   The web page pulls the JSON files and the video straight from localhost. It runs
   the step builder **in the browser** and fetches `/complete`, a 1×1 SVG, which
   closes the server; otherwise the server closes after 1 h.
5. **End.** `POST /api/upload/{id}/end {flowId, useCase, language, mode: recordKind, averyAiEnabled}`.
6. **Video.** The app PUTs `video.*` and `camera.*` to their signed URLs, then calls
   `POST /api/mux/create-asset` with `{source: "desktop-video-recording" | "desktop-camera-recording", ...}`.

Failed recordings are kept in a "recent recordings" store (Settings → History) and
can be retried under a new uploadId; screenshots are re-sent in batches of 5.

An interactive **device** recording opens `/flows/{id}/edit?action=video-to-arcade`
instead, so the server-side video→demo split takes over.

## Desktop vs Chrome extension

| | Desktop app | Capture extension |
| --- | --- | --- |
| Surface | Any app or screen, an area or window, or a USB mobile device | The active Chrome tab only |
| Click source | OS-level global mouse monitor in the native agent | DOM listeners in a content script (all frames) |
| Screenshot | Agent grabs the record area per click (ScreenCaptureKit) | 500 ms `captureVisibleTab` ring buffer; frame before the click |
| Element context | None (no DOM): no selector, text, or HTML capture | Selector, text, element rect, headings, optional cleaned HTML |
| Video | `.mov` (mac, AVAssetWriter; codec not recovered) / `.mp4` (win) | VP9 WebM via tabCapture + MediaRecorder, remuxed by ffmpeg.wasm |
| Camera / system audio | Separate `camera.*` file; system audio optional (video kind only) | Camera bubble via offscreen; tab audio |
| Typing / scroll / drag | `keystrokes.json`, `scrollwheel.json`, `mousedrags.json` (OS events) | `arcade-keypress/input/scroll/drag` events from the page |
| Coordinates | Screen points → record-area fraction; y flipped on mac | Client coords + frame offsets → tab-viewport fraction |
| API | `/api/upload/init`, `/{id}/upload-url`, `/{id}/image`, `/{id}/end` | `/api/extension/demo-start`, `upload-url`, `image`, `scrape`, `demo-end` |
| Step building | In the browser (`desktopCaptureToSteps`) from files served by the local server | Server-side on `demo-end` (web fallback uses the same builder) |
| Auth | Browser device flow → stored token (`authorization` header) | Session cookie (`/api/extension-cookie-login`) |
| Mobile | `record-device` | — |

## Not covered

- The Swift agent's exact JSON encodings for `metadata.json` and the event files.
  Field names come from the web decoder (pass 1), not the binary. Decompiling needs a
  thin-slice Mach-O plus Ghidra (Java) or Hopper/IDA, which are not installed here.
- Windows build and its C++ agent (no public download found).
- `com.arcade.desktop` native-messaging host: the capture extension asks it
  `{type:"getVersion"}`. No host manifest was found in the mac app bundle, so how it
  is installed is unknown.
