# Share, embed, publish

Evidence: **decompiled** (`getEmbedCode`, embed helpers, React embed wrapper),
**observed** (loader + payload), **static-help** (plan gates).

## Publish and share types

- Publishing sets `status = published` (+ `publishedDate`). Unpublished/draft flows 404 for viewers.
- `DefaultShareType` public 1 | private 2 (workspace setting). Private = signed-in members only.
- Share mode `secure` | `smooth` ("Enable Secure Sharing" flag; inferred: secure = no public CDN URLs).
- `crawlable` toggles SEO indexing of the share page ("Prevent Indexing" flag).

## Share URLs

```
https://<demoBase>/<flowId>                       # share page (demo.<domain>/share/<id> internally)
https://<demoBase>/<flowId>/<customLinkId>        # custom link (per prospect)
…/guide                                           # step-by-step text guide view
…/offline                                         # offline bundle (Enterprise "Offline access")
```
Custom domains: `customDomain` in share props (Enterprise).

## Custom links (Enterprise "Custom share links")

Collection `customLinks`. Protection modes: `password`, `email` (email gate → lead),
`expiration`. Reports `customLinkFirstViewed` on first view. Variables can be pre-filled
per link (inferred: link stores `variable.*` values).

## Iframe embed snippet

```
getEmbedCode(flow, opts):
  src = `${demoBase}/${flowId}${customLinkId ? "/"+customLinkId : ""}?embed`
        + `&embed_mobile=${inline|tab|modal}&embed_desktop=${inline|tab|modal}`
        + (squared ? "&squared=true" : "") + "&show_copy_link=true"
        + for each variable: `&variable.${name}=INSERT_VALUE_HERE`
        + (forceNoHeader ? "&force_no_header=true" : "")
        (custom trigger → "&embed_custom")
  aspect = flow.aspectRatio || 9/16
  if aspect <= 1 (landscape):
     <div style="position:relative; padding-bottom:calc(aspect*100% + 41px); height:0; width:100%">
        <iframe src=… title=… frameborder=0 loading=lazy webkitallowfullscreen mozallowfullscreen allowfullscreen
                allow="clipboard-write; autoplay"
                style="position:absolute; top:0; left:0; width:100%; height:100%; color-scheme:light">
  else (portrait/mobile recording):
     container with CSS aspect-ratio and max-height 70vh/80vh
  wrap in <!-- … EMBED START --> / <!-- … EMBED END --> comments
  collection embeds add a sandbox attribute
```
Mobile-recording detection uses aspect ≥ ~1.7 with date-based rollout cut-offs.
`embed_*` options: `inline` (plays in place), `tab` (opens new tab), `modal` (pop-out over host page).

### Pop-out protocol (React/JS wrapper ↔ iframe)

iframe → parent `arcade-init`; wrapper replies `register-popout-handler`; iframe asks
`arcade-popout-open` to open the fullscreen modal on the host page. (decompiled)

## Web component embed

```
<script async src="${demoBase}/embed/v1/loader.js"></script>
<arcade-demo flow-id="…" start-step="…"></arcade-demo>
```
Loader behaviour in [../../arcade-analysis/build-and-hosts.md](../../arcade-analysis/build-and-hosts.md).
Flag "Web Component Embeds". When embedded as a web component, the tracker disables
client persistence and query-string identity, and never posts events to the host via
postMessage (it dispatches DOM events instead).

## Other surfaces

- oEmbed: `GET /api/oembed?url=` (Notion, Medium, etc.).
- `/api/embed/{a}/{b}` (shape not recovered).
- Link expander extension turns pasted links into GIF previews in Gmail/Outlook/Superhuman/GitHub.
- Collections (`flowsCollections`, `/api/flows-collections`): a playlist of flows with its own
  share page and embed; Enterprise ("Demo collections"); plan-limit key `collections`.
- Step-by-step guide (`/flows/[pid]/guide`, `/share/[pid]/guide`): text + screenshots doc
  derived from steps ("Step-by-Step Guide" flag).

## Checksums

`getChecksum(flow)` hashes only viewer-affecting props, used to decide when cached
exports/previews/OG images are stale. (decompiled name + usage; exact field list is ours)
