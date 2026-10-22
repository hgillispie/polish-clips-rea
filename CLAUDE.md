# Instructions for coding agents (Claude Code, Cursor, etc.)

**Product on this branch:** an Arcade-style **interactive product demo builder**
(capture extension → click-through demo editor → embeddable player with analytics).
It is **not** a video editor. Ignore anything about Descript / Polish Clips; that lives on
branch `claude/compassionate-pascal-apg87s`.

Read in order: `HANDOFF.md` → `ARCADE_RE_PLAN.md` → `docs/architecture.md` →
`docs/pseudocode/model/flow-model.md` + `docs/schemas/flow.schema.json` →
the area you are implementing.

Rules:
- Clean-room. Implement from the specs in `docs/`. Never fetch, paste or port Arcade's
  bundles, CRX code or decompiled output into this repo. Do not reuse Arcade's brand,
  assets, extension id, or hostnames; use our own names (`demo.<ourdomain>` etc.).
- Keep the Flow JSON shape compatible with `docs/schemas/flow.schema.json`; update the
  schema and `flow-model.md` together if you change it.
- The step builder (`docs/pseudocode/capture/step-builder.md`) must be a pure function with
  fixture-based unit tests; same for branching resolution and the coordinate math.
- Evidence tags stay in docs. If you discover behaviour by experiment, tag it `observed`
  and say how.
- Do not commit captures, HARs, tokens or raw third-party bundles (see `.gitignore`).
