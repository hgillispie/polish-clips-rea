# Player runtime

Evidence: **decompiled** (standalone runtime chunk + share page modules), **observed**
(embed payload, loader), **inferred** where marked.

## Mount

```
mountEmbed({ host, container, payload, startStep, onReady, onStepChange, onComplete, onError, onNavigate })
payload = { projection: Flow (public subset), translations?, firstImage, fontStylesheetUrl,
            frameStyle, rendererRevision, stepRedirects }
```
The same component tree renders in three hosts: share page (`/share/:id`), iframe embed
(`/share/:id?embed…`, chrome-less), and the web component (shadow-root-free container).
`stepRedirects` remaps deleted step ids for deep links (inferred from name).

## Stage sizing

- Stage aspect = `flow.aspectRatio` (h/w) or computed from the widest step (`getDimensionsFromMaxStepWidth`).
- `flowWrapper` adds browser chrome (light/dark) or a phone frame; 41 px is reserved for
  the browser bar / caption row in embed snippets.
- Media is drawn to fit the stage (`coverAndFit`); hotspots are positioned in normalized
  coordinates, so they track any size. (inferred from coordinates model)
- Mobile: if the viewport is narrow and `optimizeFlowForMobileView`, layout switches to
  `MOBILE_INLINE` / `MOBILE_EXPANDED` (tap to expand) per `ViewerLayout`; `mobileLayout` fit|wide.

## Step lifecycle

```
enter(step):
  preload next targets' media (images + first video segment)            # inferred
  if Image: show image; run pan-zoom if enabled; animate hotspots → callouts(arrow) → callouts(no arrow)
  if Video: play HLS segment [startFrac, endFrac]×duration at playbackRate, muted unless sound unlocked;
            apply videoPanAndZooms; on end → `Video Ended`, then autoNext() or targetId
  if Overlay: render card (buttons / form / embed) over blurred preview image
  start voiceover audio if syntheticVoice.enabled and sound on; captions from timepoints
  report `Step Reached { stepId, fromStepId, isInitialStep, isFinalStep,
                         fromStepActiveTimeMs, totalActiveTimeMs, firstViewed?, customLinkFirstViewed?, wasManuallyPlayed? }`
  onStepChange(step.id)
```
Active time counts only while the tab is visible and the frame is in view
(`Frame Visibility` event, IntersectionObserver). (decompiled names; inferred mechanics)

## Navigation

- Hotspot click / overlay button / mobile button → see [../model/overlays-branching-forms.md](../model/overlays-branching-forms.md).
- Keyboard: ArrowRight next, ArrowLeft back (stack-aware) unless `disableKeyboardNavigation`.
- Progress bar (`showFlowNavIndicator` ON/AUTO/OFF): clicking a segment jumps (`Progress Bar Nav Clicked {fromStepId,toStepId}`).
- Back/Next buttons when `showBackNextButtons`.
- Restart on final step (`showReplay`) → `Flow Restarted`.
- Cross-flow jump loads another flow (collections / linked demos).

## Autoplay

```
stepSupportsAutoplay(step) = Image | Video | (Overlay and variant not in {form, embeds})
shouldAutoAdvance(step) = flow.autoplay.enabled
                          or (step is media without hotspots)          # default on
delayFor(step) = flow.autoplay.delay ?? max(voiceover duration, textReadTime(step))
textReadTime(chars) = 1000 * max(DEFAULT_WAIT * chars * 0.03, DEFAULT_WAIT)
```
Autoplay uses `autoNext()` with `blockedAutoTransitions` to avoid loops. A start overlay
or a paused/hidden frame suspends autoplay. `demoModeByDefault` / "Viewer Demo Mode"
toggles an auto-playing presentation mode (`Demo Mode Toggle`).

## Controls

Copy link (`Copy Share Link Clicked`), fullscreen (`Fullscreen Mode Toggled`),
captions (`Caption Toggled`), sound (`Sound Toggled`, `Sound Unlock Rejected` when the
browser blocks audio), language picker, restart, menu, "Powered by" badge
(`Powered by Arcade Button Clicked`; hidden by plan / NoArcadeBranding), logo
(`Logo Clicked`), watermark.

## Error and unavailable states

Loader error reasons: `unavailable` (404 / unpublished / private), `network`, `runtime`.
Private flows (DefaultShareType private, or custom link protection) render a gate.
Paywall (`Paywall Displayed`, `Paywall Button Clicked`) when the owner's plan limit
(e.g. Free's 1 published demo) is exceeded (`PaywallArcadeLimit` flag).
