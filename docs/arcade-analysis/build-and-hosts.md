# Web build, routes and player runtime

Tag: **static-bundle** / **observed** unless noted.

## Build

- Next.js pages router compiled with Turbopack. Build id `build-TfctsWXpff2fKS` at time of capture (2026-10-22). 3,095 JS/CSS chunks (~83 MB) downloaded locally from `_buildManifest.js`.
- Turbopack registers named exports as string lists, so export names survive minification (968 distinct export names recovered). This is why model helpers like `getFlowFromDoc`, `parseExtensionCapture`, `getEmbedCode` are identifiable.

## Route groups (from `_buildManifest.js`)

| Group | Examples |
| --- | --- |
| Flow editing | `/flows/[pid]/edit`, `/flows/[pid]/insights`, `/flows/[pid]/guide`, `/flows/[pid]/video`, `/flows/[pid]/version/[versionId]`, `/flows/[pid]/view` |
| Share | `/share/[pid]`, `/share/[pid]/[customLinkId]`, `/share/[pid]/guide`, `/share/[pid]/offline` |
| Upload | `/upload/flow`, `/upload/media`, `/upload/[id]/flow`, `/upload/figma/[uploadId]`, `/upload/desktop/[uploadInfo]` |
| Collections | `/collections/...` |
| Auth | `/auth`, `/auth/desktop/[authId]`, `/auth/figma/[authId]` |
| Integrations | `/integrations/hubspot/...`, `/integrations/sfdc/...` |
| Workspace | `/workspaces/[slug]/brand-kits`, `/connectors`, `/insights`, `/leads`, `/settings/themes`, `/start-with-ai/video`, `/start-with-ai/visuals`, `/memory`, `/impact-analysis` |
| AI video product | `/prompt-videos/...`, `/visual-projects/...`, `/videos/[id]` |
| Admin | many `/admin/...` |

## Player runtime (standalone)

- `demo.<domain>/embed/v1/loader.js` defines a custom element (`arcade-demo`, attributes `flow-id`, `start-step`). It waits until the element is within ~1250 px of the viewport (IntersectionObserver), fetches `embed/v1/flows/<id>` with `credentials: "omit"` (404 → unavailable), then dynamic-imports `runtime-<hash>.js` chosen by the payload's `rendererRevision`, verified with SRI, and calls `mountEmbed({host, container, payload, startStep, onReady, onStepChange, onComplete, onError, onNavigate})`.
- Host-page DOM events: `arcade-ready`, `arcade-step-change`, `arcade-complete`, `arcade-error` (reason `unavailable` | `network` | `runtime`).
- Embed payload keys (observed): `firstImage`, `fontStylesheetUrl`, `frameStyle`, `projection` (the flow), `rendererRevision`, `stepRedirects`.
- The main runtime chunk (`initial-*.js`, 2.7 MB) was Wakaru-decompiled locally (158k lines). It contains the same viewer components as the share page plus the tracker. **decompiled**.

## Public share page data (observed)

`/_next/data/<build>/share/<flowId>.json` → `pageProps` with:
`_serializablePublicFlow` (Flow), `_serializableTranslations`, `features`
(the owning plan's feature map), `integrations` (amplitude, intercom, mixpanel,
posthog, segment, GTM, hubspot toggles), `magicCursor`, `videoCursorPaths`,
`watermarkCustomProps`, `workspaceCustomFonts`, `themeColors`, `demoBaseUrl`,
`appBaseUrl`, `customDomain`. Two public demos were sampled for key shapes only.
