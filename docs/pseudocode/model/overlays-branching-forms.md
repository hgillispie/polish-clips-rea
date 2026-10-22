# Overlays, chapters, branching, forms, menu

Evidence: **decompiled** (step helpers, player navigation hook, viewer form submit),
**observed** (overlay step keys), **static-help** (plan gating).

## Overlay kinds

`OverlayType` Start 0 | Chapter 1 | Final 2 is the role of an overlay card:
- **Start overlay**: flow-level (`showStartOverlay`, `startOverlayButtonText`); shown over the
  first step until the viewer clicks; reports `Start Overlay Rendered` / `Start Overlay Dismissed`.
- **Chapter**: an Overlay step placed between steps (title, subtitle, buttons, blurred preview of
  another step). `showChapterStyleOnPopout` keeps chapter styling in pop-out embeds.
- **Final**: the last overlay (CTA card: "Book a demo", "Restart"). The CTA-ness of a click is
  `isCta = (url button) or (on last step)`.

`variant`: `buttons` (default) | `form` | `embeds` (third-party form/calendar embed code;
the player tags the source as HubSpot, Calendly, Typeform, Marketo or Other by URL sniffing).
Plan flag "Allow More than Five Buttons in Overlays" implies a default cap of 5 buttons.

## Paths (buttons)

```
Path {
  id
  buttonText, buttonColor?, buttonTextColor?
  pathType: "step" | "url" | "crossFlow" | "input"      # "input" = form field (below)
  targetStepId?        # step
  url?, openInTheSameTab?                               # url
  targetFlowId?, targetStepId?                          # crossFlow (jump into another demo)
}
```

## Branching ("Choose Your Own Adventure")

Any of these can point to a step id:
`hotspot.targetId`, `videoStep.targetId` (on end), `mobileButton.targetId`,
`overlay.paths[pathType=step].targetStepId`.

```
nextTargets(step) = ids from the list above (in that step), deduped

navigateFrom(step, clicked?):
  if clicked has a target id and that step exists and is not Empty: go there
  else: go to next non-empty step in array order

autoNext(steps, step, {allowRestart, blockedAutoTransitions, forwardOnly}):
  # used by autoplay / video-end / "Next" button
  fallback = next non-empty step (wrapping if allowRestart)
  candidates = nextTargets(step) sorted by their index in steps (missing target → fallback's index)
  for c in candidates:
     s = (c ? step with id c : fallback)
     if s and s != step and "step.id-s.id" not in blockedAutoTransitions
          and (!forwardOnly or index(s) > index(step)): return s
  return fallback
```

`blockedAutoTransitions` prevents autoplay loops (A→B→A). The editor's "Branching Map"
(flag) visualises this graph. Gated: Growth+ ("Demo branching", static-help;
plan-limit key `branching`).

## Back navigation

The player keeps a navigation stack. Back pops the stack if non-empty (branch-aware),
else goes to the previous non-empty step. Arrow keys ← / → map to prev/next unless
`disableKeyboardNavigation`. (decompiled)

## Forms (overlay variant `form`)

```
FormField (Path with pathType "input") {
  id, fieldLabel, buttonText (placeholder / option label), required,
  variant: "text" | "email" | "single-select" | "multi-select" | "hidden" | …
}
# options of a select are sibling inputs sharing the same fieldLabel and variant
# "hidden" fields carry a fixed value in buttonText (UTM / campaign tagging)
# submit button = a Path with pathType step|url after the inputs
```

Navigation is blocked from a form step with required inputs until it has been submitted
(`bypassFormValidation` is used only for explicit button navigation after submit).

Submit (viewer, unauthenticated):
```
POST /api/viewer/form {
  isPreview, sessionId, anonymousId, viewerIp: null if doNotTrack,
  createdBy: viewer user id | "anonymous",
  teamId, flowId, flowName, flowCreatedBy,
  stepTitle, stepSubtitle (markdown stripped),
  answers: { [fieldLabel]: { variant, value } },     # includes hidden fields
  ...utmParams }
→ 200 | 400 {error}
```
After success: toast, mark step answered, emit `Form Answered` (re-emitted to host as
`CTA Clicked` with `eventType`), and if an email field exists and tracking is allowed,
identify the viewer (feeds Leads / CRM sync). Plan gate: Growth+ ("Demo CTAs and forms").

## Menu and resources

`flow.menu.entries[{id,label,targetId}]` renders a chapter menu that jumps to steps
(plan-limit key `menu`). `flow.resources[{id,type:file|link,label,url}]` render on the
share page (`Resource Added/Edited/Deleted` editor events).
