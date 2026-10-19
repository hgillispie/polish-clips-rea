# Plan: understanding how Descript works, using REA

Status: draft for review. Nothing in this plan has been run against Descript yet.

## 1. What REA is and how it works

REA ("Reverse Engineer Anything", `rea-agents` on npm, v6.7.0 installed) is an
MCP server plus a CLI. Your agent calls REA tools; REA inspects a local target
and returns **Evidence**: findings with their source location, a confidence
level, and the limits of what was observed. The agent turns that into
explanations or code. Everything runs locally.

Relevant to Descript:

| Descript surface | REA route | Needs a native engine (Ghidra/Hopper/IDA)? |
| --- | --- | --- |
| Web app (JS + WASM bundles) | `analyze-web-bundle`, `export-web-scripts`, `inspect-wasm-artifact`, `trace-web-module-imports` | No (WASM needs WABT) |
| Desktop app (Electron `app.asar`) | `analyze-javascript-application`, `inspect-electron-fuses`, `trace-application-feature` | No |
| Live behaviour (page or Electron) | `list-browser-targets` / `list-electron-targets`, `observe-web-session`, `capture-browser-scenario`, `capture-electron-scenario` | No |
| Saved traffic (HAR from DevTools, Fiddler SAZ) | `inspect-web-network-capture` | No |
| Native add-ons / media libs inside the desktop app | `inspect-artifact`, then Hopper / Ghidra / IDA | Yes, only if needed |

Two kinds of REA output, kept distinct on purpose: **static** (read from files,
nothing executed) and **passive runtime** (observed while *you* use the app). REA
labels which is which, so we can tell "the code contains X" from "X happened".

## 2. Install status (done in this session)

- Cloned `morluto/rea`; installed the CLI with `npm install --global rea-agents` (6.7.0).
- Ran `rea setup --client claude_code --yes`. That added an MCP entry to
  `/root/.claude.json` (backup at `/root/.claude.json.rea.backup`) and the skill at
  `/root/.claude/skills/reverse-engineer-anything`. `rea doctor` reports healthy for
  Node 22.22, the Claude Code registration and the skill.
- Smoke test: `rea analyze-javascript-application` on a small synthetic Electron app
  recovered both IPC channels, the `contextBridge` surface and the fetch endpoint.
- Hopper, Ghidra, IDA, JADX and Kuna are **not** installed. Only native-binary work
  needs them; the Electron/web path does not.
- Caveat: the MCP tools only load into a Claude Code session started *after*
  setup, so they are not callable in the session that ran the install. The CLI works now.

**This container cannot reach descript.com, help.descript.com or descriptapi.com**
(network policy; npm and GitHub work). It also has no Mac/Windows Descript app. So
the Descript analysis itself should run on **your machine**, where you are already
logged in. That also means I never need your password; please do not paste it anywhere.

## 3. Constraints to settle before Phase 3

1. **Terms of service.** A third-party tracker (ConductAtlas) reports that Descript's
   terms prohibit decompiling or disassembling the app and uncovering source code or
   trade secrets. I could not read Descript's own terms from here, so this is
   unverified. Someone should read the current terms (and ask legal if the output will
   feed a competing product) before Phases 3 and 4. Phases 1 and 2 use the product and
   its documented API as intended and do not raise this.
2. **REA's own rules.** REA's `DISCLAIMER.md` says it does not support copying
   proprietary software or reproducing its protected code and assets, or bypassing
   authentication or access controls. The plan is built around that.
3. **Clean-room split.** Analysis produces behavioural specs, protocol facts and
   input/output examples. Implementation happens from those specs, not from Descript
   code. Do not paste decompiled or recovered Descript source into the new codebase.
4. **Your own account and content only.** No bypassing the paywall, credit limits or
   rate limits; no bulk or scripted use beyond what the documented API allows; no
   attempt to extract other users' data or server-side models and prompts.
5. **Traffic captures are sensitive.** HARs contain session tokens and media URLs.
   Keep them out of git (this repo's `.gitignore` should exclude `captures/`), redact
   before sharing, and rotate the session when finished.

## 4. What is publicly known (from search results; the pages themselves were not reachable from here)

- Descript launched in 2018 as an **Electron** app and said Electron let it use web
  tech for the UI while keeping native C/C++ libraries such as FFmpeg/libav and SQLite.
- Descript later rebuilt the media engine so it runs in a browser, dropping those
  native dependencies. Its blog describes a **WebCodecs-based export pipeline**, a new
  web app, and a **desktop preview running on the same engine**.
  Implication: the web app is probably the richest and most current target, and the
  desktop app may now be a thin shell over the same engine rather than a separate
  codebase. Confirm in Phase 4 by diffing the two.
- Descript documents a **public API (beta)** at `descriptapi.com/v1/...` with
  token-per-Drive auth and an asynchronous job model (import media, transcribe, set up
  a composition; Underlord actions such as Studio Sound, filler-word removal and
  captions). Quota exhaustion returns HTTP 402. There is also a Descript **MCP server**
  that uses your Descript login instead of an API token.

## 5. Phases

### Phase 0: scope and sign-off (you, about 30 minutes)

- Pick the features that matter. Working assumption, based on this repo's name: the
  "polish a clip" pipeline (filler-word and retake removal, Studio Sound, eye contact,
  captions, clip cutting). **Correct this list if it is wrong**; it sets the priority of everything below.
- Read the current Descript terms (Section 3.1) and decide go/no-go for Phases 3 and 4.
- Tell me whether your desktop app is macOS or Windows.

Exit: a ranked feature list and a written go/no-go.

### Phase 1: feature inventory with your paid account (you drive, no reverse engineering)

The goal is to know what exists before asking how it works. For each feature, fill
one row of `feature-inventory.csv`:

`feature | where in UI | input | output | runs on (instant = likely local, queued = likely server) | credit or minute cost | limits/plan gating | export formats | screen-recording filename`

Candidate checklist (from memory and search; confirm each against your plan, add
what is missing):

- Transcript-based editing (delete words, cut media), multitrack timeline, scenes/layouts
- Underlord (AI co-editor) actions: remove filler words, remove retakes, Studio Sound,
  eye contact, create clips, captions, show notes/chapters, translate/dub
- Studio Sound, Eye Contact, Green Screen, Overdub / AI voices
- Recording: screen recording, Rooms (remote recording)
- Collaboration: comments, shared Drives, publish/share pages
- Export: video and audio formats, SRT, editor interchange formats (e.g. Premiere/FCPXML),
  transcript export
- Integrations: API, MCP, Zapier, Raycast

Also create **fixtures**: three short test clips you own (clean speech, speech with
fillers and retakes, noisy audio). Run each feature once on each fixture and keep the
inputs and outputs. These double as golden tests in Phase 6.

Exit: a complete inventory and fixtures. Timing matters too: record how long each
feature takes, because latency is the cheapest clue to local-versus-server work.

### Phase 2: the documented surface (API and MCP; sanctioned black-box)

- Read the OpenAPI spec and the MCP tool list. Create a token for a **test Drive**.
- Replay each Phase 1 feature through the API on the fixtures. Record request/response
  shapes, job states, polling behaviour, error codes and credit accounting.
- Output: `api-notes.md` mapping each UI feature to an API operation or noting that no
  API equivalent exists. Anything with an API equivalent may not need reverse
  engineering at all; building on the API could be the right answer for some features.

### Phase 3: the web app (REA runs on your machine; needs Section 3.1 go)

Install REA on your laptop and run `npx rea-agents setup` there (pick your agent,
restart it). Then, with Chrome open and logged in to Descript:

1. **Passive observation while you work.** Start Chrome with
   `--remote-debugging-port=9222`, then `list-browser-targets` and
   `observe-web-session` while you perform *one* feature at a time from the Phase 1
   list. Passive mode records requests, script sources and storage key names but not
   header values or raw bodies, which keeps tokens out of the evidence.
2. **Bundle analysis.** `analyze-web-bundle` / `export-web-scripts`, then
   `analyze-javascript-application` on the exported scripts. Use
   `recover-javascript-sources` (needs Wakaru) only if the bundles are minified past reading.
3. **WASM.** `inspect-wasm-artifact` (needs WABT) on the media-engine modules: imports,
   exports and sections only. This shows the engine's *interface* (what the JS side asks it to do).
4. **Scenarios.** Once you know the steps, `capture-browser-scenario` with declared
   actions gives a repeatable capture; `compare-web-captures` diffs two runs.

Questions this phase answers, per feature:

| Question | Evidence source |
| --- | --- |
| Client-side or server-side? | Network calls during the action versus none; WASM imports |
| What is sent to the server (audio, transcript, edit list, none)? | `observe-web-session` request metadata |
| Transcript data model: words, timestamps, speakers, confidence? | Exported scripts plus a transcript export you did yourself |
| How are edits stored and synced (operation log, CRDT, snapshot)? | WebSocket / sync endpoints, module graph |
| Upload and job protocol (chunking, signed URLs, polling or push)? | Request sequence for one import |
| Render/export path (WebCodecs versus server render) | Script graph; network during export |
| Where do AI features run, and what do their requests and responses look like? | Request shapes for Underlord actions |

### Phase 4: the desktop app (your machine; needs Section 3.1 go)

1. Locate the app bundle (macOS: inside `Descript.app`; Windows: the install directory
   containing `resources/app.asar`).
2. `inspect-electron-fuses`, then `analyze-javascript-application` on the ASAR (static;
   nothing executes). `trace-application-feature` follows a route, string or IPC channel
   through main, preload and renderer.
3. `compare-application-versions` between the desktop JS and the Phase 3 web bundles to
   test the "same engine" hypothesis. If they match, desktop adds little beyond file
   access, native menus and updates, and the web results already cover it.
4. `list-electron-targets` / `capture-electron-scenario` for passive runtime observation of IPC.
5. Native add-ons (`.node` files) only if something core lives there: `inspect-artifact`
   first, then install Ghidra or Hopper. Treat this as optional and expensive.

### Phase 5: synthesis

For each prioritised feature, one spec page:

- Behaviour (inputs, outputs, edge cases), with Phase 1 fixtures as examples
- Architecture (client/server split, data model, protocol), each claim linked to an
  Evidence ID and marked *static*, *observed* or *inferred*
- Unknowns, stated explicitly; REA marks what it could not establish
- Build options: use Descript's API, build on open components (for example FFmpeg,
  Whisper-class transcription, RNNoise-class denoising), or both. Compare cost and quality.

### Phase 6: build and verify

Implement from the specs only, then run the Phase 1 fixtures through both systems and
compare outputs (word timings, cut points, loudness, caption timing). Differences
become tickets or are accepted explicitly.

## 6. Prompts to use once REA is set up on your machine

```text
Use REA. I am logged in to Descript in Chrome on port 9222 with my own paid account.
Do not log in for me and do not send anything to Descript. Passively observe the
session while I run "Remove filler words" on my test clip, then report: which network
calls happened, what data left the browser, which script modules handled it, and
what remains unknown. Cite the Evidence for each claim and mark it static, observed or inferred.
```

```text
Use REA to analyze the Descript desktop app at <path to app.asar> statically. Do not
launch it. Report the main/preload/renderer split, IPC channels, native add-ons and
update mechanism, and say whether the renderer bundle matches the web bundle I
exported to <dir>. Do not reproduce source code; write behavioural findings only.
```

## 7. Open questions for you

1. Which features are the real target? (Section 5, Phase 0)
2. macOS or Windows desktop app?
3. Has anyone read Descript's current terms, and is Phases 3 and 4 approved?
4. Is the end goal parity inside your own product, or interoperability (for example
   importing and exporting Descript projects)? Interoperability might need only Phase 2
   plus export formats, and is the easiest to justify.
5. Is it acceptable to allow `descript.com` in this cloud environment's network policy?
   I would not recommend it. Logging in from a cloud container is awkward, and your
   machine already has the session and the desktop app.

## 8. Continuing in Claude Cowork or Grok Bot

`COWORK_GROKBOT_PROMPT.md` has a self-contained prompt plus connection steps for
each client. REA's MCP server is stdio-only, so there is nothing to keep running:
each client starts its own copy. Cowork (through Claude Desktop) runs it on your
computer, which is where your Descript login and desktop app are. Grok Bot runs it on
its own hosted computer, which cannot see them.

## 9. Cheat sheet

```bash
npm install --global rea-agents          # CLI
npx rea-agents setup                     # register with your agent, then restart it
rea doctor --client claude_code --json   # readiness
rea analyze-javascript-application /abs/path/to/app-or-asar --json
rea inspect-web-network-capture /abs/session.har har --json
rea update
```
