# REA on Grok Bot

REA ("Reverse Engineer Anything", npm package `rea-agents` **6.7.0**) is the MCP server for this investigation. It is already connected on the Grok Bot computer as:

```bash
npx -y rea-agents@6.7.0 mcp
```

The server speaks stdio. The Bot starts it with the session. There is no process to keep alive, and there is no Claude Desktop or Cowork setup.

Session check (observed, 2026-10-19): the server advertised about 207 tools, Node on the Bot computer is 22.x.

## What this REA copy can see

The Bot computer can fetch public docs and can analyze files you place on it. It does not see `/Applications/Descript.app` or a logged-in Chrome on your Mac. The thin-shell conclusion in [architecture.md](architecture.md) already came from a static look at that app; do not repeat desktop ASAR work unless a new question is about the shell itself.

`rea analyze-javascript-application` on the Mac failed on an `xcrun` / Swift ownership helper (observed). Package metadata and strings were sufficient.

## If a later session has no REA tools

Ask the Bot to add a custom MCP server named `rea` whose command is exactly:

```bash
npx -y rea-agents@6.7.0 mcp
```

Do not put a Descript token, password, or cookie in that command. Optional workflow skill, only if you want REA's investigation checklist installed on that machine: `npx rea-agents@6.7.0 setup --skill`, or the skill published at `https://skills.sh/morluto/rea/reverse-engineer-anything`.

## If you hand the Bot a capture

- Redact `Authorization` headers, cookies, and signed media URLs first.
- Keep the file under `captures/` so git ignores it.
- Prefer a HAR (`inspect-web-network-capture`) over a full web bundle. Bundle decompilation still needs the terms go recorded in [DESCRIPT_RE_PLAN.md](../DESCRIPT_RE_PLAN.md).

## Prompt when an API gap needs a passive look

```text
Use REA on the redacted HAR at <path>. Do not call Descript. Report which
requests ran during <one feature>, which hosts they hit, and what is still
unknown. Behavioural findings only. Mark each claim static, observed, or
inferred. Do not paste response bodies that contain tokens or source.
```
