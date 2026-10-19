# Polish Clips REA

Clean-room notes for **Polish Clips**: a transcript-first pipeline (import, word timings, filler ignore, retakes, enhance, captions, clip cut) and a local editor (timeline, layers, mixer). Caption font, color, position, and optional burn-in are local. The Descript OpenAPI has no caption-style schema. This repository is the spec. It is not a Descript clone, and it does not contain Descript source.

Operators continue this work from **Grok Bot** with **REA** (`rea-agents` 6.7.0) already connected. The Claude Code / Claude Desktop / Cowork path is retired.

## Clean-room rules

- Write behaviour, data shapes, and pseudocode. Do not paste Descript source, minified bundles, decompiled JavaScript, or recovered assets.
- Tag claims **static** (read from a file or spec), **observed** (seen while something ran), or **inferred** (a conclusion from those).
- Use only an account and media you own. Do not bypass paywalls, credits, or rate limits, and do not extract other people's data or server-side prompts.
- Keep captures out of git. `.gitignore` excludes `captures/`, `*.har`, `*.saz`, `*.asar`, `.env`, and credential files. Redact bearer tokens before sharing a HAR.
- Deep decompilation of Descript's web bundles needs an explicit go. Descript's terms are reported to restrict decompiling the app; that report is unverified here. Public API docs, this OpenAPI summary, and building from the pseudocode do not wait on that check.

## How the docs are organized

| Path | What it is |
| --- | --- |
| [DESCRIPT_RE_PLAN.md](DESCRIPT_RE_PLAN.md) | Current plan. Scope is locked. Desktop ASAR work is finished. |
| [docs/architecture.md](docs/architecture.md) | Thin Electron shell, `web.descript.com`, and `descriptapi.com`. |
| [docs/feature-inventory.md](docs/feature-inventory.md) | Polish-clip features mapped to API operations and an open-source stack. |
| [docs/api-notes.md](docs/api-notes.md) | Request and response shapes from the staging OpenAPI (2026-10-19). |
| [docs/reuse-rescript.md](docs/reuse-rescript.md) | Whether to study [wassgha/rescript](https://github.com/wassgha/rescript) or rebuild the editor. |
| [docs/grokbot-rea.md](docs/grokbot-rea.md) | REA on Grok Bot. No Claude Desktop setup. |
| [docs/pseudocode/](docs/pseudocode/) | Pipeline, caption style, burn-in, editor, voiceover, overlays, and later AI specs. |
| [docs/descript-analysis/](docs/descript-analysis/) | Public-help notes for skin smoothing, object removal, and voice clone. |

## Next steps

1. Optional: create a Descript API token on a **test Drive** and probe one import plus one agent job. Record real `job_state` timing and credit counts in `docs/api-notes.md`. Do not commit the token.
2. Record three fixture clips you own (clean speech, fillers plus retakes, noisy audio) outside git, under `captures/` or another ignored path.
3. Build from [docs/pseudocode/polish-pipeline.md](docs/pseudocode/polish-pipeline.md) and [docs/pseudocode/editor/overview.md](docs/pseudocode/editor/overview.md). Default backend is the open stack: filler words stay ignored, and caption style is a local `CaptionStyle`. Burn-in is optional. A Descript `POST /v1/jobs/agent` job is the alternate backend and does not carry style.
4. Leave eye contact as a research note. It is not the same feature as skin smoothing. A voice clone waits on [docs/pseudocode/voice-consent.md](docs/pseudocode/voice-consent.md); punch-in voiceover does not.

Working hypothesis, not a decision: a public-API job plus a rescript-like transcript editor is a better Polish Clips MVP than cloning the Descript web app. The current rescript `LICENSE` is PolyForm Noncommercial, so read [docs/reuse-rescript.md](docs/reuse-rescript.md) before copying any of that code.
