# Descript: Publish AI (titles, YouTube description, show notes)

Public web client, build `react19/9a29d61183bce669600a9dd9a1f8588d708becac` (2026-10-19). Chunk **88** `88.fc0ea62a7f115f3adca9.js`, AI action enum near offset ~1995267.

This is not `POST /v1/jobs/publish` on `descriptapi.com`. That OpenAPI route returns a share URL and a download URL (**static** OpenAPI). Publish AI is an in-app writing surface: kebab action ids plus an Underlord skill.

## Action ids (static-bundle)

Recovered from the kebab enum slice:

| Enum member | Wire id |
| --- | --- |
| `SuggestTitle` | `suggest-title` |
| `ShowNotes` | `show-notes-v2` |
| `YouTubeDescription` | `youtube-description-v2` |
| `YouTubeThumbnail` | `youtube-thumbnail` |
| `SocialPosts` | `social-posts` |
| `Summarize` | `summarize-v2` |
| `WriteScript` | `write-script` |
| `Translate` | `translate` |

`add-chapters` is a tracked feature and a credit key (`add_chapters` → `ai_editing`). It is named in the action inventory beside these ids. The enum slice that begins at `RemoveRetakes` does not include the `add-chapters` token; treat the wire id as **static-bundle** from the action inventory, not as a second copy of the enum literal.

`GenerateTitle: 10000` is a character budget on the app-side title tool (**static-bundle**, `app` chunk). It is not a YouTube title-length field.

## Credit category `ai_writing` (static-bundle)

| Key | Category |
| --- | --- |
| `draft_a_title` | `ai_writing` |
| `autotitle_composition` | `ai_writing` |
| `summarize` | `ai_writing` |
| `draft_show_notes` | `ai_writing` |
| `draft_youtube_description` | `ai_writing` |
| `draft_social_post` | `ai_writing` |
| `draft_blog_post` | `ai_writing` |
| `brainstorm`, `write_script`, `write_outline`, `rewrite`, `smart_fill` | `ai_writing` |

No integer credit cost for these keys was in the map. The category is the fact. Chapters (`add_chapters`) bill as `ai_editing`, not `ai_writing`.

## Skill `prepare-for-publish` (static-bundle)

| Field | Value |
| --- | --- |
| id | `prepare-for-publish` |
| name | `Prepare for publish` |
| isInvokable / isViewable | both true |
| gate | feature flag `agent-first-party-macro-skills` must be true |

The skill description says it produces titles, a YouTube description with chapters, platform social posts, and a thumbnail, and that the output is text and images only. The workflow, paraphrased from the client string, not pasted:

1. Ask which platforms and who the audience is, one question at a time. Tone, length, and examples are optional.
2. Draft several titles.
3. Draft a YouTube description with chapters. If the video is longer than 10 minutes, the skill tells the agent to add spaced teaser timestamps written as `00:00` plus SEO hashtags.
4. Draft social posts using a `social-platform-style-reference` insert.
5. If the destination includes YouTube, offer a thumbnail via a `yt-thumbnail` insert (`youtube-thumbnail` is the kebab).
6. Offer to iterate. Do not export, render, or publish unless the user explicitly asks. Do not change the edit.

Other skills point at this one for "a publish package with show notes."

The server prompt templates behind `suggest-title` and `youtube-description-v2` were **not** inlined in the public entry. The skill text is orchestration. Do not invent those prompts and do not paste the skill markdown into implementation source.

## Chapters

Selector `getYouTubeChaptersFromMarkers` builds `{name, timestamp}` from composition markers (**static-bundle**). Transcript scrubbers take `leaveChapters` and `extractChapterNames`. Timestamps in Polish Clips come from those markers. The skill's "add spaced teaser timestamps" instruction is real client copy; our spec refuses a timestamp that is not a marker (see the pseudocode). That refusal is our rule, not a branch recovered from the selector.

## Thumbnail

`youtube-thumbnail` is in the generative action set with `generate-image`, `generate-video`, `generate-music`, and `generate-sfx`. It is out of the title/description spec except as a step the skill may offer. No thumbnail model was unpacked.

Build spec: [../pseudocode/youtube-titles-descriptions.md](../pseudocode/youtube-titles-descriptions.md). Agent wiring: [../pseudocode/underlord-agent-job.md](../pseudocode/underlord-agent-job.md).
