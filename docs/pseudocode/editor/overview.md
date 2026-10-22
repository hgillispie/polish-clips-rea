# Editor overview

Evidence: **static-bundle** (routes, SDK methods), **decompiled** (flow write schema,
flow hooks), **observed-network** (signed-in HAR, arcade-analysis/observed-network.md), **inferred** where marked.

## Surfaces

- `/flows/[pid]/edit`: step rail (thumbnails, drag reorder, hide from navigation), canvas
  (image with draggable hotspots/callouts, video trimmer, overlay editor), right panel
  (step settings: hotspot style/colour/target, pan-zoom, voiceover script, CTA), flow
  settings (theme, wrapper, cursor, nav, autoplay, music, share page layout, variables,
  translations), "Script View" (all voiceover scripts in one list), "Branching Map".
- `/flows/[pid]/view`: preview player; `/flows/[pid]/insights`; `/flows/[pid]/guide`.
- Image editor: blur boxes, crop (see model/pan-zoom-and-image-edits.md).
- Page Editor (extension) for editing live page text before capture.
- Add step: upload image/video (`/api/upload/init`, `/api/upload`), media library
  (`media-favorites`), record more (extension `LastEditedFlow` → append), empty step,
  chapter/form/embed overlay, duplicate step, merge another flow as a version (`POST /api/flows/{id}/merge {flowId}`).

## Save model

- Optimistic local state; writes go through `PATCH /api/flows/{id} {set, unset}` with the
  whole `steps` array when any step changes. **observed-network**: 14 PATCHes in the
  session. Each one carried `set.steps` (the full array) and sometimes `set.aspectRatio`,
  with `unset: []`, and returned `{modified}`.
- Upload-image step (observed-network): bytes go straight to Firebase Storage
  (`{uid}/{imageId}.png`). The client computes blurhash and size, writes `images/{id}`
  through the Firestore SDK, then PATCHes the flow with a `type:1` step whose
  `assetId = imageId`.
- Initial page data comes from `__NEXT_DATA__` (`_serializablePrivateFlow`,
  `_serializableTranslations`, `flowMode:"EDIT"`, `canAccessPrivateFlow`, SWR
  `fallback` for `/api/flows/{id}/access`). After that a Firestore listener keeps it live.
- The share/embed/export dialogs make no network calls when opened (observed-network).
- Live Firestore listener refreshes the doc (multi-tab, AI job results land this way:
  `awaitFirestoreDocCondition("flows", id, predicate)` polls until e.g. `autoSplit.status` reaches a state).
- Undo/redo history in the client; external updates (AI results) are captured into
  history so they can be undone (`captureExternalUpdateForHistory`, "showUndoToast").

## Collaboration and access

- Comments: Liveblocks rooms per flow (`/api/liveblocks/room-notification-settings {flowId}`),
  shown on share page when `sharePageLayout.showCommenting` ("Comments on Share Page").
- Per-flow access: `GET /api/flows/{id}/access`, invite `POST …/access/invite`, change
  level `PATCH …/access/{uid} {accessLevel: view|edit}`, remove `DELETE …/access/{uid}`,
  request access `POST …/access/{uid}/request`, answer `PATCH …/access/{uid}/request {accessStatus: Granted|Denied}`.
- Teams/workspaces with roles (Admin, Editor, Viewer…), RBAC on Enterprise.
- Approval flow: request-approval / approve (bulk endpoints).
- Versions (Enterprise "Version history"): `flows/{id}/versions`, `/flows/[pid]/version/[versionId]`, `useVersioning`, `versionId`.
- Duplicate / move between teams: `POST /api/flows/{id}/duplicate`, `POST …/move {teamId, folderId, applyTheme}`.

## Themes and brand kits

Workspace themes (`themes`, `/workspaces/[slug]/settings/themes`) set colours, font,
wrapper, cursor; `flow.themeId`. Brand kits v2 (`/api/workspace/{id}/brand-kits/*`) are
mostly for the AI-video product but also supply logo/fonts/colours.
