# AI features ("Avery")

Evidence: **decompiled** / **static-bundle** call sites; server prompts are NOT
recovered (and must not be). Credits: Free 200/mo, Growth 800/mo, Enterprise 100k/yr
(static-help). HTTP 402 = out of credits (decompiled). Observed Free workspace: `aiCredits/{workspaceId} {scope:"workspace", creditsRemaining, reservedCredits}` read by a Firestore listener. Billing page props show `aiCredits{availableCredits:250, totalCredits:250}` (observed-network), so the current Free grant is 250, not the KB's 200.

| Feature | Trigger | API | Result |
| --- | --- | --- | --- |
| Record with AI | extension `useAvery` | `/api/extension/demo-start {useAI}`, `/api/extension/image {useAI, pageContext, rectContext, x, y}`, `/api/extension/demo-end {useAI, tone}` | Server writes hotspot labels, flow title/description (`titleSource:"ai"`, `processedAI`). AI only if ≤ 50 clicks. |
| Auto hotspot text | editor panel | `POST /api/ai/flow-hotspots {useCase/tone/options…, message?, flowId, promptId?}` | `{hotspots:[{id,label}], promptId}`; refine chain by promptId. |
| Ask AI on a text field | sparkle menu | `POST /api/arcade-ai {value, context, action, tone}` | `{message:"ok", suggestion}`; suggestion may be wrapped in `<hotspot>…</hotspot>`. Actions: rewrite/shorten/… by use case. |
| Video → interactive demo ("smart split") | on a Video step | `POST /api/ai/smart-split {flowId, stepId}` | async; `flow.autoSplit.status` goes split-pending → hotspots-pending → text-pending → completed (or *-failed). Steps replaced. |
| AI hotspots on a video | | `POST /api/ai/add-hotspots {flowId, videoAssetId}` | same status machine from text-pending. |
| Generate element (HTML capture) | page/HTML step | `POST /api/ai/generate-element {html, pageUrl, prompt}` | new HTML element (DomCapture AI). |
| Translations | language menu | `POST /api/flows/{id}/translations/generate {language, mode:"missing"}` → **202** `{message, started, translation{createdAt, updatedAt, generationStatus{runId, status:"queued", total/completed/failedVoiceovers, startedAt, updatedAt}, strings{name, description, steps{}}}}` (observed-network) | Per-language doc `flows/{id}/translations/{lang}` reaches `status:"completed"` with `finishedAt`, and the editor listener picks it up (observed-network). Free plan: `Paywall Displayed {paywallSource:"metering-translations"}`, then "continue" allows a metered use. |
| Voiceover | step / apply-all | `POST /api/synthetic-voice` | `{url, timepoints, duration}`. Voice list `GET /api/synthetic-voice` → `{voices[{id, name, accent, avatarUrl, isBuiltIn, isDefault, previewUrl, description, provider, languages[], models[], voice{key, variant, provider, model, languageCode}}], isCustomApiKey}` (observed-network). |
| Flow → AI video | "Create video" | `POST /api/ai/flow-video-generation {flowId, fps:60, sizeConstraint:1920, brandKitId}` → `{videoGenerationId}`; then `POST /api/flows/{id}/video-generation/{generationId} {generate, backgroundMusicUrl, backgroundMusicVolume(.8), voiceModel:"eleven_v3", voiceKey, font, companyLogo, introSequence, outroSequence, sections[{id,title,…,voiceover{script},fontColor,backgroundColor}]}` | AI-video product (separate subscription). |
| Prompt-video import into a flow step | | `POST /api/flows/{id}/step-generations/prompt-video-import`, retry `…/step-generations/{gid}/retry` | operation `{status: queued|running|finalizing|succeeded|failed|cancelled, result{url, streamUrl, duration, size, assetId}}` |
| Visual copy | visuals | `POST /api/ai/flow-visual-copy-generation {brandKitId, tone, flowId, promptText, type, templates}` | `{copyByTemplate}` |

Model choice exists (`AiModelProvider` openai|claude; WIZARD light/medium/high) but is a
server concern. For our build: one `/api/ai/*` service with a provider abstraction, jobs
tracked on the flow doc (`autoSplit`-style status field) and a credit ledger.
