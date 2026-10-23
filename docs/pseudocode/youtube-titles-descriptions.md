# YouTube titles, descriptions, and show notes

> **Generalized** to all platforms in [publish-metadata.md](publish-metadata.md) (spec: [../features/publish-metadata/README.md](../features/publish-metadata/README.md), limits: [platform-profiles.md](../features/publish-metadata/platform-profiles.md)). This file remains the reference for chapters.

Publish-package copy from the transcript and composition markers. Wire ids match the web client's AI actions. This does not call `POST /v1/jobs/publish` and does not render a file.

Analysis: [../descript-analysis/youtube-publish-ai.md](../descript-analysis/youtube-publish-ai.md). Skill wiring: [underlord-agent-job.md](underlord-agent-job.md).

## Actions and credits (static-bundle)

| Call | Kebab | Credit key | Category |
| --- | --- | --- | --- |
| Titles | `suggest-title` | `draft_a_title` | `ai_writing` |
| Also a title path | (autotitle) | `autotitle_composition` | `ai_writing` |
| YouTube description | `youtube-description-v2` | `draft_youtube_description` | `ai_writing` |
| Show notes | `show-notes-v2` | `draft_show_notes` | `ai_writing` |
| Summary | `summarize-v2` | `summarize` | `ai_writing` |
| Social posts | `social-posts` | `draft_social_post` | `ai_writing` |
| Chapters as an edit | `add-chapters` | `add_chapters` | `ai_editing` |

No integer cost was in the category map. Record the key. Do not invent a credit count.

`GenerateTitle: 10000` is the app tool's character budget (**static-bundle**). Clamp the prompt input to 10000 characters after whitespace collapse. It is not a title-length limit. Titles themselves are short strings the model returns; store them whole.

Thumbnail kebab `youtube-thumbnail` is in the generative action set. This spec does not generate images. The publish skill may offer that step; the implementation returns `thumbnail: skipped`.

## Types

```text
ChapterMarker
  name         string
  timestamp    string          # "HH:MM:SS" or "MM:SS" from a composition Marker
  time_seconds number

PublishBrief
  composition_id   string
  title_hint       string | null
  audience         string | null
  platforms        string[]        # operator words: YouTube, LinkedIn, ...
  tone             string | null
  duration_seconds number
  transcript_text  string          # non-ignored words, capped at 10000 chars
  chapters         ChapterMarker[] # from markers only

TitleResult
  action   "suggest-title"
  titles   string[]                # several options
  credit   "draft_a_title"

YoutubeDescription
  action       "youtube-description-v2"
  description  string
  chapters     ChapterMarker[]
  hashtags     string[]            # may be empty
  credit       "draft_youtube_description"

ShowNotes
  action    "show-notes-v2"
  markdown  string
  credit    "draft_show_notes"

PublishPackage
  titles        TitleResult
  youtube       YoutubeDescription | null
  show_notes    ShowNotes | null
  social        string[] | null
  thumbnail     "skipped"
  exported      false               # this skill does not export
```

## Chapters

Selector name in the client: `getYouTubeChaptersFromMarkers` (**static-bundle**). Scrubber options `leaveChapters` and `extractChapterNames` exist. We only need the marker list.

```text
function chapters_from_markers(composition) -> ChapterMarker[]:
  # Timeline markers are { time_seconds, label } in editor/overview.md.
  rows = []
  for marker in composition.timeline.markers, sorted by time:
    if marker.label.trim() == "":
      continue
    rows.append({
      name: marker.label,
      time_seconds: marker.time_seconds,
      timestamp: format_clock(marker.time_seconds)
    })
  return rows

function assert_real_timestamps(text, chapters) -> void:
  # Our rule. The prepare-for-publish skill tells the agent to add spaced
  # teaser timestamps when duration > 10 minutes (static-bundle). We still
  # refuse a clock time that is not one of chapters[].timestamp.
  for token in clock_tokens(text):
    if token not in [c.timestamp for c in chapters]:
      fail "timestamp " + token + " is not a marker"
```

If there are no markers, the description has no chapter block. Do not synthesize times from topic shifts in this version. `add-chapters` would be a separate edit that creates markers first; it bills `ai_editing`, and this file does not run it.

## Draft

```text
function publish_brief(composition, transcript, hints) -> PublishBrief:
  words = [w.text for w in transcript.words if not w.flags.ignored]
  text = join(words)
  if text.trim() == "":
    fail "no transcript"
  return PublishBrief(
    transcript_text=truncate(text, 10000),
    chapters=chapters_from_markers(composition),
    duration_seconds=composition_duration(composition),
    ...
  )

function suggest_title(brief) -> TitleResult:
  raw = llm(system=title_instructions(brief), user=brief.transcript_text)
  titles = nonempty unique lines(raw)
  if titles is empty:
    fail "no titles"
  return { action: "suggest-title", titles: titles, credit: "draft_a_title" }

function youtube_description(brief) -> YoutubeDescription:
  over_10_min = brief.duration_seconds > 600
  raw = llm(...)
  # The skill asks for teaser timestamps and SEO hashtags only when over 10 minutes.
  # Hashtags may be model text. Timestamps may not be invented.
  assert_real_timestamps(raw.description, brief.chapters)
  if not over_10_min:
    # Still allow a chapter list built from markers. Do not add extra teaser lines.
    raw.teaser_lines = []
  return {
    action: "youtube-description-v2",
    description: raw.description,
    chapters: brief.chapters,
    hashtags: raw.hashtags if over_10_min else [],
    credit: "draft_youtube_description"
  }

function show_notes(brief) -> ShowNotes:
  md = llm(...)
  assert_real_timestamps(md, brief.chapters)
  return { action: "show-notes-v2", markdown: md, credit: "draft_show_notes" }
```

`title_instructions` is ours: several options, grounded in the transcript, no claims the transcript does not support. The server's hidden prompt for `suggest-title` was not in the entry bundle. Do not copy a Descript prompt out of a skill body into source. The skill workflow is paraphrased in the analysis file and implemented by `prepare_for_publish` below.

Store the package on the project as metadata. Do not burn it into the media.

## Skill `prepare-for-publish`

Client skill id `prepare-for-publish`, gate flag `agent-first-party-macro-skills` must be on (**static-bundle**). Invokable and viewable. Output is text and images only.

```text
function prepare_for_publish(composition, transcript) -> PublishPackage:
  if not flag("agent-first-party-macro-skills"):
    fail "prepare-for-publish is gated"
  hints = ask_one_at_a_time([
    "Where is this being published, and who is the audience?",
    "Any tone, length, or example to match? (optional)"
  ])
  brief = publish_brief(composition, transcript, hints)
  package = {
    titles: suggest_title(brief),
    youtube: youtube_description(brief) if "YouTube" in hints.platforms else null,
    show_notes: show_notes(brief),
    social: social_posts(brief) if hints.platforms else null,
    thumbnail: "skipped",
    exported: false
  }
  # Do not call export_composition, POST /jobs/publish, or mutate the timeline.
  offer_iteration(package)
  return package

function social_posts(brief) -> string[]:
  # Kebab social-posts. Credit draft_social_post.
  # Platform tone comes from the operator's named platforms.
  # The client insert is named social-platform-style-reference; its body was not recovered.
  return llm_posts(brief)
```

Iteration is another call to the same functions with the operator's note appended to `tone`. It does not export.

## Errors

| Case | Behaviour |
| --- | --- |
| Empty transcript | Fail before any LLM call |
| Input over 10000 characters | Truncate and set `truncated: true` on the brief |
| Clock token that is not a marker | Reject that draft and ask the model once more with the marker list. If it happens again, fail the description and keep the titles |
| LLM not configured | Fail. Do not call `api.descript.com` to fill in |
| Gate flag off | `prepare_for_publish` fails. Direct `suggest_title` still runs; it is not the skill |
| Operator asks to publish | Stop. Point at [editor/export-render.md](editor/export-render.md) or the public publish job. This skill's `exported` stays false |

`add-chapters` is not called implicitly when markers are missing.
