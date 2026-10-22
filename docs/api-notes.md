# API notes (backend surface)

Pass 1 recovered this from client code: the extension's HTTP client (**decompiled**) and
the web app's typed SDK factories / `fetchWithToken` call sites (**static-bundle**, some
**decompiled**). Pass 2 added the desktop app and the AI-video extension (**decompiled**),
plus a signed-in HAR capture (**observed-network**). Routes marked ✓ were hit, and their
full request/response type shapes are in arcade-analysis/observed-network.md. Paths are
relative to the app origin.

Auth: app routes send `Authorization: <Firebase ID token>` plus `x-arcade-workspace-id` /
`x-arcade-team-id` (✓ headers). Extension routes use the session cookie
(`withCredentials`). Viewer routes are public. Most *reads* are Firestore listeners, not
REST (✓, observed-network §3).

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
| POST | /api/flows ✓ | create: `FlowCreate` with `steps:[]` → 201 `{id}` |
| PATCH | /api/flows/{id} ✓ | `{set{steps (whole array), aspectRatio?, …}, unset[]}` → `{modified: iso}` |
| GET | /api/flows/public-data?ids= ✓ | `PublicFlow[]` (unauthenticated) |
| POST | /api/flows/{id}/duplicate | `{teamId, folderId, applyTheme}` |
| POST | /api/flows/{id}/move | `{teamId, folderId}` |
| POST | /api/flows/{id}/merge | `{flowId}` → `{versionId}` |
| POST | /api/flows/{id}/export | `{type, fps, sizeConstraint, language, opts}` → `{exportId}` |
| POST | /api/flows/{id}/update-step | `{stepId, action:"updateEditedImage", url, blurhash, size, imageEditorState}` |
| POST | /api/flows/{id}/translations/generate ✓ | `{language, mode:"missing"}` → 202 `{message, started, translation{generationStatus{runId,status,…}, strings}}` |
| PUT | /api/flows/{id}/translations | `{language, translations}` |
| DELETE | /api/flows/{id}/translations?language= | |
| POST | /api/flows/{id}/translate-strings | `{destinationLanguage, sourceStrings}` |
| GET | /api/flows/{id}/access ✓ | `{membersWithAccess[]}` |
| POST | /api/flows/{id}/access/invite | `{accessLevel, email, flowUrl, flowName, inviteeName?, …}` |
| POST | /api/flows/{id}/access/invite/request | |
| PATCH / DELETE | /api/flows/{id}/access/{uid} | `{accessLevel}` |
| POST / PATCH | /api/flows/{id}/access/{uid}/request | `{accessLevel}` / `{accessStatus}` |
| POST | /api/flows/{id}/video-generation/{generationId} | flow → AI video (editor/ai-features.md) |
| POST | /api/flows/{id}/step-generations/prompt-video-import | |
| POST | /api/flows/{id}/step-generations/{gid}/retry | |
| POST | /api/flows/{id}/shortcuts | flow shortcuts (folders) |
| POST | /api/flows/set-status ✓ (`{flowIDs, status}` → 204) \| set-unlocked \| tag \| untag \| request-approval \| approve | `{flowIDs[1..30], …}` |
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
| GET/POST/PUT | /api/synthetic-voice[/pronunciation[/preview]] | GET ✓ → `{voices[…], isCustomApiKey}`; see model/variables-translations-voice.md |
| POST | /api/voiceovers | `{urls}` → `{voiceovers}` |

## Viewer (public)

| Method | Path | Notes |
| --- | --- | --- |
| GET | /_next/data/{build}/share/{id}.json | share page props (observed) |
| GET | demo host `/embed/v1/flows/{id}` | embed payload (observed) |
| POST | /api/viewer/form | form answers (model/overlays-branching-forms.md) |
| GET | /api/oembed?url= | oEmbed |
| POST | `t.arcade.show/api/ingest/{t\|p\|i}` ✓ | Segment-compatible single events (text/plain JSON). PostHog proxy `/ingest/*` on the same host |
| GET | /api/revalidate?id=&variant= ✓ | `{revalidated}`. ISR refresh after publish |
| GET | /api/community-showcase/{id} ✓ | `{isInCommunityShowcase, isHidden, item}` |

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
- Desktop device login (decompiled, desktop-app.md): `POST /api/auth/desktop` → `{authId}`; browser page `/auth/desktop/{authId}` → `POST /api/auth/desktop/{authId}/authorize`; app polls `/api/auth/desktop/{authId}` (with a `deliveryId`) → `authenticated` (token) \| `expired` \| `claimed-by-other-client`. `/api/saml/provider-for-domain` (SSO).
- `/api/upload/init`, `/api/upload`, `/api/images/attributes/{id}?source=&uploadId=`. Desktop upload sequence (decompiled): `POST /api/upload/init` → `{id}`; per asset `POST /api/upload/{id}/upload-url` → signed URL, then PUT bytes; screenshots via `POST /api/upload/{id}/image`; `POST /api/upload/{id}/end`; video via `POST /api/mux/create-asset`.
- User/UI (✓): `GET /api/announcements?product=` → `{announcements[…], seen{items, latestDate, latestId}, preview}`, `POST /api/announcements/seen {product, announcementId}` → 204, `GET /api/user/company-hint` → `{companyName}`, `POST /api/user/product-experience {videoProductExperience}` → 204, `GET /api/wizard/saved-video-templates` → `{templates[], nextCursor}`, `GET /api/wizard/prompt-video/pricing-model` → `{model}`.
- Billing (✓ page props, not REST): `/workspaces/[slug]/settings/billing` SSR props `{prices{…}, currPlan, interval, currInvoiceTotal, currentPeriodEnd, cancelAt, aiCredits{availableCredits,totalCredits}, defaultPaymentMethod…}`. See plans-and-gating.md.
- `/api/brand-kit-v2`, `/api/workspace/{id}/brand-kits/*`, `/api/fonts/*`, `/api/referrals/*`,
  `/api/community-showcase/*`, `/api/media-favorites`, `/api/shortcuts`.
- AI-video product: `/api/prompt-to-video`, `/api/url-to-video`, `/api/video-generations/*`,
  `/api/prompt-video-generations/*`, `/api/wizard/*`, `/api/visual-projects/*`.
- 270 distinct `/api/...` strings were found in total (local list `api-paths-raw.txt`).

## Extension cookie login (decompiled, both extensions)

`POST /api/extension-cookie-login {chromeExtensionVersion}` (JSON, sent with the app
cookie) → `{user, …}`. The popup (capture extension) or sidepanel (AI-video extension)
saves `user` to `chrome.storage.local` when it is not yet logged in.

## AI-video recorder extension (`plbpm…`, decompiled)

All calls go through one helper: POST, `credentials:"include"`, JSON or FormData, 90 s
timeout (300 s for FormData). A 404 or an HTML response means "server too old /
unavailable". See arcade-analysis/ai-video-extension.md.

| Path | Body | Response read |
| --- | --- | --- |
| /api/producer/chat | `{messages[{role,content}], pages[{url,title,text,role}], recordings?[Recording], answers?{…}, brief?:str, recordingOpening?, batchInterview?, interviewFinished?}` | `{reply, options[], questions?, amendsBrief, settles, readyToWrite, asksVisuals}`. On 400 it retries without the newer flags |
| /api/producer/classify-page | `{pages[{url,title,text,role}], candidate{url,title,text}}` | `{relationship, options[{role,…}]}` |
| /api/producer/read-video | `{url}` | `{text}` (transcript of a video page) |
| /api/producer/upload-image | FormData `image` | `{imageId}` |
| /api/producer/upload-file | FormData `file` | `{url, mimeType, name, size}` |
| /api/producer/analyze-recording?recordingUses=1&recordingLayouts=1 | `{recording, pages, preference, conversation, otherRecordings[]}` (170 s timeout; 403/503 handled) | analysis `{recommendation{layouts…}, uses…}` |
| /api/producer/draft | `{pages, recordings?, answers?, conversation?:str ≤50k}` | brief `{topic, audience, objective, format, keyMessage, tone, narrativeArc, mustHitMoments[], keyFacts[], recommendedLength}` |
| /api/producer/capabilities[?videoCredits=1] | `{}` | integer feature bits `{extensionVideoContext, recordingLayouts, followUpsAfterInterview, templateMediaRecording}` (==1 → on); 3 s timeout, all off on failure |
| /api/producer/brand-kits | GET | brand kit list |
| /api/wizard/prompt-video/session | `{action:"start", prompt, brandKitId, targetLength:"15s"…"120s", aspectRatio:"16:9", extensionVideoContext?{source:"chrome-extension", version:1, recordings[]}, …attachments}` | `{sessionId}` → opens the web video wizard |
| /api/extension/demo-start, /api/extension/upload-url, /api/mux/create-asset, /api/extension/demo-status | same as capture extension | screen/camera video upload to Mux |
