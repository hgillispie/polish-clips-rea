# Flow document

Evidence: **decompiled** (`getFlowFromDoc` defaults and the server write zod schema in the
web bundle), **observed** (public share JSON keys). The Flow is one JSON document
(Firestore doc `flows/{id}`), read and written whole. Subcollections:
`flows/{id}/versions` (version history), `flows/{id}/mediaProcessingJobs`.

## Identity and ownership

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| id | string `^[A-Za-z0-9_-]{1,128}$` | generated (20-char) | Share URL key. |
| teamId | string | — | Owning team (workspace sub-unit). |
| createdBy, created, modified | uid, timestamps | — | |
| editors | uid[] | [] | Direct collaborators. |
| folderId | string \| null | null | Dashboard folder. |
| tagIds | string[] | [] | |
| status | PublishStatus | draft (published for very old docs) | draft 1, published 2, archived 3, deleted 4, recording 5, error 6, pending 7. Setting published stamps `publishedDate`. |
| isTemplate, submittedForSpotlight, unlocked | bool | false | |
| useVersioning, versionId | bool, string | false, "" | Enterprise version history. |
| approvalRequestedBy | uid \| null | null | Approval workflow. |
| createdWith | string | "" | e.g. `extension/1.9.33`, desktop, upload. |
| uploadId | string | "" | Links to capture upload. |
| schemaVersion | string | "" | |

## Content

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| name, description | string | "", "" | `titleSource`: default \| ai \| user. `externalName` overrides public title. |
| aspectRatio | number | 0 → computed | **height / width** of the stage. |
| steps | Step[] | [] | See [steps.md](steps.md). |
| capturedEvents | object[] | — | Raw capture events kept for re-processing (AI, auto-recapture). |
| videoTimestampWindows | [start,end][] | — | From capture. |
| customVariables | `{ [name]: { fallback, createdAt } }` \| null | null | [variables-translations-voice.md](variables-translations-voice.md) |
| originalLanguage | string \| null | null ("en") | |
| resources | `{id, type:"file"\|"link", label, url}[]` | [] | Shown on share page. |
| menu | `{ entries: {id, label, targetId}[] }` \| null | null | Table-of-contents / chapter menu (plan-gated "menu"). |
| cta | object | {} | Flow-level CTA (share page button). |

## Presentation

| Field | Type | Default |
| --- | --- | --- |
| flowWrapper | none 1 \| browserLight 2 \| browserDark 3 \| mobileDark 4 | none |
| customCursor | default 1 \| arcade 2 \| mobile 3 | default |
| font | string | "Inter" |
| bgImage | object \| null | null |
| themeId, sharePageThemeId | string \| null | null |
| openingAnimation | "Fade and Grow" \| null | null |
| showStartOverlay / startOverlayButtonText | bool / string | false / "" |
| showFlowNavIndicator | ON \| AUTO \| OFF (legacy bool: true→AUTO, false→OFF) | AUTO (for docs after 2022-10) |
| showBackNextButtons, disableKeyboardNavigation | bool | false |
| showCaptions, showCopyLink, showFullscreen, showReplay, showTranslation | bool | true |
| captionsVisible | bool | — |
| showChapterStyleOnPopout | bool | true for new docs |
| showArcadeButton | bool \| null | null ("Powered by" badge; removable by plan) |
| demoModeByDefault | bool | false |
| keepSoundOffUntilEnabled | bool | false |
| optimizeFlowForMobileView | bool | true |
| mobileLayout | "fit" \| "wide" \| null | null |
| mobileBackground | string \| object \| null | null |
| autoplay | bool \| `{enabled, delay}` | false |
| backgroundMusicUrl / backgroundMusicVolume | string / number | "" / default (≈0.8 in exports) |
| useMagicCursor | bool | false (animated cursor between hotspots; share payload carries `magicCursor.path[{x,y,time,click}]`) |
| watermark | object \| null | null (custom watermark) |
| ogImagePreset | style1..4 \| null | null |
| thumbnailUrl, gifUrl, videoUrl | string | |
| prefs | object \| null | null (per-flow overrides of team prefs) |

## Share page

| Field | Type | Default |
| --- | --- | --- |
| sharePageLayout | `{ type: default\|compact\|arcade-only\|sidebar, showHeader, showLogo, showButton, showDescription, showResources, showCommenting }` | default, all true |
| sharePageLogo, sharePageButton | object \| null | null |
| sharePageFaviconUrl | string \| null | null |
| crawlable | bool | false (SEO indexing of share page) |

## Processing / AI state

`hasUsedAI`, `processedAI`, `processedAIReason`, `ai {}`, `autoSplit { status }`
(video→demo job state: split-pending/completed/failed, hotspots-pending/failed/completed,
text-pending/failed, completed), `clipsReqId`, `clipsRequested`, `useCase`
(promotional / educational / sales / custom), `usedUploadInChunks`, `isMobileRecording`,
`rrwebEventsUrls` (rrweb DOM recording; "DomCapture" feature), `urlToDemoKind`,
`claimToken` (anonymous creation then claim), `experiments`, `experimentsConfig`, `firstViewed`.

## Team defaults (decompiled `defaultTeamPrefs`)

```
fontFamily "Inter", bgColor "#2142E7", fgColor "#FFFFFF", wrapper none, cursor default,
showStartOverlay false, showFlowNavIndicator AUTO, showBackNextButtons false,
showCopyLink/showCaptions/showFullscreen/showReplay/showTranslation true,
showChapterStyleOnPopout true, autoplayEnabled false, autoplayDelay null,
backgroundMusicUrl null, backgroundMusicVolume DEFAULT
```

## Write API (decompiled zod schemas)

- **Create** `POST /api/flows`: strict object, all presentation fields optional; required
  `name, description, schemaVersion, aspectRatio, steps, sharePageLayout, folderId, teamId`;
  optional `id`, `createdWith`, `uploadId`, `capturedEvents`.
- **Edit** `PATCH /api/flows/{id}`: `{ set: Partial<Flow>, unset: FieldName[] }`. A field
  cannot be in both. `name, description, schemaVersion, aspectRatio, steps, sharePageLayout,
  folderId` cannot be unset. Response `{ modified }`.
- Error codes: `flow-exists`, `flow-deleted`, `flow-too-large` (document size cap; inferred
  Firestore 1 MiB limit → keep screenshots out of the doc, URLs only).
- Bulk ops take `flowIDs` (1..30): set-status, set-unlocked, tag/untag, request-approval, approve.

## Observed in a signed-in session (observed-network)

See arcade-analysis/observed-network.md §3–4. Key confirmations and corrections:
- Reads use a **Firestore realtime listener** on `flows/{id}`. There is no REST GET.
  Writes use REST `PATCH {set, unset}`, and every edit sends the whole `steps` array. The
  response is `{modified}`.
- Create body = presentation defaults with `steps: []`, `schemaVersion:"1.1.0"`,
  `createdWith:"arcade-web"`, `font:"Inter"`, `flowWrapper:1`, `customCursor:1`,
  `showFlowNavIndicator:"AUTO"`, `sharePageLayout.type:"default"`. The response is `{id}` (201).
- A new flow has `status` 1. Publish = `POST /api/flows/set-status {flowIDs, status:2}`,
  then `GET /api/revalidate?id&variant` refreshes the share page.
- The stored doc has ~19 fields the pass-1 table lacked (`ai`, `experiments`,
  `experimentsConfig`, `hasComments`, `hasUsedAI`, `processedAI(Reason)`, `clipsReqId`,
  `clipsRequested`, `usedUploadInChunks`, `rrwebEventsUrls`, `claimToken`,
  `urlToDemoKind`, `themeIdMismatchConfirmed`, `firstViewed`, `lastModifiedBy`, …). They
  are now in flow.schema.json. The schema validates the 4 observed private snapshots and
  the 3 public-data flows with zero errors.
- `titleSource`, `captionsVisible`, `capturedEvents` and `videoTimestampWindows` are absent
  on a web-created flow. Only capture/AI paths write them.
- Dates: Firestore timestamp ↔ SSR `{"__arcadeIsoDate": iso}` ↔ REST ISO string.
- Subcollections observed: `flows/{id}/translations/{lang}`, `flows/{id}/stepGenerations`.

Our build: keep this shape; store as JSONB; enforce a size cap; reject data: URLs in
saved docs (the capture builder emits data: URLs only before upload).
