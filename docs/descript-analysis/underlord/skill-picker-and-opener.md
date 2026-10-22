# Underlord: skill picker, "Improve this video" opener, suggestion cards

From the signed build's app and 8211 chunks (**decompiled**), Hunter's screenshots, and his capture (**observed-network**). No skill bodies or template prompts are reproduced here.

## Skill picker (`/` in the prompt box, or the skills button)

- **Source of items.** The catalog that the system prompt also carries.
  - It is the `user_skills` set: 11 global skills in the observed catalog, listed in [observed-network.md](observed-network.md#skills-catalog-and-skills-observed-network).
  - Personal skills join the set when `use-personal-skills` is on. They are stored as `/agent-instructions` items, `type: "skill"`.
  - Hidden `agent_guidance` skills never show in the picker.
  - Hunter's screenshot shows 11 rows plus a **Create skill** footer. The catalog lists `create-skill` among the 11, so the picker either has one more entry than the prompt catalog or renders `create-skill` as the footer. Which one is unresolved (see gaps).
- **Picker actions** (static-bundle, agent slice): `SET_SKILLS_CATALOG`, `INVALIDATE_SKILLS_CATALOG`, `SET_PENDING_OPEN_SKILLS_PICKER`, `SET_PENDING_TRY_SKILL`, `RUN_SKILL_IN_UNDERLORD`.
- **What choosing a skill sends** (decompiled saga for `RUN_SKILL_IN_UNDERLORD {skillId, skillName, submitImmediately = true, newChat = true}`):
  1. Without an open project: create a new project from the Drive view, wait for it to load, then continue. If there is no Drive, show a toast.
  2. Open the Agent sidebar. If `submitImmediately` is false, put the skill into the prompt box as a pending chip (`SET_PENDING_TRY_SKILL`) and stop.
  3. Otherwise, clear the pending chip, start a new chat if `newChat`, and dispatch `SEND_AGENT_REQUEST`:
     - `prompt` is the literal markup `<skill id="{skillId}">{skillName}</skill> ` (one trailing space). The model sees that tag and calls `load_skill`.
     - `agentTemplate` is undefined.
     - `context` is the current @-chips.
     - `analyticsCtx` is `{agent_session_id, num_project_files, initiated_by: "user", origin: "agent"}`.
  - The capture has no skill-picker run: both `load_skill` calls followed typed prompts. The `<skill>` tag is therefore **decompiled**, not observed.
- **Create skill** runs the `create-skill` skill. That skill walks the user through a draft, and the model saves the result with `save_skill`. `delete_skill` exists as well. Both tools were in the 72 sent.

## "Improve this video" card (AI Tools menu)

Component `ImproveThisVideoCard({projectId, compositionId})` (decompiled, 8211):

- **Title.** "Improve this video" when the composition has video, otherwise "Improve this project". Subtitle: "Let Underlord plan your edits with smart suggestions".
- **On view.** Sends telemetry `agent_chat_suggestion_viewed {kind: emptyProject | existingProject, context: "ai_tools_menu_suggestions"}`.
- **On click.** Telemetry `agent_chat_suggestion_clicked {button: "improve_this_video"}`, then one of two paths.
  - **Skills UX on** (a store selector; for Hunter the flags imply yes): dispatch `RUN_SKILL_IN_UNDERLORD {skillId: "ask-underlord-for-suggestions", skillName: <display name>, newChat: false}`. This is the picker path above, staying in the current chat.
  - **Skills UX off:**
    1. Open the Agent sidebar.
    2. Look up the public template whose slug starts with `ask-underlord-for-suggestions` (a fixed slug with a random suffix) in `/agent_templates`.
    3. Take its `prompt`. If it is missing, fall back to a built-in one-line request for creative suggestions.
    4. Dispatch `SEND_AGENT_REQUEST {prompt, agentTemplate, context, analyticsCtx{origin: "agent_template"}}`.
- **What the agent does next** matches Hunter's prompt B5 in [prompt-catalog.md](prompt-catalog.md). He typed the request rather than clicking the card, and the model loaded the same skill.

## "Want me to improve this video?" opener

The literal string is **not in any signed chunk we hold** (searched all of them). The candidates are:

1. **Agent-panel empty state** (`use-suggestion-empty-state`, true for Hunter; decompiled).
   - When a chat is empty and the project has content, the panel shows suggestion chips built from `suggestedTemplates` (agent templates), shuffled when the composition is empty.
   - It needs `agentBrain` feature access and agent access.
   - Clicking a chip sends `SEND_AGENT_REQUEST` with that template's prompt.
2. **The auto-open experiment.**
   - `exp-auto-open-agent-sidebar` and `exp-agent-new-chat-on-load` are both `experiment-treatment` for Hunter. The sidebar opens on project load with a fresh chat.
   - The opener line is then either a template title or server-provided copy (**inferred**).

What it sends when accepted is, either way, the `ask-underlord-for-suggestions` skill or template prompt above. Its exact trigger condition and copy source remain a gap.

## Other agent-side actions seen in the bundle (static-bundle)

`OPEN_AGENT_UNDERLORD_FROM_HOME`, `SET_AGENT_DRAFT_INPUT`, `SET_SHOW_AGENT_TEMPLATES_MODAL`, `SET_SHOW_REMIX_LAYOUT_PACK_MODAL`, `UPDATE_CREATIVE_BRIEF_PARAMS`, `ENTER_AGENT_PLANNING`/`EXIT_AGENT_PLANNING`, `LOG_AGENT_FEEDBACK`, `LOG_AGENT_END_STATE`, `LOG_AGENT_REVERT`, `PROVIDER_DOWN`.
