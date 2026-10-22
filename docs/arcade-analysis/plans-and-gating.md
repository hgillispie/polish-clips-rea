# Plans, credits and feature gating

## Plans (static-help, Arcade KB + pricing page, retrieved 2026-10-22)

| Plan | Price | Interactive-demo highlights |
| --- | --- | --- |
| Free | $0 | Unlimited AI demos, 1 published demo, unlimited views, record anywhere, Arcade MCP, AI voiceover, AI creation (Avery), 200 AI credits/mo |
| Growth | $50/seat/mo ($42.50 yearly), ≤10 seats | + integrations, demo branching, CTAs and forms, advanced insights, custom branding & landing page, custom watermark, shared workspace, AI translations, MP4 & GIF exports, 1 brand kit, 800 credits/mo |
| Enterprise | custom | + RBAC, multiple teams, HTML capture, custom share links, collections, offline access, version history, SSO, custom domains, up to 10 brand kits, Salesforce, 100k credits/yr |
| Pro (grandfathered) | $38/mo | unlimited demos, basic insights, video editing, GIF/MP4, no watermark, 500 credits |

AI-video product is a separate subscription (Free / Pro $49–59 / Enterprise) with its
own credits per generated video. Out of scope for the demo builder.

## How gating is implemented (decompiled / observed / observed-network)

1. **Feature map per workspace** — the share payload carries `features: { "<Feature Name>": bool|number }`
   (109 keys on a sampled flow). The UI checks names like "Pan and Zoom", "FlowForm",
   "Choose Your Own Adventure", "Custom Variables", "Synthetic Voice", "Custom Share Links",
   "DomCapture", "Versioning", "Web Component Embeds", "Publish Events to Host", "Do Not Track",
   "Offline Mode", "Remotion Export", "Paywall Arcade Limit" …
2. **Metering** — per-user/workspace counters `meteringUsage.<key>` updated in a DB
   transaction; reaching the limit stamps `meteringLimitHit.<key>`; failed jobs roll back.
   Free-plan "first use free, then paywall" behaviour (`useOfferGrowthTrialInsteadOfMetering`).
3. **Extension flags in storage** — `mayUseDirectUpload`, `mayUseTypoCorrection`, `mayNotRecord`.
4. **Team feature flags** (admin can toggle via `/api/admin/{teams|users|workspaces}/{id}/flags {features}`):
   NoArcadeBranding, PublishEventsToHost, DisableIPTracking, DoNotTrack, DefaultShareType,
   PaywallArcadeLimit, FlowInsights, DesignLock, AutoHotspotText, Collections, CustomCodeScenes,
   VoiceModelSelection, Analytics30, AiModelProvider, ImagesInCallouts, VideoProduct, WebComponentEmbeds…
5. **Credits** — AI calls return HTTP 402 when out of credits; billing summary and
   credit-usage endpoints back the UI.

## Observed in a Free workspace (observed-network)

- `workspaces/{id}.freePlanType = "singleFlow"` and `subscriptions: []`. Billing page props:
  `currPlan:"Free"`, `interval:""`, `currInvoiceTotal:""`, `aiCredits{availableCredits:250, totalCredits:250}`,
  `_totalNumberOfCredits:250`.
- Price table served to the billing page (USD): `proMonthly 38`, `proAnnual 388`,
  `growthMonthly 50`, `growthAnnual 510`, legacy growth five-seat `{basePrice 350,
  unitAmount 150, unitAmountStartsAt 6}` monthly / `{3570, 1530, 6}` annual,
  `aiCreditsPack 0.12`.
- **Metering in action**: on Free, using the image editor, step pan-and-zoom and AI
  translation each fired `Paywall Displayed {paywallSource: "metering-image-editor" |
  "metering-pan-and-zoom" | "metering-translations"}`. "Paywall continue clicked" then let
  the action proceed. The client wrote `users/{uid}.meteringUsage.panAndZoom` with a
  Firestore update and a server-timestamp `modified`. Collections showed
  `paywallSource:"Collection"` (hard paywall on Free).
- The plan limit for published demos uses a listener on `flows` where
  `status, teamId, unlocked` (`unlocked` marks the flow allowed under `singleFlow`).
- Workspace `features` on Free has 4 keys only (`Disable IP Tracking`, `Workspace
  Auto-Join`, `Publish Events to Host`, `Do Not Track`), and team `features` is `{}`. The
  109-key map in share payloads is therefore the *resolved* entitlement set, computed
  server-side from plan + overrides (inferred from the difference).
- Rollout/experiment flags come from PostHog (`t.arcade.show/ingest/flags/`, 43 keys),
  e.g. `limited-free-plan-vs-the-old-plan`, `metering-features`, `growth-trial-vs-metering`,
  `annual-pricing-first`, `pro-experiment-50-off`, `unlimited-brand-kits`. Pages get a
  per-page subset as `_featureFlags`.

For our build: a single `entitlements(workspace)` function returning the same kinds of
answers (bool features + numeric limits + counters), checked server-side on every write
and mirrored client-side for UI.
