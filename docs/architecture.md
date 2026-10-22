# Architecture (as recovered from Arcade, and as we will build it)

Evidence tags: **decompiled** (Wakaru module), **static-bundle** (raw JS string),
**observed** (public response), **static-help**, **inferred**.

## 1. Hosts and deployables

| Host / artifact | Role | Evidence |
| --- | --- | --- |
| `app.<domain>` | Editor + dashboard. Next.js pages router, Turbopack chunks under `/_next/static/immutable/chunks/`. ~180 routes in `_buildManifest.js` (`/flows/[pid]/edit`, `/flows/[pid]/insights`, `/upload/[id]/flow`, `/workspaces/[slug]/…`). Middleware proxies `/api/*`, `/cdn-proxy`, `/s3-proxy`, `/mux-proxy`, `/transform-proxy`. | static-bundle |
| `demo.<domain>` | Public share pages `/share/[pid]`, `/share/[pid]/[customLinkId]`, `/share/[pid]/guide`, `/share/[pid]/offline`. Page data at `/_next/data/<build>/share/<id>.json`. | observed |
| `demo.<domain>/embed/v1/loader.js` | Web-component loader. Fetches `/embed/v1/flows/<id>` payload, then imports a versioned standalone runtime (`rendererRevision`) with SRI. | observed |
| `cdn.<domain>` | Image/asset CDN with on-the-fly resize (`/cdn-cgi/image/fit=scale-down,format=auto,dpr=2,width=N/<path>`). | static-bundle |
| Video host (Mux) | HLS `stream.mux.com/<playbackId>.m3u8`, thumbnails `image.mux.com/<id>/thumbnail.webp?time=`, static MP4 renditions. | static-bundle, observed |
| Document DB (Firebase/Firestore) | Collections `flows` (+ subcollections `versions`, `mediaProcessingJobs`), plus users, teams, workspaces, exports, uploads, customLinks, flowsCollections, insights, comments, translations, voiceovers … Client reads with live listeners; writes mostly go through `/api/*`. | decompiled |
| Object storage | Signed PUT URLs issued by `/api/extension/upload-url` and `/api/upload*`. | decompiled |
| Analytics ingest | Segment-compatible endpoint on a first-party host (`t.<domain>/api/ingest`), PostHog-style `/ingest`. | static-bundle |
| Chrome extension "interactive demo" (MV3, v1.9.33) | Capture. See [arcade-analysis/extension.md](arcade-analysis/extension.md). | decompiled |
| Chrome extension "AI video" (v1.0.26) | Side-panel recorder with camera bubble and cursor tracker. Not analysed in depth. | static-bundle (manifest only) |
| Desktop app | Exists (native-messaging host `com.arcade.desktop`, `/desktop/download`, `/upload/desktop/[uploadInfo]`, macOS-style mouse/keyboard events). **Not downloaded.** Only its upload format is known from the web step builder. | static-bundle, decompiled (web side) |

Third parties seen: Sentry, Segment, PostHog, HubSpot, Liveblocks (comments),
ElevenLabs + Google TTS (synthetic voice), Clearbit (Audience Reveal),
Mux (video), Firebase Auth (ID tokens on `fetchWithToken`). (static-bundle)

## 2. End-to-end data flow

```
 ┌──────────── Chrome extension (MV3) ─────────────┐
 │ content script (all frames)                      │
 │   pointer/scroll/key/input listeners ──► events  │
 │   frame geometry reports                         │
 │   optional getCleanHTML snapshot                 │
 │ service worker                                   │
 │   captureVisibleTab every 500 ms (ring of 4)     │
 │   tabCapture stream id ──► offscreen document    │
 │ offscreen document                               │
 │   MediaRecorder(webm/vp9) + ffmpeg.wasm remux    │
 │   blurhash / JSON→blob URL helpers               │
 └───────────┬─────────────────────────────────────┘
             │ direct-upload path (flag mayUseDirectUpload)
             │   POST /api/extension/demo-start  → flowId
             │   POST /api/extension/upload-url  → signed PUT (image|video|html)
             │   POST /api/extension/image       → per-click analysis (blurhash, AI copy)
             │   POST /api/mux/create-asset
             │   POST /api/extension/demo-end    → server builds steps
             │ fallback path
             │   open app /upload/flow, page pulls payload via content-script postMessage,
             │   builds steps client-side (parseExtensionCapture), uploads, writes flow
             ▼
 ┌──────────────── Backend ────────────────┐
 │ flows/{id} document (Flow JSON)          │
 │ async jobs: AI hotspot text, smart split │
 │   (video→demo), translations, voiceover, │
 │   exports (GIF/MP4), video generation    │
 └───────────┬─────────────────────────────┘
             ▼
 ┌──────── Editor (app) ────────┐   ┌──────── Player (share / embed) ────────┐
 │ edits Flow via PATCH /api/flows│  │ public flow JSON → stage → steps        │
 │ live Firestore listeners       │  │ hotspots, overlays, nav, autoplay       │
 │ comments (Liveblocks)          │  │ events → Segment ingest + postMessage   │
 └────────────────────────────────┘  └─────────────────────────────────────────┘
```

## 3. Components we will build (mapping)

| Ours | Mirrors | Notes |
| --- | --- | --- |
| `extension/` MV3 (service worker, content script, offscreen doc, popup) | Arcade CRX | Same permission set minus the ones we do not need (no `debugger`, no `nativeMessaging` for v1). |
| `packages/model` | shared types chunk | Flow/Step/Hotspot types + zod schemas + migrations. |
| `packages/step-builder` | `parseExtensionCapture` | Pure function, unit-testable with fixture captures. |
| `packages/player` | standalone runtime (`initial-*.js`) | React, no app dependencies, mountable into iframe page and web component. |
| `apps/web` | Next.js app | Editor, dashboard, share pages, API routes. |
| `services/jobs` | server-side workers | Exports, AI copy, translations, TTS, smart split. |

Storage choice for v1 (inferred, ours): Postgres JSONB for the Flow document
(the Flow is always read/written whole) + S3-compatible object storage + a
video host (Mux or self-hosted HLS). Firestore is what Arcade uses; we do not
need its live listeners for v1.

## 4. Auth model (static-bundle, inferred)

- App calls use a Firebase ID token: `fetchWithToken(idToken, method, path, body)` sends `Authorization: <token>`.
- The extension calls `/api/extension/*` with cookies (`withCredentials: true`); the app passes the signed-in user to the extension via `chrome.runtime.sendMessage(extId, {name:"UserFromApp", user})` (`externally_connectable` for `*.arcade.software`).
- Desktop app auth uses a device flow: `/auth/desktop/[authId]` page → `POST /api/auth/desktop/{authId}/authorize`.
- Viewer endpoints (`/api/viewer/form`, share JSON, embed payload) are unauthenticated.
