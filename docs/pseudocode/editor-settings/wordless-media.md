# Wordless media in the script

## Input / output

```text
input:   script clip (media time range, words with times, gain), media loudness envelope (u16 @ hz)
output:  extra text runs inside the clip's rendered script string, tagged WordlessMedia, drawn as bars
```

## Constants

```text
BAR      = 0.2 s       # one glyph
PAD      = 0.5 s       # left after a word before bars start
MIN_LEAD = 0.2 s       # leading / no-words threshold
MIN_GAP  = 0.7 s       # between-words threshold (PAD + BAR)
GLYPHS   = ["─","━","│","┃","┄","┅"]   # low -> high; drawn by the WordlessMedia font
FLOOR    = 65 / 65535
CEIL     = 0.06 (0.2 for embedded-composition clips)
MAX_GAIN = 4
```

## Spans

```text
function wordless_spans(clip) -> [Span{start, duration, location_in_text, leading}]:
  if clip.is_ai_speech or is_gap_clip(clip): return []
  if clip.words is empty:
    dur = clip.is_cut ? clip.audio.duration : clip.duration
    return dur >= MIN_LEAD ? [Span(clip.offset, dur, location = 0)] : []
  out = []
  first = clip.words[0]
  if first.start - clip.offset >= MIN_LEAD:
    out += Span(clip.offset, first.start - clip.offset, location = text_start(first), leading = true)
  for i, w in clip.words:
    next_start = (i + 1 < len) ? clip.words[i+1].start : clip.offset + clip.duration
    gap = next_start - w.end
    if gap >= MIN_GAP:
      out += Span(w.end + PAD, gap - PAD, location = text_end(w))
  return out
```

## Bars and text

```text
function bars(file, span, gain, embedded) -> [float]:
  n = floor(span.duration / BAR)
  env = file.energies
  if env == null: return file.is_local ? fill(n, -1) : fill(n, 0)   # -1 = still computing
  per = round(BAR * env.hz)
  out = []
  for k in 0..n-1:
    avg = mean(env[(span.start*env.hz) + k*per : + per]) / 65535
    v = avg < FLOOR ? 0 : min(1, avg / (embedded ? 0.2 : 0.06))
    out += v * min(MAX_GAIN, gain) / MAX_GAIN
  return out

function glyphs(values) = join(GLYPHS[min(5, floor(max(v,0) * 6))] for v in values)

function render_clip_text(clip, show_wordless):
  runs = clip.inline_components                        # markers, notes, pins
  if show_wordless and clip.track.is_main:
    for s in wordless_spans(clip):
      t = " " + glyphs(bars(clip.file, s, clip.gain, clip.is_embedded)) + " "
      runs.insert_sorted(TextRun(t, at = s.location_in_text,
                                 attrs = {wordless: {is_blocked: clip.is_cut, computing: any(-1),
                                                     first_of_clip: s is first}}))
  return interleave(clip.text, runs)
```

## Rendering and editing

```text
style wordless run:  font-family WordlessMedia; color secondary
  cut        -> line-through
  computing  -> stepped opacity pulse (3 s) + "Transcribing N%" badge on the first run of the clip
  playhead   -> accent caret

on insert_text(at) inside wordless run:  reject "Writing is not allowed in word gaps."
on correct_transcript(range ∩ wordless): reject "Word gaps cannot be corrected."
on delete/cut(range):                   map run back to its media time span; same as deleting words
on drop(track, at wordless run):        pin to the span's start time ("ScriptPinToWordlessMedia")
agent text anchors:                     never match inside wordless runs
```

We ship our own small font with these six code points (or swap the glyphs for inline SVG). Descript's font file is a signed-in gap.
