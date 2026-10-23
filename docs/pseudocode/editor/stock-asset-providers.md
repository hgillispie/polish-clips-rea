# Stock and GIF providers

A pluggable search interface for overlay assets. Providers are configured with environment variables. This repo does not embed API keys, client secrets, or a provider SDK.

The operator searches, picks a result, and the app downloads it into the project cache. The clip is then an overlay ([overlays.md](overlays.md)).

## Interface

```text
AssetKind = "image" | "gif" | "video"

Attribution
  provider_id     string
  provider_name   string
  author_name     string | null
  author_url      string | null
  source_url      string          # page on the provider, not a hotlink used at render time
  license_name    string          # required; human-readable
  license_url     string | null

AssetResult
  provider_asset_id  string
  kind               AssetKind
  title              string
  preview_url        string       # thumbnail or preview mp4; may expire
  download_url       string | null  # null until the provider returns one for the chosen size
  width              integer | null
  height             integer | null
  duration_seconds   number | null
  attribution        Attribution  # required; a result with an empty license_name is dropped

StockProvider
  id              string
  display_name    string
  kinds           AssetKind[]     # what search may return
  search(query, kind, limit) -> AssetResult[]
  download(result) -> MediaAsset  # bytes in the project cache
```

```text
function search_stock(providers, query, kind, limit) -> AssetResult[]:
  if query.trim() == "":
    return []
  out = []
  for provider in providers:
    if kind not in provider.kinds:
      continue
    if not provider_configured(provider):
      continue
    try:
      hits = provider.search(query, kind, limit)
    catch error:
      record provider.id + " search failed"; continue
    for hit in hits:
      if hit.attribution.license_name.trim() == "":
        continue
      out.append(hit)
  return out

function place_stock_result(composition, provider, result, at) -> OverlayClip:
  asset = provider.download(result)
  asset.origin = "stock"
  asset.attribution = result.attribution
  clip = add_overlay(composition, asset, at, null)
  clip.attribution = result.attribution
  return clip
```

`provider_configured` is true only when the env vars that provider needs are present and non-empty. A missing key hides that provider in the picker. It is not a hard failure of the editor.

## Candidate providers

Integrate later. Names and terms below are public product facts, not a recommendation to ship a key. Read the current terms before enabling one. Keys stay in the environment (`GIPHY_API_KEY`, `TENOR_API_KEY`, `UNSPLASH_ACCESS_KEY`, `PEXELS_API_KEY`), never in git.

| Provider | Kind | Notes |
| --- | --- | --- |
| Giphy | gif | API key. Their terms restrict how results are shown and cached. Hotlinking preview URLs is not a substitute for reading the current API terms |
| Tenor (Google) | gif | API key. Same rule: cache only what the terms allow, and keep attribution |
| Unsplash | image | Access key. Their API requires attribution and forbids copying the library into another stock service |
| Pexels | image, video | API key. Attribution is part of their guidelines. Video results map to `AssetKind.video` |

Do not scrape a website when the API is the supported path. Do not strip attribution to fit a layout. The inspector shows `author_name` and `license_name` on stock clips, and export can write a sidecar `CREDITS.txt` listing them.

## Download rules

```text
function download(result) -> MediaAsset:
  if result.download_url is null:
    result = refresh_download_url(result)     # provider-specific; may 401 if the key is bad
  bytes = http_get(result.download_url, timeout=60s, max_bytes=200_000_000)
  if status != 200:
    fail "download failed"
  sniff the container; reject html and unknown types
  path = project_cache("stock/" + provider_id + "/" + provider_asset_id)
  write path
  return MediaAsset(path, kind, attribution=result.attribution)
```

200 MB cap. The operator can import a larger local file through [overlays.md](overlays.md) without a provider.

## Errors

| Case | Behaviour |
| --- | --- |
| No providers configured | Search returns empty and the UI says to set a key. Local import still works |
| 401 / 403 from a provider | That provider fails the search. Do not log the key |
| Empty license | Drop the hit |
| Rate limit | Skip that provider for this query. Do not retry in a loop |
| Preview URL used as the timeline media | Refuse. Only the downloaded cache file is a `media_id` |

No Descript 402. This path does not call descriptapi.com.

## How Descript does it (for comparison)

From Hunter's signed-in capture (**observed-network**) and the signed build (**decompiled**). It is a reference only; our providers above stay the plan.

### Stock libraries (observed-network)

| Call | Body → response |
| --- | --- |
| `GET /v2/cloud_libraries/providers` | `{providers: [{id, display, media_types[]}]}`. For Hunter: `stock-photos` (image), `stock-illustrations` (image), `stock-footage` (video), `stock-backgrounds` (video), `stock-music` (audio), `stock-sfx` (audio) |
| `POST /v2/cloud_libraries/providers/{provider}/{mediaType}/explore` | `{tracking_info: {project_id}, pagination_info: {page, page_size}}` → `{results: [{id, preview_url, thumbnail_url, info: {name, duration?, aspect_ratio}}]}`. With no query this is the browse view; search is the same route plus a query (static-bundle) |
| `POST /v2/media/assets/copy_to_project` | `{project_id, asset_id, library_type ("drive" for brand/library items), library_id}` → `{asset: {id, lookup_key, created_at, created_by, metadata: {default_display_name, type}}}` |
| `POST /v2/mts/asset/{id}/image`, `…/video_playlist`, `…/audio_playlist` | Media transcoding service: thumbnails and HLS-style playlists for previews and imported assets |

Preview URLs are short-lived signed CDN links (not recorded). The editor only keeps the copied project asset, which matches our "download, then reference the cache file" rule.

### GIPHY (decompiled; not in the capture, which only kept Descript hosts)

- **Providers.** `giphy-gifs` and `giphy-stickers`. They show in the New layer menu only when the Drive feature `gifs_and_stickers` is on. The flag `cloud-provider-giphy` was true for Hunter.
- **The browser calls GIPHY directly.**
  - It uses `api.giphy.com/v1/gifs` or `/v1/stickers`, path `search` (with `q`) or `trending` (no query).
  - Parameters: `limit` (25), `offset = (page−1)·limit`, and an API key from the client config.
  - With flag `cloud-library-safe-search` it adds `rating=g`, except on a search where the caller turned safe results off.
  - Fetch-by-id is `/v1/gifs/{id}`.
- **Result mapping.**
  - `{id, title → info.name, preview/thumbnail = original.webp ?? original.url, aspectRatio = width/height}`, plus a `giphyOriginal {gif{url,size}, mp4{url,size}, transparent}` record. `transparent` is true for stickers.
- **Import.**
  - **Stickers** import the **gif** (alpha) as a video media ref flagged `isGif`.
  - **GIFs** import the **mp4** as ordinary video. Either way the file is fetched and stored as a project asset, not hotlinked.

### AI image generation (decompiled; no generation ran in the capture)

- **Entry points.** These are New layer → **Generate image**, the empty-scene overlay → **Generate visuals**, and AI Tools → **Generate media**. All three open the sidebar AI-actions panel with preset `generate-image`; only the `entrypoint` differs: `selection-toolbar`, `empty_scene_overlay` or the AI Tools item. The agent tool `generate_images` calls the same backend.
- **Job.**
  1. `POST /projects/{id}/media_generation/queue` with `{model, prompt, number of results, aspect ratio, optional reference images}` (static-bundle).
  2. The client polls every 1 s, giving up after 600 s.
  3. The editor also polls `GET /v2/projects/{id}/media_generation/jobs/active`. The capture has 9 such calls, all empty.
- **Models** (enum in chunk 5433). Image models include `nano-banana`, `nano-banana-2`, `nano-banana-2.1`, `nano-banana-pro`, `imagen4`, `flux-pro-kontext` and `seedream-v3`. Each id maps to a hosted route; most are `fal-ai/…`, while `nano-banana-2.1` maps to a `google/…` route. Video, music and SFX models are in the same enum.
- **Defaults.**
  - **nano-banana, verified.** The agent's layout and thumbnail path hard-codes `nano-banana-2.1` (one result, 16:9, plus title/topic/description context). Other paths use the picker's model. Its default is `nano-banana-2.1` when that model is in the available list and not disabled on the Drive's plan; otherwise it is `nano-banana`.
  - **Flags (observed).** `dall-e-model` = `gpt-image-1` is a legacy image route. `hidden-media-generation-models` hides veo3/veo3-fast, kling v2.6 pro, seedance v1 lite and pro, seedream-v3, and minimax h3/h3-max from the picker. `unlimited-media-generation-models` is false.
- **Billing.** Feature `image_generation` (paywall `imageGeneration`).

For our build: one `GenerateImageProvider` beside the stock providers. Its output is a downloaded file with `license_name: "generated"` and the prompt stored in the asset metadata.
