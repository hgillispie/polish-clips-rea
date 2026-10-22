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

## How gating is implemented (decompiled / observed)

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

For our build: a single `entitlements(workspace)` function returning the same kinds of
answers (bool features + numeric limits + counters), checked server-side on every write
and mirrored client-side for UI.
