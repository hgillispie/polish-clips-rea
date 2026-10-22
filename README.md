# Polish Clips REA

Clean-room notes for **Polish Clips**: a transcript-first pipeline (import, word timings, filler ignore, retakes, enhance, captions, clip cut) and a local editor (timeline, layers, mixer). Caption font, color, position, and optional burn-in are local. The Descript OpenAPI has no caption-style schema. This repository is the spec. It is not a Descript clone, and it does not contain Descript source.

Operators continue this work from **Grok Bot** with **REA** (`rea-agents` 6.7.0) already connected. 

## Clean-room rules

- Write behaviour, data shapes, and pseudocode. Do not paste Descript source, minified bundles, decompiled JavaScript, Wakaru modules, or recovered assets.
- Tag claims **static** (OpenAPI or a file in this repo), **observed** (seen while something ran; **observed-network** when it comes from a signed-in capture), **inferred** (a conclusion from those), **decompiled** (a Wakaru-recovered module), **static-bundle** (a string or slice of the public JS), or **static-help** (help copy).

- Use only an account and media you own. Do not bypass paywalls, credits, or rate limits, and do not extract other people's data or server-side prompts.
- Keep captures out of git. `.gitignore` excludes `captures/`, `*.har`, `*.saz`, `*.asar`, `.env`, and credential files. Redact bearer tokens before sharing a HAR.

## How the docs are organized

| Path | What it is |
| --- | --- |
| [DESCRIPT_RE_PLAN.md](DESCRIPT_RE_PLAN.md) | Current plan. Scope is locked. Desktop ASAR work is finished. |
| [docs/architecture.md](docs/architecture.md) | Thin Electron shell, public API host, and the `api.descript.com` effect/artifact pipeline. |
| [docs/feature-inventory.md](docs/feature-inventory.md) | Polish-clip features mapped to API operations and an open-source stack. |
| [docs/api-notes.md](docs/api-notes.md) | Public OpenAPI shapes, plus editor routes on `api.descript.com` (eye gaze, mask, lip sync, speech enhancement). |
| [docs/reuse-rescript.md](docs/reuse-rescript.md) | Whether to study [wassgha/rescript](https://github.com/wassgha/rescript) or rebuild the editor. |
| [docs/grokbot-rea.md](docs/grokbot-rea.md) | REA on Grok Bot. No Claude Desktop setup. |
| [docs/pseudocode/](docs/pseudocode/) | Pipeline, editor, and bundle-backed effect specs (Eye Contact, Look Good, Video Regenerate, Publish AI), our Underlord-style agent ([underlord/](docs/pseudocode/underlord/)), editor settings ([editor-settings/](docs/pseudocode/editor-settings/)), [smooth-jump-cuts.md](docs/pseudocode/smooth-jump-cuts.md) and [automatic-multicam.md](docs/pseudocode/automatic-multicam.md). |
| [docs/descript-analysis/](docs/descript-analysis/) | Bundle notes for Eye Contact, the enhance suite, Video Regenerate, Publish AI, skin smoothing, the Underlord agent ([underlord/](docs/descript-analysis/underlord/), now with a signed-in [observed-network](docs/descript-analysis/underlord/observed-network.md) pass and a [prompt catalog](docs/descript-analysis/underlord/prompt-catalog.md)), the AI Tools panel ([ai-tools/](docs/descript-analysis/ai-tools/): Smooth jump cuts, Automatic multicam, Publish/Write prompt actions), and three editor settings: room tone, Smart transitions, wordless media ([editor-settings/](docs/descript-analysis/editor-settings/)). |

## Next steps

1. Optional: create a Descript API token on a **test Drive** and probe one import plus one agent job. Record real `job_state` timing and credit counts in `docs/api-notes.md`. Do not commit the token.
2. Record three fixture clips you own (clean speech, fillers plus retakes, noisy audio) outside git, under `captures/` or another ignored path.
3. Build from [docs/pseudocode/polish-pipeline.md](docs/pseudocode/polish-pipeline.md) and [docs/pseudocode/editor/overview.md](docs/pseudocode/editor/overview.md). Default backend is the open stack: filler words stay ignored, and caption style is a local `CaptionStyle`. Burn-in is optional. A Descript `POST /v1/jobs/agent` job is the alternate backend and does not carry style.
4. Eye Contact, the Look Good suite, Video Regenerate, and Publish AI are specified from the public bundle and are later than the polish pipeline. Video Regenerate is `lip_sync` variant `imputation`, not `generate-video`. A voice clone waits on [docs/pseudocode/voice-consent.md](docs/pseudocode/voice-consent.md); the picture step also waits on the visual confirmation in [docs/pseudocode/video-regenerate.md](docs/pseudocode/video-regenerate.md). Punch-in voiceover does not need the voice record.

Working hypothesis, not a decision: a public-API job plus a rescript-like transcript editor is a better Polish Clips MVP than cloning the Descript web app. The current rescript `LICENSE` is PolyForm Noncommercial, so read [docs/reuse-rescript.md](docs/reuse-rescript.md) before copying any of that code.

In-progress work and open signed-in gaps: [HANDOFF.md](HANDOFF.md).
