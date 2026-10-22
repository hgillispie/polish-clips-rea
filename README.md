# Arcade-style interactive demo builder (REA branch `arcade-rea`)

> **This branch is NOT a video editor.** It is the clean-room spec for an
> **interactive, click-through product demo builder** in the style of
> [Arcade](https://www.arcade.software/): a Chrome extension records a web
> app, every click becomes a screenshot step with a hotspot, an editor adds
> callouts, chapters, branching, forms, pan-and-zoom and AI voiceover, and a
> lightweight player is embedded as an iframe or web component with analytics.
>
> The earlier **Descript / Polish Clips** (transcript video editor) work lives on
> branch [`claude/compassionate-pascal-apg87s`](https://github.com/hgillispie/polish-clips-rea/tree/claude/compassionate-pascal-apg87s).
> Its docs were removed from this branch on purpose so an agent picking this up
> is not confused about which product it is building.

Start with [HANDOFF.md](HANDOFF.md), then [ARCADE_RE_PLAN.md](ARCADE_RE_PLAN.md).
Claude Code / other implementers: read [CLAUDE.md](CLAUDE.md).

## What we are building

| Surface | What it does | Spec |
| --- | --- | --- |
| Capture extension (MV3) | Records a tab. Per click: screenshot + normalized click point + DOM context; optional tab video, optional HTML snapshot. | [docs/pseudocode/capture/](docs/pseudocode/capture/) |
| Step builder | Turns captured events into an ordered list of Image / Video steps with one hotspot each, inserting video clips where something "interesting" happened. | [step-builder.md](docs/pseudocode/capture/step-builder.md) |
| Editor | Edits the Flow document: hotspots, callouts, overlays (chapters, forms, embeds), branching, pan-zoom, blur/crop, variables, translations, voiceover. | [docs/pseudocode/model/](docs/pseudocode/model/), [docs/pseudocode/editor/](docs/pseudocode/editor/) |
| Player | Renders a Flow: stage scaling, hotspot/callout animation, navigation, autoplay, captions/voice, analytics events. | [docs/pseudocode/player/](docs/pseudocode/player/) |
| Share + embed | Share page, iframe embed snippet, `<arcade-demo>`-style web component, oEmbed, custom links. | [embed-and-share.md](docs/pseudocode/player/embed-and-share.md) |
| Backend | Firestore-style document store + REST routes under `/api/*`, signed upload URLs, Mux-style video, async AI jobs. | [docs/api-notes.md](docs/api-notes.md), [docs/architecture.md](docs/architecture.md) |

## Clean-room rules

- Write behaviour, data shapes and pseudocode in our own words. **Do not paste** Arcade source, minified bundles, Wakaru output, CRX contents or recovered assets.
- Raw downloads and decompiled output stay **local** (on the REA box under `/workspace/arcade-rea-research/`). `.gitignore` blocks the usual paths.
- Every detailed claim carries an evidence tag:
  - **decompiled**: read from a Wakaru-unpacked module of the CRX or web/player bundle.
  - **static-bundle**: a string, enum or call shape read from the raw public JS.
  - **observed**: seen in a public response (public share JSON, embed payload, loader).
  - **static-help**: Arcade help center / pricing / marketing copy.
  - **inferred**: our conclusion from the above.
- Use only public pages and our own account. Do not bypass paywalls, credits, or auth; do not extract other people's data or server-side prompts.
- Names like `Flow`, `Step`, `Hotspot` are kept because they are the natural domain words; implementation is ours.

## How the docs are organized

| Path | What it is |
| --- | --- |
| [HANDOFF.md](HANDOFF.md) | What was done, evidence gaps, what is unfinished. |
| [ARCADE_RE_PLAN.md](ARCADE_RE_PLAN.md) | RE plan: sources, method, status per area, next passes. |
| [docs/architecture.md](docs/architecture.md) | Hosts, components, data flow from capture to share. |
| [docs/feature-inventory.md](docs/feature-inventory.md) | Every feature, where it lives, plan gate, evidence, build priority. |
| [docs/api-notes.md](docs/api-notes.md) | Backend routes (method, path, payload) recovered from the extension and web bundles. |
| [docs/evidence-index.md](docs/evidence-index.md) | Which local artifact backs which doc, REA evidence ids, hashes. |
| [docs/arcade-analysis/](docs/arcade-analysis/) | Bundle notes: extension manifest, build/hosts, plans and gating, enums. |
| [docs/pseudocode/](docs/pseudocode/) | Implementable specs (capture, model, player, editor). |
| [docs/schemas/flow.schema.json](docs/schemas/flow.schema.json) | Our JSON Schema for the Flow document (derived, not copied). |

## Next steps

1. Implement the data model first ([flow-model.md](docs/pseudocode/model/flow-model.md), [flow.schema.json](docs/schemas/flow.schema.json)).
2. Build the player against hand-written fixture flows ([player/runtime.md](docs/pseudocode/player/runtime.md)).
3. Build the MV3 capture extension and the step builder ([capture/](docs/pseudocode/capture/)).
4. Then editor features in the priority order in [feature-inventory.md](docs/feature-inventory.md).
