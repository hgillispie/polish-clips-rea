# Observed network (signed-in HAR capture)

Evidence tag: **observed-network**. Source: 4 HARs recorded 2026-10-22 (America/New_York)
in a Free workspace we own (`HAR-1..4` in evidence-index.md). Session: home, new demo
from 2 uploaded PNGs, one hotspot and one callout added, ES AI translation, publish,
share/embed/export dialogs opened, flow and workspace insights (sample data), settings,
billing, brand kits.

Method: `tools/har-shapes/*.py` (committed) reads the HARs locally, keeps
`app.arcade.software` `/api/*` and `/_next/data`, Firestore and Firebase Storage/Auth,
and Arcade's own ingest host. It drops static assets and third-party trackers. It turns
every JSON body into a type skeleton (field → type). Ids are templated as `{id}`.
**No values are recorded here** except non-identifying enum literals, plan prices and
limits. The HARs themselves (tokens, cookies, email) stay on the REA box.

Type notation: `str`, `num`, `int`, `bool`, `null`, `ts` (Firestore timestamp),
`iso` (ISO-8601 string), `?` = optional (absent in some samples), `[]` = array never
non-empty in the capture.

## 1. The big picture: most data is Firestore, not REST

| Concern | Transport (observed-network) |
| --- | --- |
| Auth | Firebase Auth: `identitytoolkit…/v1/accounts:lookup {idToken}` and `securetoken…/v1/token` refresh. |
| All reads of flows, workspace, team, user, members, brand kits, credits, translations | Firestore WebChannel `Listen` (realtime listeners). No REST "get flow" or "list flows" call was made. |
| Flow create / edit / publish | REST: `POST /api/flows`, `PATCH /api/flows/{id}`, `POST /api/flows/set-status`. |
| Image upload | Direct to Firebase Storage `POST /v0/b/cdn.arcade.software/o?name={uid}/{id}.png`, then a Firestore `Write` of `images/{id}`. |
| AI translation | REST kick-off `POST …/translations/generate` (202) → result arrives on the `flows/{id}/translations` listener. |
| Page data | Pages Router `__NEXT_DATA__` (`/flows/[pid]/edit`, insights, billing, brand-kits, home…) and some App Router RSC routes (`/workspaces/[slug]/settings`, `/settings/privacy`). |
| Product analytics | Segment-compatible `t.arcade.show/api/ingest/{t,p,i}` plus a PostHog proxy `t.arcade.show/ingest/*` (flags, session recording). |

REST calls carry `x-arcade-workspace-id` and `x-arcade-team-id` headers. Chrome strips
`Authorization`/`Cookie` from HAR exports, so the REST auth header could not be confirmed
from this capture. It is still `decompiled`: Firebase ID token via `fetchWithToken`.

## 2. REST routes hit

| Method | Path | Status | Request | Response |
| --- | --- | --- | --- | --- |
| GET | /api/announcements?product= | 200 | — | `{announcements[{id,title,summary,imageUrl,videoUrl:null,buttonLabel,buttonDestination,buttonClose:bool,product,date:iso,autoShow:bool,availableFrom:null,availableUntil:null}], seen{items{<annId>:bool},latestDate,latestId}, preview:bool}` |
| POST | /api/announcements/seen | 204 | `{product, announcementId}` | — |
| GET | /api/user/company-hint | 200 | — | `{companyName: str\|null}` |
| POST | /api/user/product-experience | 204 | `{videoProductExperience: bool}` | — |
| GET | /api/wizard/saved-video-templates | 200 | — | `{templates[], nextCursor: null}` |
| GET | /api/wizard/prompt-video/pricing-model | 200 | — | `{model: str}` |
| GET | /api/flows/public-data?ids= | 200 | — | `PublicFlow[]` (§4.3; used for home-page sample/template demos) |
| POST | /api/flows | 201 | `FlowCreate` (§4.1) | `{id}` |
| PATCH | /api/flows/{id} | 200 | `{set: {steps?: Step[], aspectRatio?: num, …}, unset: str[]}` | `{modified: iso}` |
| POST | /api/flows/set-status | 204 | `{flowIDs: str[], status: num}` (publish = 2) | — |
| GET | /api/flows/{id}/access | 200 | — | `{membersWithAccess[]}` |
| POST | /api/flows/{id}/translations/generate | **202** | `{language: "es", mode: "missing"}` | `{message, started: bool, translation{createdAt:iso, updatedAt:iso, generationStatus{runId, status:"queued", totalVoiceovers:num, completedVoiceovers:num, failedVoiceovers:num, startedAt:iso, updatedAt:iso}, strings{name, description, steps{}}}}` |
| GET | /api/synthetic-voice | 200 | — | `{voices[{id,name,accent,avatarUrl,isBuiltIn:bool,isDefault:bool,previewUrl,description:str\|null,provider,languages:str[],models:str[],voice{key,variant,provider,model,languageCode:str\|null}}], isCustomApiKey: bool}` |
| GET | /api/community-showcase/{id} | 200 | — | `{isInCommunityShowcase: bool, isHidden: bool, item: null}` |
| GET | /api/revalidate?id=&variant= | 200 | — | `{revalidated: bool}` (ISR refresh of the share page after publish/edit) |

Not hit in this session (still static-bundle only): `/api/flows/{id}/export`,
`/api/insights/*`, `/api/billing/*`, `/api/ai/*`, `/api/flows/{id}/update-step`.
Opening the share, embed and export dialogs fired **no** extra network calls. They render
from the flow doc already in memory, plus `/access`, `/community-showcase` and
`/revalidate`.

## 3. Firestore

### 3.1 Listen targets (realtime queries)

| Target | Filter fields (operators not recorded) | Order | Limit |
| --- | --- | --- | --- |
| doc `users/{uid}`, `workspaces/{id}`, `teams/{id}`, `aiCredits/{workspaceId}` | — | — | — |
| doc `flows/{id}`, `wizardSessions/{id}` | — | — | — |
| `flows` | `status`, `teamId`, `modified` | modified | yes |
| `flows` | `editors`, `status`, `modified` | modified | yes |
| `flows` | `createdBy`, `status` | modified | yes |
| `flows` | `status`, `teamId`, `unlocked` | — | no (counts for plan limit) |
| `flowsCollections` | `status`, `teamId` | modified | yes |
| `flows/{id}/translations` | — | — | no |
| `flows/{id}/stepGenerations` | — | created | 200 |
| `promptVideoGenerations/{id}/exports` | — | requestedAt | 500 |
| `promptVideoGenerations`, `videoGenerations`, `visualProjects`, `videos` | `teamId`/`workspaceId`, `deleted`, (`format`, `publishStatus`, `assetId`) | modified/created | yes |
| `workspaces/{id}/members`, `teams/{id}/members` | — | __name__ | yes |
| `workspaces/{id}/themes` | `deleted` | created | yes |
| `brandkitv2/{workspaceId}/kits`, `…/kits/{id}/proposals` | — | created | — |
| `backgroundImages` | `createdBy`, `variant` (+ `teamId`) | created | yes |
| `workspaceInvitations` | `inviteeEmail`+`status`; `workspaceId`+`status` | created | yes |

Listen responses with document bodies were only captured in HAR-2/3. The other HARs
recorded the long-poll responses empty.

### 3.2 Document shapes

`flows/{id}`: see §4.2 (authoritative stored form).

`users/{uid}`:
`{name, email, photoURL, emailDomain, created:ts, modified:ts, createdBy, lastModifiedBy,
lastUsedTeamId, lastUsedWorkspaceId, teams[{teamId, workspaceId, name, slug, type:"Admin", status:"Active", visibility:"personal"}],
workspaces[{workspaceId, name, slug, role:"Owner", status:"Active"}],
features{"Workspaces":bool, "Video Product Experience":bool},
meteringUsage{panAndZoom:int, …}, launchLanding{basis:"signup", product:"video", decidedAt:ts},
personalizedUseSelection{video:bool}, onboardingQuestionSteps{videoInterests, heardAboutUs},
onboardingVideoTypes:str[], videoLaunchModalSeenAt:str, firstOwnedWorkspaceCreditsGrantedAt:ts,
cmsAnnouncementSeen{demo{items{<id>:bool}, latestDate, latestId}, video{items{}, latestDate}},
intercomUserId, intercomUserHash}`

`workspaces/{id}`: `{name, slug, emailDomain:null, created:ts, modified:ts, createdBy, lastModifiedBy,
freePlanType:"singleFlow", onboardingBrandKitStep:"skipped", subscriptions[],
features{"Disable IP Tracking":bool, "Workspace Auto-Join":bool, "Publish Events to Host":bool, "Do Not Track":bool}}`

`workspaces/{id}/members/{uid}`: `{userId, email, role:"Owner", status:"Active", created, modified, createdBy, lastModifiedBy}`

`teams/{id}`: `{workspaceId, name, slug, visibility:"personal", status:"active", features{}, integrations{}, hubSpotEnabled:bool, clearbitEnabled:bool, created, modified, createdBy, lastModifiedBy}`

`teams/{id}/members/{uid}`: `{id, email, type:"Admin", status:"Active", created, modified, createdBy, lastModifiedBy}`

`aiCredits/{workspaceId}`: `{scope:"workspace", creditsRemaining:int, reservedCredits:int, created, modified, createdBy, lastModifiedBy}`

`brandkitv2/{workspaceId}/kits/{id}`: `{name, workspaceId, domain:null, status:"ready", creationOrigin:"empty",
colorsStatus:"pending", assetsStatus:"pending",
identity{colors{palettes[{id, name, isDefault, primary, secondary, highlight, background, textColor, darkNeutral, lightNeutral, allColors[]}]},
         logos{logotypes{items[]}, icons{items[]}}, fonts{primary{fontFamily, weight}, secondary{fontFamily, weight}}},
messaging{tones[], voice{voiceDescription, productDescription, icp, keyMessaging, dos, donts, wordsToAvoid, baseline}},
assets{product, photography, backgrounds, illustrations}, foundations{sources{files[], links[]}}, customElements{items[]},
created, modified, createdBy, lastModifiedBy}`

`promptVideoGenerations/{id}` (AI-video product, created by onboarding):
`{name, teamId, createdBy, format:"wizard", targetLength:"30s", duration:num, publishStatus:int, deleted:bool,
folderId:null, tagIds[], wizardSessionId, exampleVideoSource{videoId, workspaceId}, currentRevisionId,
editVersion:int, headVersion:int, thumbnailUrl, created, modified, lastModifiedBy}`

### 3.3 Client writes (Firestore `Write` channel)

| Doc | Fields | Transforms |
| --- | --- | --- |
| `images/{id}` | `{name, url, label, size{width,height}, blurhash, workspaceId, deleted:false, lastUpdatedAt:ts, createdBy, lastModifiedBy}` | `created`, `modified` = serverTimestamp |
| `users/{uid}` | updateMask `meteringUsage` (`{panAndZoom:int}`), `lastModifiedBy` | `modified` = serverTimestamp |

So the **client itself** writes the metering counter for pan-and-zoom on the user doc.
The decompiled code used a transaction for this. Flow edits never go through Firestore
writes; they use `PATCH /api/flows/{id}`.

### 3.4 Upload sequence (editor "upload image" → new demo)

```
POST firebasestorage…/v0/b/cdn.arcade.software/o?name={uid}/{imageId}.png   (raw bytes)
   → {name, bucket, generation, metageneration, contentType, size, md5Hash, crc32c, etag, downloadTokens, timeCreated, updated, storageClass, contentEncoding, contentDisposition}
Firestore Write images/{imageId}  (url, size, blurhash computed client-side)
POST /api/flows  FlowCreate{steps: []}           → {id}
PATCH /api/flows/{id} {set:{steps:[ImageStep…], aspectRatio}, unset:[]}  (once per edit; steps array sent whole)
```
The browser computes `blurhash` and `size` itself. The image step's `assetId` equals the
`images/{id}` doc id, and `url`/`originalImageUrl` point at the CDN object.

## 4. Flow document (authoritative)

### 4.1 `FlowCreate` (POST /api/flows body)
`{name, externalName:null, description, schemaVersion:"1.1.0", aspectRatio, steps[], cta{}, teamId, folderId:null,
themeId:null, menu:null, optimizeFlowForMobileView, showCaptions, showCopyLink, showFullscreen, showReplay,
showTranslation, showFlowNavIndicator:"AUTO", flowWrapper:1, customCursor:1, font:"Inter", showStartOverlay,
showBackNextButtons, disableKeyboardNavigation, keepSoundOffUntilEnabled, startOverlayButtonText:"",
autoplay{enabled, delay:null}, backgroundMusicUrl:null, backgroundMusicVolume:1, bgImage:null,
sharePageLayout{type:"default", showHeader, showLogo, showButton, showDescription, showCommenting},
useVersioning, createdWith:"arcade-web"}`

### 4.2 Stored / SSR form (`flows/{id}` and `/flows/[pid]/edit` `_serializablePrivateFlow`)
All §4.1 fields, plus: `id, status:int (1 draft → 2 after publish), editors[], created, modified,
createdBy, lastModifiedBy, submittedForSpotlight, experiments[], experimentsConfig{}, isTemplate,
ogImagePreset:null, showArcadeButton:null, openingAnimation:null, demoModeByDefault,
showChapterStyleOnPopout, gifUrl:str, videoUrl:str, tagIds[], uploadId:str, firstViewed:null,
unlocked:null, customVariables:null, thumbnailUrl:null, originalLanguage:null,
themeIdMismatchConfirmed:null, sharePageThemeId:null, watermark:null, sharePageLogo:null,
sharePageFaviconUrl:null, sharePageButton:null, prefs:null, useMagicCursor, hasComments,
clipsReqId:str, clipsRequested{}, hasUsedAI, processedAI, processedAIReason:null, resources[],
versionId:str, approvalRequestedBy:null, mobileLayout:null, mobileBackground:null, ai{},
useCase:null, usedUploadInChunks, autoSplit{}, crawlable, rrwebEventsUrls:null,
claimToken:null, urlToDemoKind:null}`.

Date encoding differs by transport: Firestore `timestampValue`; SSR props
`{"__arcadeIsoDate": iso}` (a custom serializer marker); REST/public-data plain ISO strings.

Uploaded image step (observed in PATCH and Firestore):
`{id, type:1, url, originalImageUrl, assetId, blurhash, size{width:int,height:int}, isMobileRecording:false,
panAndZoom{enabled}, hotspots[{id, x, y, width, height, label, style:"pulsating"|"callout"|"area",
shape?:"rounded", bgColor, textColor, overlayColor?, defaultOpen}]}`.
`x, y` are 0..1 fractions; `width`/`height` are pixels (int or float).

### 4.3 PublicFlow (`/api/flows/public-data`)
The stored form minus private fields (no `editors` content, no AI/claim fields). Steps
carry the full captured shape: `clickContext{cssSelector, elementType:"button"|"link"|"other",
text, sections[], originalRect{x,y,width,height}}`, `pageContext{url, title, description,
language, width, height}`, video fields `{streamUrl, videoThumbnailUrl, playbackRate (1|1.5|4),
startTimeFrac, endTimeFrac, duration, muted, videoProcessing}`,
`cameraRecording{enabled, audioOnly, placement:"bottom-right", shape:"circle", size:"medium",
playbackRate, startTimeFrac, endTimeFrac}`, `syntheticVoice{enabled, playbackRate}`,
`panAndZoom{enabled, zoomLevel, position{top,left}}`, overlay `{title, subtitle, theme:"light",
variant:"buttons", textAlign:"left", showPreviewImage, showLogo, paths[{id, pathType:"step",
buttonText, buttonColor, buttonTextColor, targetStepId:null}]}`; flow-level
`ogImagePreset:"style4"`.

### 4.4 Translation doc (`flows/{id}/translations/{lang}`)
`{createdAt, updatedAt, generationStatus{runId, status: queued→completed, totalVoiceovers,
completedVoiceovers, failedVoiceovers, startedAt, updatedAt, finishedAt}, strings{name,
description, steps{<stepId>: …}}}`. A 2-step image demo with no voiceover completed within
the capture.

## 5. Page props (`__NEXT_DATA__`)

Common to every signed-in page: `_serializableUserProfile, _serializableTeam,
_serializableWorkspace, _teamSlugsById, _lockedMemberships{workspaceIds[], teamIds[]},
_algoliaApiKey, _featureFlags{<flag>: bool|variant}, _flowsRBACAccess, _offlineModeEnabled,
_totalNumberOfCredits:num, _aiCreditsLaunched:bool, _viewedProduct:"demo"|"video",
isReadonly, userSerialized`.

| Page | Extra props |
| --- | --- |
| `/flows/[pid]/edit` | `_serializablePrivateFlow, _serializableTranslations{<lang>: Translation}, _serializableFlowOwnership{team, workspace}, workspaceId, flowTheme{}, flowMode:"EDIT", magicCursor:null, videoCursorPaths:null, canAccessPrivateFlow, flowsRBACAccess{}, fallback{"/api/flows/{id}/access": …}` (SWR fallback) |
| `/flows/[pid]/insights` | `flowSSR` (= flow), `_serializablePrivateFlow`, `_serializableTranslations`, `_serializableFlowOwnership`, `timezone`, `fallback` |
| `/workspaces/[slug]/teams/[team]/insights` | `teamId, timezone` |
| `/workspaces/[slug]/settings/billing` | `prices{proMonthly, proAnnual, growthMonthly, growthAnnual, growthMonthlyLegacy, growthAnnualLegacy, growthMonthlyFiveSeatsLegacy{basePrice, unitAmount, unitAmountStartsAt}, growthAnnualFiveSeatsLegacy{…}, aiCreditsPack}, currPlan:"Free", currInvoiceTotal:str, interval:str, currentPeriodEnd:null, cancelAt:null, aiCredits{availableCredits, totalCredits}, defaultPaymentMethod:str, defaultPaymentMethodExpires, serializableBillableWorkspaceMembers{<i>: member}` |

**Insights carried no data over the network**: both insights pages (team and flow)
loaded with no `/api/insights/*` request and no Firestore insights listener, and they
showed sample data. On Free with no views, the sample dataset is rendered client-side.
The real insights response shapes are still unobserved (§7).

## 6. Product analytics (Arcade's own)

`POST t.arcade.show/api/ingest/{t|p|i}` (text/plain JSON, analytics.js): `t` track
`{event, properties, context{page, userAgent, userAgentData, locale, library, timezone}, messageId, anonymousId, userId, timestamp, sentAt}`,
`p` page `{name, properties{…flowId?, sessionId?, productExperience}}`, `i` identify
`{traits{email, firstName, planName, planIsTrial, creationDate, isInternalUser, isReferred, onboardingExtensionDeniedReason}}`.
Page names seen: Home, Video Home, Editor, Viewer, Shared View, Analytics, Team Library,
Brand Kits, Workspace Settings, User Privacy Settings, Billing Page.
Editor events seen: Flow Created, Add Step From Options (`type:"My computer"`), Hotspot
Added (`style`), Step Tool Clicked, Image Editor Opened, Step-Level Pan and Zoom Enabled,
Flow AI Translation Started, Flow Published, Action Button Clicked, Paywall Displayed
(`paywallSource`), Paywall continue clicked, First Demo Checklist Shown, Get Started Guide
Viewed, Step Reached, Frame Visibility. The editor preview emits the same viewer
events as the player (`Step Reached` with `fromStepActiveTimeMs`, …).

PostHog runs behind the same host (`/ingest/flags/`, `/ingest/s/` session recording,
`/ingest/e/`). The flags response `{flags{<key>{key, enabled, variant, reason{code,
condition_index, description}, metadata{id, version, payload, has_experiment}}},
errorsWhileComputingFlags}` listed 43 experiment/rollout flags, e.g.
`limited-free-plan-vs-the-old-plan`, `metering-features`, `growth-trial-vs-metering`,
`annual-pricing-first`, `pro-experiment-50-off`, `unlimited-brand-kits`,
`themes-brandkits-merged`, `push-desktop-use`, `share-button-split` and `wizard-*` (×17).

## 7. Still not observed
- `/api/insights/*` responses (needs a published demo with real views, or a Growth trial).
- Export job (`POST /api/flows/{id}/export` + `exports` doc lifecycle): the dialog was
  opened but no export was started.
- AI hotspot/copy endpoints (`/api/ai/*`, `/api/arcade-ai`) and billing actions.
- Extension capture uploads (`/api/extension/*`): the demo came from uploaded PNGs.
