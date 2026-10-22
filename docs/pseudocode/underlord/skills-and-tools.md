# Skills and tools

## Skill

```text
Skill
  id            kebab-case string, unique
  name          display name
  description   one line; this is all the model sees until it loads the skill
  body          markdown playbook (steps, rules, examples); may contain {{other-skill-id}}
  source        global | team | user
  invokable     boolean   # shown in the user's skills picker as a slash action
  viewable      boolean   # user can open and read the body
  gate          [flag]    # all must be on for the account
```

### Catalog in the system prompt

```text
function skills_catalog(account) -> text:
  visible = [s for s in global_skills + team_skills(account) + user_skills(account) if all_on(s.gate, account)]
  return "## Skills\nLoad a skill with load_skill before doing a task it covers.\n" +
         join(visible, s -> "- `" + s.id + "` (" + s.source + "): " + s.description)
```

### load_skill

```text
tool load_skill(id, source = "global", name = null) -> ToolResult:
  s = find_skill(source, id) or find_skill_by_name(source, name)
  if not s: return "No skill with id " + id + ". Available: " + ids(visible)
  body = s.body
  refs = regex_all(body, /\{\{([a-z0-9-]+)\}\}/)
  footer = ""
  for r in unique(refs):
    if exists(r): footer += "- {{" + r + "}} is a skill: load_skill(\"" + r + "\") when you reach that step.\n"
    else:         footer += "- {{" + r + "}} has no skill body; do that step yourself with the tools.\n"
  return ToolResult(content = body + "\n\n---\nReferenced skills:\n" + footer, label = "Loaded " + s.name)
```

Descript leaves `{{ref}}` unexpanded and adds no footer, and 14 of its referenced ids have no body. The footer is our fix so the model never goes looking for a missing skill.

### Personal skills

```text
tool save_skill(mode: create|update, id?, name, description, content) -> ToolResult
tool delete_skill(id) -> ToolResult       # only after the user confirmed in chat; we also require a UI confirm
```

## Tool contract

```text
Tool
  name, description, schema (JSON Schema), mutates: bool, group: AdminGroup | null
  in_progress_label, completed_label
  execute(ctx, args) -> ToolResult
ToolResult
  content: string                 # always prefixed "[ref:xxxxx] " by the loop
  updated_state: State | null     # only if mutates
  images: [Image] | null
  label: string | null
ctx
  doc, composition_id, chat, emit_progress(label), services (render, stt, tts, gen, search), signal
```

Rules: errors are returned as `content` (`"Error: ..."`), not thrown, so the model can correct itself. Every mutating tool returns a short diff summary ("Cut 14 words (3.2 s) in paragraphs 4–6").

## Targets

```text
PositionTarget = {text: string, prefix?: string, suffix?: string, side: before|after}
               | {time: seconds} | {end: true}
RangeTarget    = {text: string, prefix?, suffix?} | {start: s, end: s}
               | {scene: index} | {scenes: [index]} | {paragraphs: [index]}
resolve_range(doc, target) -> (word_start, word_end) | error "ambiguous: N matches, add prefix/suffix"
```

Text targets are matched on the normalized transcript (case-folded, punctuation-stripped), and must match exactly once.

## Minimal tool set for plain-language transcript editing (v1)

| Tool | mutates | Does |
| --- | --- | --- |
| `query_script` | no | Markdown transcript with paragraph indexes, speakers, timecodes every N seconds, `~~cut~~` words, scene markers; filters by paragraphs, time or speaker |
| `find_in_script` | no | Text, regex, filler words, silence gaps over a threshold, speaker changes; returns target strings |
| `query_compositions` | no | Compositions and durations |
| `edit_script` | yes | Operations: `cut` (soft ignore), `delete`, `restore`, `replace_text` (correct the transcript only), `move` |
| `shorten_gaps` | yes | Pauses over X s shrink to Y s |
| `remove_fillers` | yes | Ignore filler words (wraps [../filler-removal.md](../filler-removal.md)) |
| `add_scene_boundary` / `remove_scene_boundary` | yes | Scene splits |
| `create_composition` | yes | New composition from ranges (used by clipping) |
| `set_layout` | yes | Orientation, crop focal point, captions on or off |
| `screenshot` | no | Renders frames at times; returns images |
| `todo_write`, `enter_planning`, `exit_planning` | no | Planning |
| `load_skill`, `edit_memory` | no | Skills and preferences |
| `compact_context`, `restore_context`, `summarize_context` | no | Context |

`edit_script` example:

```text
tool edit_script(composition_id, operations) -> ToolResult:
  doc = ctx.doc
  for op in operations:
    (a, b) = resolve_range(doc, op.target)  or return error
    match op.kind:
      cut:          doc = set_ignored(doc, a..b, true)
      restore:      doc = set_ignored(doc, a..b, false)
      delete:       doc = remove_words(doc, a..b)
      replace_text: doc = correct_words(doc, a..b, op.text)        # transcript only, no audio change
      move:         doc = move_words(doc, a..b, resolve_position(doc, op.to))
  return ToolResult(content = summarize_diff(ctx.doc, doc), updated_state = ctx.state with doc)
```
