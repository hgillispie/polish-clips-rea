# Viewer analytics

Evidence: **decompiled** (tracker class + call sites in the standalone runtime; host
event publisher in share page bundle), **static-bundle** (ingest URL), **observed-network**
(signed-in HAR; see arcade-analysis/observed-network.md §6).

## Transport

```
Tracker(pageName = "Viewer", pageProperties = {flowId, flowName, sessionId?, …}, utmParams,
        {webComponent?, shouldPublishToHost, shouldAnonymizeIP, doNotTrack})
  init: unless doNotTrack (flow/team flag, window._doNotTrack) → Segment-compatible client with
        apiHost = first-party ingest (t.<domain>/api/ingest), writeKey "" , cookies SameSite=None
        browser DNT=1 → no client persistence
        anonymizeIP → context.ip = "0.0.0.0"   ("DisableIPTracking")
  page(): analytics.page("Viewer", props); if publishing to host: publish("Flow Rendered")
  report(name, props): analytics.track(name, {...pageProperties, ...props, name: pageName})
                       if shouldPublishToHost: publish(name, props)
  identifyViewer({userId, email, accountId, companyName}): identify; rotate sessionId if the
        known person changes; also window.__arcadeTracker?.identify(...)
```

Publish to host (flag "Publish Events to Host"):
```
publish(page, name, pageProps, utm, props):
  evt = { eventName: name, eventSource: "Arcade", eventHostname, eventPathname,
          eventTimestamp: ISO, ...utm, ...pick(pageProps, schema[name].pageProperties),
          ...pick(props, schema[name].eventProperties) }
  window.parent.postMessage(evt, "*"); window.__arcadeTracker?.track(name, evt)
  if (name == "Overlay Clicked" and evt.isCta) or name in
     {"Powered by Arcade Button Clicked", "External Url Clicked", "Form Answered"}:
       repost as { ...evt, eventName: "CTA Clicked", eventType: name }
```
Host integrations configured per team (`integrations` in share props: amplitude, intercom,
mixpanel, posthog, segment, GTM, hubspot) consume these on the host page.

## Event catalogue (viewer)

| Event | Properties (beyond flowId, flowName) |
| --- | --- |
| Flow Rendered | — |
| Step Reached | stepId, fromStepId, isInitialStep, isFinalStep, fromStepActiveTimeMs, totalActiveTimeMs, firstViewed?, customLinkFirstViewed?, wasManuallyPlayed? |
| Hotspot Clicked | stepId, hotspotId, hotspotLabel, targetStepId |
| Overlay Clicked | stepId, title, subtitle, buttonLabel, buttonId, linkType (button\|link), linkUrl, isCta, isEmbed?, embedSource? |
| CTA Clicked | stepId, ctaLabel (+ eventType when re-emitted) |
| External Url Clicked | stepId, linkUrl, source |
| Form Answered | (form step + answers summary; not fully recovered) |
| Video Ended | stepId |
| Flow Restarted | — |
| Progress Bar Nav Clicked | fromStepId, toStepId |
| Start Overlay Rendered / Dismissed | — |
| Copy Share Link Clicked, Fullscreen Mode Toggled, Caption Toggled, Sound Toggled, Sound Unlock Rejected, Demo Mode Toggle | toggle state |
| Logo Clicked, Powered by Arcade Button Clicked, Custom Share Page Button Clicked | — |
| Frame Visibility, Page Unloaded | visibility / active time |
| Paywall Displayed / Button Clicked / continue clicked | — |
| Navigated With Arrow Right/Left Key | (navigation source labels) |

Editor/share-page-only events also seen: Comment Added/Deleted, Thread Deleted,
Resource Added/Edited/Deleted, Notification settings changed, Color Picker *.
App lifecycle events forwarded to HubSpot: Flow Created, Flow Published, Flow Unpublished,
Flow First Viewed, Embed Code Copied, Embed Added, Custom Link Created, Form Answered, …

## Insights (author side)

Routes: `/api/insights/aggregated/{flowId}`, `/api/insights/overviewPlays/{flowId}`,
`/api/insights/companiesForLeads/{flowId}`, workspace insights page, "Export All Insights",
"Analytics 3.0". Per-step drop-off and branch tracking are Growth (static-help). Leads:
`/api/leads/subscribe|unsubscribe` (email digests), Audience Reveal via Clearbit
(`/api/clearbit/toggle`) resolves viewer IP → company. Response shapes **not recovered**.

Observed-network (Free workspace, unpublished→published demo with no real views): the
team and flow insights pages loaded with **no** `/api/insights/*` request and no
insights Firestore listener, and showed sample data. On this plan/state the sample
dataset is client-side. Page props are `{teamId, timezone}` (team) and
`{flowSSR, timezone, _serializableTranslations, …}` (flow). Real response shapes still
need a demo with views or a Growth trial.

Ingest transport confirmed (observed-network): `POST t.arcade.show/api/ingest/{t,p,i}`,
`text/plain` JSON from analytics.js. Each is a single event, not a batch. Envelope
`{type, event|name, properties, context{page{path, referrer, search, title, url},
userAgent, userAgentData, locale, library, timezone}, messageId, anonymousId, userId,
timestamp, sentAt, _metadata}`. Viewer `Step Reached` properties observed:
`flowId, flowName, flowGroup, sessionId, stepId, fromStepId, isInitialStep, isFinalStep,
fromStepActiveTimeMs, totalActiveTimeMs, pageWidth, pageHeight, customLinkId,
hasCustomValues, language, flowHasTranslation, productExperience`.

Our build: implement our own ingest (`POST /api/events` batch) with the same event names
so dashboards and host integrations are compatible in spirit; compute insights by
aggregating Step Reached / Hotspot Clicked per session.
