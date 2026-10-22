# Agent loop

## Input / output

```text
input:
  project_id        string
  composition_id    string
  chat_id           string | null      # null = new chat
  message
    content         string
    context         [ContextChip]      # selected text range, scene, media ids
    is_plan_approval boolean
  harness           Harness            # model, prompt sections, toolset, limits
output (SSE events, in order):
  turn_started            {chat_id, turn_id}
  assistant_chunk*        {assistant_message_id, content}
  tool_call_started*      {tool_call_id, name, label}
  tool_call_progress*     {tool_call_id, label}
  tool_call_completed*    {tool_call_id, label, status}
  doc_committed*          {revision_id}             # ours: client refetches or applies patch
  turn_completed          {usage, credits_used}
  | turn_failed {reason}  | turn_cancelled
```

```text
Harness
  id, model_main, model_multimodal, context_limit
  max_loop_main = 25, max_loop_global = 300
  reasoning | temperature, max_completion_tokens
  prompt_sections [SectionId]
  toolset [ToolName]
```

## Turn controller

```text
function run_turn(req) -> stream<Event>:
  chat  = load_or_create_chat(req.chat_id, req.project_id)
  turn  = new_turn(chat, base_revision = current_revision(req.project_id))
  emit turn_started{chat.id, turn.id}
  append(chat, UserMessage(req.message, turn.id))

  state = { doc: load_doc(req.project_id, turn.base_revision),
            composition_id: req.composition_id,
            planning: chat.planning }
  tools  = filter_tools(req.harness.toolset, account_flags, admin_disabled_groups, state)
  system = build_system_prompt(req.harness, user_memory, skills_catalog(), credit_status, admin_disabled_groups)

  try:
    state = agent_loop(chat, system, tools, state, req.harness, call_source="main")
    state = post_turn_hooks(chat, system, tools, state, req.harness)
    if state.doc != load_doc(turn.base_revision):
      rev = commit_doc(req.project_id, state.doc, parent=turn.base_revision, turn=turn.id)
      emit doc_committed{rev}
    emit turn_completed{usage = turn.usage, credits_used = charge(turn.usage)}
  catch Cancelled:  emit turn_cancelled
  catch OutOfCredits: emit turn_failed{"insufficient_credits"}
  catch e: emit turn_failed{classify(e)}
```

## Agent loop

```text
function agent_loop(chat, system, tools, state, h, call_source) -> state:
  for i in 1 .. h.max_loop_main:
    if global_loop_counter(turn) >= h.max_loop_global: break
    messages = [system] + history_for_model(chat)        # drops rollback markers, applies summaries
    messages = apply_context_policy(messages, tools, h)   # see below
    mark_cache_breakpoints(messages)                      # last text part of the last 2 user/tool msgs

    reply = stream_completion(h, messages, tools, call_source)   # emits assistant_chunk as text arrives
    append(chat, AssistantMessage(reply.content, reply.tool_calls, reply.reasoning))
    add_usage(turn, reply.usage)

    if reply.tool_calls is empty: return state

    for call in reply.tool_calls:                         # sequential: tools mutate the doc
      emit tool_call_started{call.id, call.name, label = tools[call.name].in_progress_label}
      if state.planning and tools[call.name].mutates: 
        result = ToolResult(content = "You are in planning mode. Present the plan and wait for approval.")
      else:
        args = validate(tools[call.name].schema, parse_json(call.arguments))  # error text goes back to model
        result = tools[call.name].execute(ctx(state, chat, emit_progress), args)
      if result.updated_state: state = result.updated_state
      append(chat, ToolMessage(call.id, ref = short_ref(), content = result.content, images = result.images))
      emit tool_call_completed{call.id, result.label or completed_label, status}
  append(chat, SystemNote("Loop limit reached; summarize what was done and what is left."))
  final = stream_completion(h, [system] + history_for_model(chat), tools = [], call_source)
  append(chat, AssistantMessage(final.content))
  return state
```

Ours enforces planning mode in code (Descript only tells the model). `mutates` is declared per tool.

## Completion call

```text
function stream_completion(h, messages, tools, call_source) -> Reply:
  body = { model: h.model_main, messages, tools: to_json_schema(tools), stream: true,
           stream_options: {include_usage: true}, max_completion_tokens: h.max_completion_tokens,
           ...(h.reasoning ? {reasoning: h.reasoning} : {temperature: h.temperature}),
           metadata: {turn_id, call_source} }
  for attempt in 1..3:
    try:
      return parse_sse(POST(gateway + "/chat/completions", body))
    catch RetryableStreamError if attempt < 3 and not cancelled:
      sleep(500ms * 2^(attempt-1))

function parse_sse(resp) -> Reply:
  content = ""; reasoning = []; calls = {}           # index -> {id, name, arguments}
  for line in resp.lines():
    if not line.startswith("data: "): continue
    if line == "data: [DONE]": break
    chunk = json(line[6:])
    if chunk.usage: usage = chunk.usage
    d = chunk.choices[0].delta
    if d.content: content += d.content; emit assistant_chunk
    if d.reasoning_details: merge_reasoning(reasoning, d.reasoning_details)
    for tc in d.tool_calls or []:
      slot = calls[tc.index] ||= {}
      slot.id ||= tc.id; slot.name ||= tc.function.name
      slot.arguments += tc.function.arguments or ""
    if chunk.choices[0].finish_reason == "error": raise ProviderDown
  return Reply(content, values(calls) sorted by index, reasoning, usage)
```

## Context policy

```text
function apply_context_policy(messages, tools, h):
  est   = chars(messages)/4 + chars(json(tools))/4
  used  = max(est, last_measured_input_tokens or 0)
  hard  = min(0.8*h.context_limit, h.context_limit - min(32k + 8k, h.context_limit/2))
  if used <= hard:
    if used >= 0.5*h.context_limit and not advisory_sent:
      inject SystemNote("Context is filling. Use compact_context on old tool results or summarize_context.")
    return messages
  if compaction_savings(messages) >= 0.15: return auto_compact(messages)      # shrink old tool args/results to stubs with refs
  if can_summarize(messages):          return force_summarize(messages)       # side call writes summary; replaces range
  raise ContextExhausted
```

On a provider `context_length_exceeded` error: compact once, then retry the call.

## Post-turn hooks

```text
function post_turn_hooks(chat, system, tools, state, h):
  issues = lint(state.doc, changed_since(turn.base_revision))
  if flag("post_turn_verification"):
    verdict = completion(h.model_main, verification_prompt(chat.last_turn, issues), call_source="post-turn-verification",
                         response_format = {ok: bool, follow_up: string})
    if not verdict.ok:
      append(chat, SystemNote(verdict.follow_up))
      state = agent_loop(chat, system, tools, state, h with max_loop_main = 5, "main")
  return state
```

## Planning and approval

```text
tool enter_planning():  chat.planning = true;  return "Planning. Query freely, then present the plan with todo_write."
tool exit_planning():   require last user message.is_plan_approval; chat.planning = false; return "Approved."

UI: when the last assistant message follows enter_planning and has a todo list, show [Approve plan].
    Approve -> run_turn({content: "Approved", is_plan_approval: true})
```

## Rollback

```text
function rollback_to(chat, user_message_id):
  turn = turn_of(user_message_id)
  set_current_revision(project, turn.base_revision)       # pointer move; later revisions kept for redo
  removed = messages_at_or_after(chat, user_message_id)
  mark(removed, rolled_back_at = now)
  append(chat, RollbackMarker(to = turn.created_at, message_id = user_message_id,
                              removed_user_messages = removed.where(role == user)))
  # the history sent to the model skips rolled-back messages and markers
```
