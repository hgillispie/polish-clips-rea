# Platform profiles (config + sources)

This is the single source of truth for per-platform limits and conventions. Find Highlights packaging ([../find-highlights/](../find-highlights/README.md)), Highlight Reel and the publish optimizer all load a `PlatformProfile` from this table. The profiles ship as `config/platform_profiles.yaml`, versioned, so a platform change does not need a code release.

**Every number here was checked on 2026-10-22 (public-research)** unless the row says otherwise. **Uncertain** means the platform has not documented it, or the sources conflict. Re-check these quarterly; the check is the `profiles_checked_at` field.

## Limits and formats

| Field | YouTube (long) | YouTube Shorts | TikTok | Instagram Reels | Facebook Reels |
| --- | --- | --- | --- | --- | --- |
| Aspect | 16:9 | 9:16 or 1:1 | 9:16 | 9:16 | 9:16 |
| Max length | long-form | **3 min** for square or vertical uploads since 2024-10-15 [YT-3min] | app upload up to 60 min; API 3–10 min depending on the account [TT-len] (**uncertain**: varies by account) | up to 3 min is recommended to non-followers [IG-3min]; longer Reels are allowed but **reported** not to be recommended (**uncertain**) | No maximum. All new videos are Reels (since June 2025) [FB-reels] |
| Title | 100 chars [YT-up] | 100 chars [YT-shorts] | no separate title; caption only | none | none |
| Description / caption | 5,000 chars [YT-up] | 5,000 chars | 4,000 chars in the app; **2,200 UTF-16 units through the Content Posting API** [TT-cap] | 2,200 chars (Graph API error text; **uncertain** in the app) [IG-tags-guide] | not published (**uncertain**) [FB-api] |
| Hashtags | up to 60; more than 60 and **all** are ignored; first 3 shown by the title [YT-tags] | same | no documented cap; an in-app "max 5" message was reported in Aug 2025 (**uncertain**) [TT-len] | **5** per post or reel since 2025-12-18; the API docs still say 30 [IG-tags] | ≤ 5 recommended by Meta creator guidance (**uncertain**: secondary source) [FB-cap] |
| Thumbnail / cover | custom 1280×720, 16:9, JPG/PNG; ≤ 2 MB from a phone [YT-thumb] | frame picker (custom Shorts thumbnails **uncertain**) | cover frame + text | cover 1080×1920; the profile grid crops to a **centred 3:4** (**secondary source**) [IG-cover] | cover frame |
| A/B built in | Title and thumbnail A/B (up to 3), judged by **watch-time share** [YT-ab] | no | no | no (trial reels exist; not covered here) | no |

## What ranking rewards (summary)

| Platform | Signals the platform says matter | What our generator optimizes |
| --- | --- | --- |
| YouTube long | Recommendation uses viewer history, interests and satisfaction. A/B tests judge by watch-time share, not CTR [YT-rec][YT-ab] | **Title and thumbnail CTR without clickbait**: the title must be paid off in the first 30 s. Description keywords for search. Chapters |
| YouTube Shorts | "Viewed vs swiped away", engaged views, seed audience then expansion [YT-rec][YT-engaged] | **The first 1–2 s stops the swipe.** Loop-friendly endings. Titles are short, since they are mostly hidden in the feed |
| TikTok | Watch to completion, likes, shares, comments, follows, favorites, skips/"Not interested"; video info such as captions, sounds, hashtags [TT-rec] | **Completion + rewatch.** Searchable caption keywords (TikTok search). 3–5 specific hashtags. On-screen hook text |
| Instagram Reels | Top 3: **watch time, likes per reach, sends per reach**; sends weigh more for non-followers. Originality: copies and watermarked videos get less reach [IG-rank][IG-mosseri][IG-orig] | **Sendability** (useful, funny, "send this to X"). **No other platform's watermark.** 5 specific hashtags |
| Facebook Reels | Predicted completion, views, likes, shares, comments; recent interactions; topic similarity; reel length; also predicts skips and hides [FB-rank] | Completion + shares. Plainer captions. Older-skewing audiences: clarity over slang (**design** assumption) |

**Audience notes (design, low confidence).** Audience demographics differ by platform. TikTok and Instagram skew younger, and Facebook and YouTube long-form skew older and broader. We do not hard-code age claims. Instead, each profile has a `voice` default (TikTok: casual, Facebook: plain, YouTube: descriptive) that the user can override per brand. Treat any demographic claim as **uncertain** until we cite a current survey (for example Pew Research's social media fact sheet) in a later pass.

## Safe zones (9:16, 1080×1920)

These keep hook text, captions and faces clear of the platform UI. They are design defaults, taken from Meta's ads guidance and creator templates. Organic UI differs by app version, so they are **uncertain**.

| Platform | Top clear | Bottom clear | Right clear | Source |
| --- | --- | --- | --- | --- |
| Instagram Reels | 14% (270 px) | 35% (670 px) | 6% | Meta ads safe zone [META-safe] |
| Facebook Reels | 14% | 35% | 6% | same |
| TikTok | 8% (150 px) | 25% (480 px) | 12% (130 px, action rail) | creator templates (**uncertain**) |
| YouTube Shorts | 8% | 25% | 12% | creator templates (**uncertain**) |

**Profile default (design).** We use the union of all four: **top 14%, bottom 35%, sides 12%**. Captions sit at y ≈ 55–62%, and hook text sits at y ≈ 18–30%. A per-platform export can loosen this.

## Sources

| Key | URL |
| --- | --- |
| YT-3min | https://support.google.com/youtube/answer/15424877 |
| YT-shorts | https://support.google.com/youtube/answer/10059070 |
| YT-up | https://support.google.com/youtube/answer/57407 |
| YT-tags | https://support.google.com/youtube/answer/6390658 |
| YT-thumb | https://support.google.com/youtube/answer/72431 |
| YT-ab | https://support.google.com/youtube/answer/16391400 |
| YT-rec | https://support.google.com/youtube/answer/16559650 |
| YT-engaged | https://blog.youtube/inside-youtube/engaged-views-youtube-explained/ |
| TT-rec | https://support.tiktok.com/en/using-tiktok/exploring-videos/how-tiktok-recommends-content |
| TT-cap | https://developers.tiktok.com/doc/content-posting-api-reference-direct-post (via the summary at https://kodahq.app/en/reference/tiktok-caption-and-hashtag-limits) |
| TT-len | https://postango.ai/guides/tiktok-video-size (quotes TikTok developer docs and support pages) |
| IG-rank | https://about.instagram.com/blog/announcements/instagram-ranking-explained |
| IG-mosseri | https://www.socialmediatoday.com/news/instagram-shares-algorithm-insights-2025/738034/ |
| IG-orig | https://creators.instagram.com/blog/recommendations-and-originality |
| IG-3min | https://www.theverge.com/2025/1/18/24346567/instagram-announces-reels-3-minute-video-posts |
| IG-tags | https://www.socialmediatoday.com/news/instagram-implements-new-limits-on-hashtag-use/808309/ ; https://help.instagram.com/351460621611097 |
| IG-tags-guide | https://postboost.co/learn/instagram-hashtag-limit.md (cites the Graph API error text: 2,200 chars / 30 tags) |
| IG-cover | https://wowreveal.com/blog/reel-cover-size-safe-zones (secondary) |
| FB-reels | https://creators.facebook.com/blog/making-it-easier-to-create-videos-on-facebook ; https://www.reuters.com/business/all-new-facebook-videos-be-classified-reels-soon-meta-says-2025-06-17/ |
| FB-rank | https://transparency.meta.com/features/explaining-ranking/fb-reels/ |
| FB-api | https://developers.facebook.com/docs/video-api/guides/reels-publishing/ |
| FB-cap | https://reeluploader.com/blog/caption-length-limits (secondary) |
| META-safe | https://www.facebook.com/business/help/980593475366490 |

## Config shape

```yaml
# config/platform_profiles.yaml  (profiles_checked_at: 2026-10-22)
youtube_shorts:
  aspect: "9:16"
  duration: { min_s: 5, max_s: 180, sweet_spot_s: [20, 60] }   # sweet spot = design default
  title:   { max_chars: 100, show_chars: 40, required: true }
  caption: { max_chars: 5000, show_chars: 100, unit: "chars" }
  hashtags: { max: 3, placement: "description_end", hard_cap: 60, over_cap_behavior: "all_ignored" }
  hook:    { window_s: [0, 2], on_screen_text_max_words: 8 }
  cover:   { mode: "frame_pick" }
  safe_zone: { top: 0.08, bottom: 0.25, right: 0.12, left: 0.04 }
  voice: "descriptive"
  optimize_for: ["stop_swipe", "completion", "loop"]
tiktok:
  aspect: "9:16"
  duration: { min_s: 3, max_s: 600, api_max_s_default: 180, sweet_spot_s: [15, 45] }
  title: null
  caption: { max_chars: 2200, unit: "utf16", app_max_chars: 4000, show_chars: 90 }
  hashtags: { max: 5, placement: "caption_end", uncertain: true }
  hook: { window_s: [0, 1.5], on_screen_text_max_words: 7 }
  cover: { mode: "frame_plus_text" }
  safe_zone: { top: 0.08, bottom: 0.25, right: 0.12, left: 0.04 }
  voice: "casual"
  optimize_for: ["completion", "rewatch", "search_keywords", "shares"]
instagram_reels:
  aspect: "9:16"
  duration: { min_s: 3, max_s: 180, sweet_spot_s: [15, 60] }
  title: null
  caption: { max_chars: 2200, show_chars: 125 }
  hashtags: { max: 5, placement: "caption_end" }
  hook: { window_s: [0, 2], on_screen_text_max_words: 8 }
  cover: { size: [1080, 1920], grid_crop: "3:4" }
  safe_zone: { top: 0.14, bottom: 0.35, right: 0.06, left: 0.06 }
  forbid: ["foreign_watermark"]
  voice: "conversational"
  optimize_for: ["sends", "watch_time", "likes"]
facebook_reels:
  aspect: "9:16"
  duration: { min_s: 3, max_s: null, sweet_spot_s: [20, 90] }
  title: null
  caption: { max_chars: null, show_chars: 125 }
  hashtags: { max: 5, placement: "caption_end", uncertain: true }
  hook: { window_s: [0, 3], on_screen_text_max_words: 9 }
  cover: { mode: "frame_pick" }
  safe_zone: { top: 0.14, bottom: 0.35, right: 0.06, left: 0.06 }
  voice: "plain"
  optimize_for: ["completion", "shares", "comments"]
youtube_long:
  aspect: "16:9"
  title: { max_chars: 100, show_chars: 60, required: true }
  caption: { max_chars: 5000, show_chars: 150 }
  hashtags: { max: 3, placement: "description_end", hard_cap: 60, over_cap_behavior: "all_ignored" }
  chapters: { required_min: 3, first_at: "0:00", min_len_s: 10 }     # YouTube chapter rules: re-check
  thumbnail: { size: [1280, 720], max_bytes_mobile: 2000000, text_max_words: 4 }
  ab: { titles: 3, thumbnails: 3, metric: "watch_time_share" }
  voice: "descriptive"
  optimize_for: ["ctr_honest", "search_keywords", "retention_first_30s"]
```

`sweet_spot_s` values are **design** defaults, not platform rules. Tune them from our own eval (see [README.md](README.md#eval--metrics)).
