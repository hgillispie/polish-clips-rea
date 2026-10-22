# Create-clips workflow (macro skill example)

What Descript's `create-clips` macro does (see [../../descript-analysis/underlord/skill-library.md](../../descript-analysis/underlord/skill-library.md)), redone as our skill plus tool calls. Highlight finding is the backlog item; here it is a single tool so the workflow is complete.

## Input / output

```text
input:   "make 3 vertical clips under 60s about pricing"
output:  3 new compositions, each with source ranges, 9:16 layout, captions, title; one summary message
```

## Flow

```text
1. model: load_skill("create-clips")
2. model: enter_planning
3. model: query_compositions                              -> source composition, duration
4. model: find_highlights(composition, count=3, max_s=60, topic="pricing")
     tool: transcript -> candidate windows (sentence-aligned, 15–60 s)
           score with a side completion (hook strength, self-contained, topic match) -> top N, non-overlapping
           returns [{start, end, title, why}]
5. model: todo_write([...one item per clip...]); presents the plan with the 3 picks
6. user:  [Approve]  (is_plan_approval)
7. model: exit_planning
8. per clip:
     create_composition(name=title, ranges=[{start, end}])
     edit_script(cut fillers and false starts inside the range)
     shorten_gaps(min=0.6, target=0.3)
     set_layout(orientation="9:16", focal="active_speaker", captions=true)
     screenshot(time = 2s)                                 -> model checks framing
     todo_write(mark done)
9. post-turn lint: every clip <= max_s, no clip starts mid-word, captions present
10. final message: table of clips with durations and links
```
