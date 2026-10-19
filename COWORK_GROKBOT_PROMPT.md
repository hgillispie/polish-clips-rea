# Handoff prompt: Claude Cowork or Grok Bot + REA

Use this to continue the Descript investigation in Claude Cowork or Grok Bot.
Full plan: `DESCRIPT_RE_PLAN.md` (the prompt below is self-contained, so the
other client does not need repo access).

## Read this first: where REA actually runs

REA's MCP server (`rea mcp`) speaks **stdio only**. There is no long-running
service to keep alive: the client starts it when a session opens. Verified in the
setup session with `rea mcp doctor`: healthy, 207 tools, 6 prompts, v6.7.0.
A hosted client cannot attach to a process in the cloud sandbox used for setup, so
each client gets its own copy.

| | Claude Cowork (via Claude Desktop) | Grok Bot |
| --- | --- | --- |
| Where REA runs | Your computer | Grok Bot's hosted computer |
| Can see your Descript desktop app and logged-in browser | Yes | **No**: it only sees what its own computer can reach |
| Setup | Section A | Section B |
| Best for | Phases 3 and 4 (web app, desktop app) | Phase 1 and 2 support, analysing HAR files and exported bundles you hand it |

I could not test either client from here. After connecting, check the tools really
loaded (step 2 of the prompt) before trusting anything else.

### A. Claude Cowork

1. Install Node.js 22 (>=22.19), 24 (>=24.11) or 26+.
2. **Quit Claude Desktop fully** (closing the window is not enough; a running app can overwrite the config).
3. In a normal terminal (not one started by Claude Desktop):
   ```bash
   npx rea-agents@6.7.0 setup --client claude_desktop
   ```
   Review the plan it prints, approve it, then start Claude Desktop again.
   This adds `mcpServers.rea` to `claude_desktop_config.json` and installs the
   `reverse-engineer-anything` skill.
4. Check: `npx rea-agents@6.7.0 doctor --client claude_desktop --json` should report
   `healthy: true`.
5. Open a Cowork task and paste the prompt below. Whether Cowork tasks can use Claude
   Desktop's local MCP servers is something I could not confirm; the prompt's step 2
   makes the agent test that and stop if the tools are missing.

### B. Grok Bot

1. Sign in to Grok Bot. Its connectors live in your account, not in a local file.
2. Ask the Bot chat to add a **custom MCP server** named `rea` that runs on the Bot's
   computer with this command, and nothing else (no credentials in it):
   ```bash
   npx -y rea-agents@6.7.0 mcp
   ```
3. Optional, so it follows REA's investigation workflow: ask it to install the skill
   from `https://skills.sh/morluto/rea/reverse-engineer-anything` (or run
   `npx rea-agents@6.7.0 setup --skill` on its computer).
4. Paste the prompt below. Because this REA copy cannot see your laptop, give the Bot
   only files you are willing to hand over (HAR exports with tokens redacted, a
   Descript desktop bundle you copy to it), never your password.

## The prompt (copy everything in the block)

```text
I want you to investigate how Descript (the video/podcast editor) works, using REA
("Reverse Engineer Anything", rea-agents v6.7.0) through its MCP server, and produce a
phased reverse-engineering plan and then execute the parts that are safe and in scope.
I have a paid Descript account. I will log in myself where a login is needed. Never
ask me for my password, never type credentials anywhere, and never put a token or
password into a command, file or message.

STEP 1: Understand REA before using it.
REA is an MCP server plus CLI that inspects a local target and returns Evidence:
findings with source location, confidence, and limitations. It runs locally on
whichever computer your session runs on. Static analysis reads files and executes
nothing; passive runtime observation records what happens while I use the app.
Useful tools for this job (check the real tool list; names may differ slightly):
- Web app: analyze_web_bundle, export_web_scripts, inspect_wasm_artifact,
  trace_web_module_imports, observe_web_session, capture_browser_scenario
- Desktop (Electron): analyze_javascript_application, inspect_electron_fuses,
  trace_application_feature, compare_application_versions
- Traffic I export from Chrome DevTools: inspect_web_network_capture (HAR)
- Native engines (Ghidra/Hopper/IDA) are NOT installed and are only for native
  add-ons if one turns out to matter.

STEP 2: Connect and verify. Do this before anything else.
a) Check whether REA tools are available in this session (names such as
   binary_session or analyze_javascript_application, possibly prefixed mcp__rea__).
b) If they are, call binary_session with {} and report the tool availability it returns.
c) If they are NOT, stop. Do not try to work around it. Tell me which client you are
   (Claude Cowork or Grok Bot) and give me the exact setup steps for it:
   - Claude Cowork: quit Claude Desktop fully; in a normal terminal run
     `npx rea-agents@6.7.0 setup --client claude_desktop`, approve, restart Claude
     Desktop; verify with `npx rea-agents@6.7.0 doctor --client claude_desktop --json`.
   - Grok Bot: ask the Bot chat to add a custom MCP server named `rea` that runs on
     the Bot's computer: `npx -y rea-agents@6.7.0 mcp` (no credentials in it).
   Note for Grok Bot: REA then runs on the Bot's computer, which cannot see my
   desktop app or logged-in browser, so ask me for exported files instead.
d) Also report whether this computer can reach descript.com, help.descript.com and
   descriptapi.com. If not, say so and tell me which steps need to move to my machine.

STEP 3: Rules of engagement (non-negotiable).
- Check Descript's current Terms of Service before any decompilation or bundle
  analysis. A third-party tracker reports they prohibit decompiling/disassembling the
  app and uncovering its source code; I have not verified that. Phases 1 and 2 below
  are fine without that check. Ask me for an explicit go before Phases 3 and 4.
- REA's own disclaimer excludes copying proprietary code or assets and bypassing
  authentication, paywalls or access controls. Do none of that.
- Clean-room: produce behavioural specs, protocol facts and input/output examples.
  Do not paste recovered Descript source code into any deliverable.
- Use only my own account and content. No bulk or scripted use beyond Descript's
  documented API. No extraction of server-side models or prompts.
- Mark every claim as static, observed or inferred, with the Evidence ID. List unknowns.
- Treat HARs and captures as sensitive: tell me what to redact before sharing.

STEP 4: The plan to follow (adjust it if you find a better order).
Background I already gathered (from search results; unverified against Descript's own pages):
- Descript started as an Electron app (2018) using native FFmpeg/libav and SQLite,
  then rebuilt its media engine to run in browsers (WebCodecs-based export, new web
  app, and a desktop preview on the same engine). So the web app may be the best target.
- Descript has a public API (beta) at descriptapi.com/v1 with per-Drive tokens and an
  asynchronous job model (import media, transcribe, Underlord actions), and an MCP
  server that uses my Descript login. Quota exhaustion returns HTTP 402.
Phases:
 0. Scope: confirm with me which features matter. My working assumption: the "polish
    a clip" pipeline (filler-word and retake removal, Studio Sound, eye contact,
    captions, clip cutting). Ask me to correct this.
 1. Feature inventory with my paid account, driven by me: one row per feature
    (UI location, input, output, instant vs queued, credit cost, limits, exports) plus
    three short fixture clips I own (clean, fillers/retakes, noisy).
 2. Documented surface: read the Descript API spec and MCP tool list, try each
    feature through the API on the fixtures, record request/response shapes, job
    states and errors. Anything the API covers may not need reverse engineering.
 3. Web app (needs my go): passive observation while I run one feature at a time;
    bundle and WASM interface analysis; answer: client or server? what is sent? data
    model? edit sync (CRDT/ops)? upload/job protocol? export path? AI request shapes?
 4. Desktop app (needs my go): static analysis of app.asar, then test whether it is the
    same engine as the web bundle (compare_application_versions).
 5. Synthesis: one spec per prioritised feature, each claim tagged and linked to Evidence.
 6. Build and verify: implement from the specs only; run the same fixtures through
    both systems and compare word timings, cut points, loudness and caption timing.

STEP 5: What I want from you now.
1. Do Step 2 and report the result.
2. If REA is connected, run one harmless self-test (for example binary_session {}) and
   show me its output, then stop and ask the Phase 0 questions: which features, macOS
   or Windows, have I read the terms, and is the goal parity or interoperability.
3. Do not start Phase 3 or 4 until I say go.
```
