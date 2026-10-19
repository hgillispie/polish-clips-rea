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
