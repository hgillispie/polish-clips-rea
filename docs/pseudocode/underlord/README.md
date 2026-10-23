# Underlord-style agent: pseudocode

Pseudocode for our own plain-language editing agent, modeled on what [../../descript-analysis/underlord/](../../descript-analysis/underlord/) found in Descript's client. It is written against our transcript and timeline model ([../transcript-model.md](../transcript-model.md), [../editor/timeline-model.md](../editor/timeline-model.md)), not Descript's document.

| File | Covers |
| --- | --- |
| [agent-loop.md](agent-loop.md) | Turn controller, completion call and stream parse, tool execution, loop caps, context budget, planning and approval, rollback |
| [skills-and-tools.md](skills-and-tools.md) | Skill catalog and `load_skill`, how `{{ref}}` sub-skills resolve, the tool contract, targets, the minimal tool set for transcript editing |
| [create-clips-workflow.md](create-clips-workflow.md) | The "make N short clips" macro, end to end, as one worked example of a skill driving tools |

Design choices (ours):

1. Run the loop **server-side** (in the Polish Clips worker), not in the browser. Descript runs it client-side by default because its document lives in the browser. Ours lives in the database, and a server loop also covers the API front door. The client renders the same SSE events as Descript's cloud mode.
2. Tools are **pure functions** `(doc, args) -> (doc', text)` plus a small set of async service tools (render, transcribe, generate). Each turn commits one document revision, so rollback is a pointer move.
3. Skills are markdown files in the repo, loaded on demand. The system prompt only carries their catalog.
