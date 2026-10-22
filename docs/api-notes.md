# API notes (backend surface)

Recovered from client code only: the extension's HTTP client (**decompiled**) and the
web app's typed SDK factories / `fetchWithToken` call sites (**static-bundle**,
some **decompiled**). No authenticated requests were made; response shapes are given
only where the client reads them. Paths are relative to the app origin.

Auth: app routes send `Authorization: <Firebase ID token>`; extension routes use the
session cookie (`withCredentials`). Viewer routes are public.

## Extension (capture)

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| POST | /api/extension/demo-start | `{chromeExtensionVersion, name, useAI, uploadInChunks}` | `{id}` (flowId, status recording) |
| POST | /api/extension/upload-url | `{flowId, type: image\|video\|html, resumable}` | `{uploadUrl, contentType, publicUrl}` |
| PUT | *signed uploadUrl* | bytes | — |
| POST | /api/extension/image | `{flowId, hasHTML, useAI, assetId, url, x, y, pageContext, rectContext}` | image analysis `{blurhash, size, aspectRatio, …}` |
| POST | /api/extension/scrape | `{sessionId: flowId, pages:[{websiteUrl, imageId, htmlUrl}]}` | — |
| POST | /api/mux/create-asset | `{source, sourceUrl, uploadId, flowId, stepId}` | asset/playback ids |
| POST | /api/extension/demo-end | see capture/upload-and-finalize.md | — |
| POST | /api/extension/demo-status | `{id, status: deleted\|error, description}` | — |

## Flows (`/api/flows`)

| Method | Path | Body / notes |
| --- | --- | --- |
| POST | /api/flows | create (schema in model/flow-model.md) |
| PATCH | /api/flows/{id} | `{set, unset}` → `{modified}` |
| GET | /api/flows/public-data | public subset (params not recovered) |
| POST | /api/flows/{id}/duplicate | `{teamId, folderId, applyTheme}` |
| POST | /api/flows/{id}/move | `{teamId, folderId}` |
| POST | /api/flows/{id}/merge | `{flowId}` → `{versionId}` |
| POST | /api/flows/{id}/export | `{type, fps, sizeConstraint, language, opts}` → `{exportId}` |
| POST | /api/flows/{id}/update-step | `{stepId, action:"updateEditedImage", url, blurhash, size, imageEditorState}` |
| POST | /api/flows/{id}/translations/generate | `{language, mode:"missing"}` → `{started}` |
| PUT | /api/flows/{id}/translations | `{language, translations}` |
| DELETE | /api/flows/{id}/translations?language= | |
| POST | /api/flows/{id}/translate-strings | `{destinationLanguage, sourceStrings}` |
| GET | /api/flows/{id}/access | `{membersWithAccess}` |
| POST | /api/flows/{id}/access/invite | `{accessLevel, email, flowUrl, flowName, inviteeName?, …}` |
| POST | /api/flows/{id}/access/invite/request | |
| PATCH / DELETE | /api/flows/{id}/access/{uid} | `{accessLevel}` |
| POST / PATCH | /api/flows/{id}/access/{uid}/request | `{accessLevel}` / `{accessStatus}` |
| POST | /api/flows/{id}/video-generation/{generationId} | flow → AI video (editor/ai-features.md) |
| POST | /api/flows/{id}/step-generations/prompt-video-import | |
| POST | /api/flows/{id}/step-generations/{gid}/retry | |
| POST | /api/flows/{id}/shortcuts | flow shortcuts (folders) |
| POST | /api/flows/set-status \| set-unlocked \| tag \| untag \| request-approval \| approve | `{flowIDs[1..30], …}` |
| POST | /api/flows/video-effects \| blur-all | bodies not recovered |

`/api/flows-collections` mirrors create/edit/duplicate/move/access/tag/status plus
`PATCH /{id}/thumbnails`.

## AI

| Method | Path | Body |
| --- | --- | --- |
| POST | /api/ai/flow-hotspots | `{…options, flowId, promptId}` → `{hotspots, promptId}` |
| POST | /api/ai/add-hotspots | `{flowId, videoAssetId}` |
| POST | /api/ai/smart-split | `{flowId, stepId}` |
| POST | /api/ai/generate-element | `{html, pageUrl, prompt}` |
| POST | /api/arcade-ai | `{value, context, action, tone}` → `{message, suggestion}` |
| POST | /api/ai/flow-video-generation | `{flowId, fps, sizeConstraint, brandKitId}` → `{videoGenerationId}` |
| POST | /api/ai/flow-visual-copy-generation | `{brandKitId, tone, flowId, promptText, type, templates}` |
| POST | /api/ai/stock-videos/search\|resolve\|similar\|select, stock-images/search\|resolve, prompt-image-generation, prompt-scene-generation, source-url-probe, proxy-file-fetch | AI-video product |
| GET | /api/ai/credits-launch | credit launch state |
| POST | /api/ai/video-generation-rating | `{generationId, generationType, rating, reasons, note}` |
| GET/POST/PUT | /api/synthetic-voice[/pronunciation[/preview]] | see model/variables-translations-voice.md |
| POST | /api/voiceovers | `{urls}` → `{voiceovers}` |

## Viewer (public)

| Method | Path | Notes |
| --- | --- | --- |
| GET | /_next/data/{build}/share/{id}.json | share page props (observed) |
| GET | demo host `/embed/v1/flows/{id}` | embed payload (observed) |
| POST | /api/viewer/form | form answers (model/overlays-branching-forms.md) |
| GET | /api/oembed?url= | oEmbed |
| POST | analytics ingest (`t.<domain>/api/ingest`) | Segment-compatible batch |

## Insights, leads, integrations

`/api/insights/aggregated/{id}`, `/api/insights/overviewPlays/{id}`,
`/api/insights/companiesForLeads/{id}`, `PUT /api/leads/subscribe`, `DELETE /api/leads/unsubscribe`,
`POST /api/clearbit/toggle`, `/api/teams/{id}/webhook-settings`, `/api/workspaces/{id}/api-keys`,
`POST /api/team/{id}/update-integrations`, HubSpot and Salesforce OAuth pages
(`/integrations/hubspot|sfdc/authorize|callback`). Shapes not recovered.

## Workspace, team, billing, misc

- `/api/workspace/create {name, slug, logoUrl}`, `check-slug {slug}`, `accept-invite`,
  `request-membership`, `request-role-upgrade {workspaceId, note}`,
  `/api/workspace/{id}/{invite|nominate-member|approve-member|reject-member|rescind-invite|resend-invite|update-member|deactivate-member|accept-role-upgrade|reject-role-upgrade|join-team|upgrade {isMonthly, planVariant}|delete}`,
  `/api/workspace/{id}/teams/{teamId}/invite {emails, type}`, `…/member-count`.
- `/api/team/create`, `/api/team/update-logo {type, url}`, `/api/team/{id}/update-slug {slug}`.
- `/api/billing/summary`, `credit-usage`, `downgrade-to-free`, `downgrade-to-pro?frequency=`, `cancel-immediately[/preview]`, `cancel-overdue[/status]`, `ai-video/*`.
- `/api/auth/desktop/{authId}/authorize` (desktop device login), `/api/saml/provider-for-domain` (SSO).
- `/api/upload/init`, `/api/upload`, `/api/images/attributes/{id}?source=&uploadId=`.
- `/api/brand-kit-v2`, `/api/workspace/{id}/brand-kits/*`, `/api/fonts/*`, `/api/referrals/*`,
  `/api/community-showcase/*`, `/api/media-favorites`, `/api/shortcuts`.
- AI-video product: `/api/prompt-to-video`, `/api/url-to-video`, `/api/video-generations/*`,
  `/api/prompt-video-generations/*`, `/api/wizard/*`, `/api/visual-projects/*`.
- 270 distinct `/api/...` strings were found in total (local list `api-paths-raw.txt`).
