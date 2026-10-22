# Feature inventory

Plan column from Arcade's interactive-demo pricing/help (static-help, May 2026 plans:
Free / Growth $50 per seat / Enterprise; legacy Pro and pre-May Growth are grandfathered).
Priority is ours: **P0** MVP, **P1** next, **P2** later, **—** out of scope.

| Area | Feature | Arcade plan | Evidence | Spec | Priority |
| --- | --- | --- | --- | --- | --- |
| Capture | Chrome extension Demo recording (click → screenshot + hotspot) | Free | decompiled | capture/recording-session.md | P0 |
| Capture | Screenshot (single image) | Free | decompiled | capture/recording-session.md | P0 |
| Capture | Video recording (tab + mic) | Free | decompiled | capture/video-recording.md | P1 |
| Capture | Interesting events → auto video clips (scroll/typing/drag/pauses) | Free | decompiled | capture/step-builder.md | P0 |
| Capture | Camera bubble / face recording | Free (flag FaceBubble) | decompiled (fields), static-bundle | model/steps.md | P2 |
| Capture | HTML capture (cleaned DOM per click) | Enterprise | decompiled | capture/html-capture.md | P2 |
| Capture | Page editor (edit live text before capture) | flag Page Editor | static-bundle | arcade-analysis/extension.md | P2 |
| Capture | Selective click capture (CapsLock), pause/resume, cancel, shortcuts | Free | decompiled | capture/click-and-event-capture.md | P0 |
| Capture | Typo correction in typing clips | server flag | decompiled | capture/click-and-event-capture.md | P2 |
| Capture | Desktop app capture | Free | static-bundle; binary not analysed | capture/desktop-capture.md | — |
| Capture | Upload video/images → demo; Figma import | Free | static-bundle (routes) | editor/overview.md | P1 / — |
| Editor | Hotspots (pulsating/area), callouts (arrow/no arrow, shape), colours | Free | decompiled, observed | model/hotspots-and-callouts.md | P0 |
| Editor | Overlays: chapter / start / final, buttons | Free | decompiled, observed | model/overlays-branching-forms.md | P0 |
| Editor | Branching (hotspot/button/video targets), branching map | Growth | decompiled, static-help | model/overlays-branching-forms.md | P1 |
| Editor | Forms in overlays, embeds (HubSpot/Calendly/…), CTAs | Growth | decompiled, static-help | model/overlays-branching-forms.md | P1 |
| Editor | Pan & zoom (image + timed video zooms) | plan-limit `panAndZoom` | decompiled | model/pan-zoom-and-image-edits.md | P1 |
| Editor | Blur/redact, crop | plan-limit `imageEditor` | decompiled | model/pan-zoom-and-image-edits.md | P1 |
| Editor | Video trim / split | plan-limit `trimVideo`, `splitVideo` | decompiled | model/steps.md | P1 |
| Editor | Custom variables `{{name}}` | flag Custom Variables | decompiled | model/variables-translations-voice.md | P1 |
| Editor | Menu / chapters nav, resources | plan-limit `menu` | observed, decompiled | model/overlays-branching-forms.md | P2 |
| Editor | Themes, wrapper, custom cursor, fonts, branding, custom watermark | Growth (branding) | decompiled | model/flow-model.md | P1 |
| Editor | Background music | flag | decompiled | model/flow-model.md | P2 |
| Editor | Magic cursor (animated cursor path) | flag | observed | model/flow-model.md | P2 |
| Editor | Comments (Liveblocks), share-page comments | flag Commenting | static-bundle | editor/overview.md | P2 |
| Editor | Version history | Enterprise | decompiled | editor/overview.md | P2 |
| Editor | Access control per flow, approval workflow, RBAC | Enterprise (RBAC) | decompiled | editor/overview.md | P2 |
| AI | AI hotspot copy, titles ("Avery"), tones | Free (credits) | decompiled | editor/ai-features.md | P1 |
| AI | AI voiceover (ElevenLabs/Google), captions, pronunciation | Free | decompiled, observed | model/variables-translations-voice.md | P1 |
| AI | AI translations | Growth | decompiled, static-help | model/variables-translations-voice.md | P2 |
| AI | Video → interactive demo (smart split) | flag Video to Arcade | decompiled | editor/ai-features.md | P2 |
| AI | Flow → AI video, prompt video, visuals | separate AI-video subscription | static-bundle, static-help | editor/ai-features.md | — |
| Player | Responsive stage, hotspot animation, navigation, keyboard, progress bar | Free | decompiled | player/runtime.md | P0 |
| Player | Autoplay, demo mode, start overlay | Free | decompiled | player/runtime.md | P1 |
| Player | Translations picker, captions, sound | per features | decompiled | player/runtime.md | P1 |
| Share | Public share page + layouts, OG image presets | Free (1 published demo) | observed, decompiled | player/embed-and-share.md | P0 |
| Share | Iframe embed (inline/tab/modal, pop-out) | Free | decompiled | player/embed-and-share.md | P0 |
| Share | Web component embed | flag | observed | player/embed-and-share.md | P1 |
| Share | Private share, secure mode | workspace setting | static-bundle | player/embed-and-share.md | P2 |
| Share | Custom links (password/email/expiration) | Enterprise | static-bundle | player/embed-and-share.md | P2 |
| Share | Collections | Enterprise | static-bundle | player/embed-and-share.md | P2 |
| Share | Custom domain, offline access | Enterprise | static-bundle, static-help | player/embed-and-share.md | — |
| Share | Step-by-step guide view | flag | static-bundle | player/embed-and-share.md | P2 |
| Export | GIF / MP4 export (fps, size, captions, language) | Growth | decompiled, static-help | editor/exports.md | P2 |
| Analytics | Viewer events + host postMessage | Free (basic) | decompiled | player/analytics-events.md | P0 (events), P1 (dashboards) |
| Analytics | Advanced insights (per-step, branch), export, leads, Audience Reveal | Growth / Enterprise | static-help, static-bundle | player/analytics-events.md | P2 |
| Integrations | HubSpot, Salesforce, Segment/Amplitude/Mixpanel/PostHog/GTM/Intercom, webhooks, API keys, MCP | Growth (+Salesforce Enterprise) | static-bundle, static-help | api-notes.md | P2 |

Plan-limit keys tracked as `<key>_limit_hit_at` / `meteringUsage.<key>` (decompiled):
panAndZoom, forms, translations, imageEditor, branching, trimVideo, menu, watermark,
exportToGIF, exportToVideo, collections, splitVideo, videoGeneration, customLinks.
See [arcade-analysis/plans-and-gating.md](arcade-analysis/plans-and-gating.md).
