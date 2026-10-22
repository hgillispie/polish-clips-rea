# Click and event capture (content script, all frames)

Evidence: **decompiled** (recording-manager bundle, background merge logic).

## Listeners (capture phase, added on AddEventListeners)

| DOM event | Produces |
| --- | --- |
| `pointerdown` | starts a potential click/drag; remembers position + target |
| `pointermove` while button down | `arcade-drag-event` samples |
| `pointerup` | `arcade-click-event` (if not a drag) |
| `scroll`, `wheel` | `arcade-scroll-event` |
| `keypress` | `arcade-keypress-event` |
| `input` | `arcade-input-event` (value + target selector) |
| window move/resize | `arcade-frame-info-report` when geometry changes |

Rules:
- Ignore a click within 500 ms of the previous one (dedupe double fires).
- If `selectiveClickCapture` is on and CapsLock is active, do not record the click (lets the author click "off camera").

## Click message

```
ClickEvent {
  type: "click"
  clickId: uuid
  tabId, frameId
  frameX: clientX, frameY: clientY      # CSS px inside the frame
  timeMs: Date.now()
  pageContext: { url, title, description (meta description/og), width: innerWidth,
                 height: innerHeight, language (html[lang] or meta[name=language]) }
  clickContext: {
    cssSelector                         # see below
    text: innerText of target, ≤ 300 chars
    elementType: "button" | "link" | "image" | "input" | "select" | "other"
    sections: up to 10 section heading texts (H1–H6) found walking up from the target (last 10 kept), each ≤ 200 chars
    originalRect: {x,y,width,height}    # rect of nearest BUTTON/A/IMG/SVG/INPUT/TEXTAREA/SELECT ancestor
  }
  links?: [ {href, rect} ]              # visible <a> rects, only if autoLink
  html?: CleanHtml                      # only if captureHTML (html-capture.md)
}
```

`cssSelector(el)`: walk from the element up to the root. For each node emit
`tag[id="…"]` and stop if it has an id, else `tag:nth-of-type(n)`. Join with
` > `. (Our version should escape ids and cap depth.)

The click context feeds AI hotspot copy (`/api/extension/image` with `useAI`)
and the editor's "AI hotspots" feature.

## Frame geometry

Each frame reports `frameScreenX = screenX - clientX`, `frameScreenY = screenY - clientY`
(i.e. the frame's viewport origin in screen coordinates), plus `innerWidth/innerHeight`.
The top frame's numbers become the tab geometry. See [hotspot-coordinates.md](hotspot-coordinates.md).

## "Interesting" events (merged in background)

```
toInteresting(evt):
  drag   → {type:"dragging",  startTimeMs, endTimeMs}
  scroll → {type:"scrolling", startTimeMs, endTimeMs}
  input  → {type:"typing",    startTimeMs, endTimeMs, typedText, targetSelector}
  media  → {type:"media", camera:bool, audio:bool}       # mic/camera on during recording

merge(list):  consecutive events of the same type extend the previous one's endTimeMs.
```

Typo correction (only if server flag `mayUseTypoCorrection`): for a typing
event, diff the typed sequence against the final input value (diff-match-patch
style) and rewrite `typedText` so the replayed typing has no backspaces.
(decompiled; exact rewrite policy is ours to define.)

## Should we upload the video at all?

```
needsVideo(events, windows, settings):
  if not settings.recordInterestingEventsAsVideos: return true   # captureFullVideo path decides elsewhere
  if settings.selectiveClickCapture: return true
  if any event.type != "click": return true
  clicks = map each click time through windows to recording time
  return any gap between consecutive clicks (or start/end) ≥ 3000 ms
```

If false, skip the video upload entirely (screenshots only).
