# Editor settings: pseudocode

Our versions of the three Descript toggles analyzed in [../../descript-analysis/editor-settings/](../../descript-analysis/editor-settings/). They are written against our transcript and timeline model ([../transcript-model.md](../transcript-model.md), [../editor/timeline-model.md](../editor/timeline-model.md), [../editor/audio-mixer.md](../editor/audio-mixer.md)).

| File | Setting |
| --- | --- |
| [settings-model.md](settings-model.md) | Where the three values live: user defaults, project settings, per-clip flags |
| [room-tone.md](room-tone.md) | Use room tone on gap clips |
| [smart-transitions.md](smart-transitions.md) | Apply Smart transitions to new scenes |
| [wordless-media.md](wordless-media.md) | Show wordless media in script |

Where we differ from Descript, on purpose:

1. **Room tone is extracted locally first.** We pick the quietest non-speech spans from the transcript and loudness envelope in the worker, so it works with no server model. A server "synthesize" step can replace it later.
2. **Loops crossfade.** Descript butt-joins its loops. We crossfade 50 ms between loop iterations so a short sample does not click.
3. **Smart transitions also fire for agent-created scenes**, through the same post-edit hook.
