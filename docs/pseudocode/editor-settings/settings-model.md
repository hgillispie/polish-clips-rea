# Settings model

```text
UserDefaults                         # per user, synced to the account (Descript keeps these in local storage)
  room_tone_on_gap_clips   bool = true
  smart_transitions        bool = true
  show_wordless_media      bool = false

ProjectSettings                      # in the project document
  room_tone_on_gap_clips   bool | null    # null = off (old projects)
  show_wordless_media      bool | null    # null = off

Clip (gap)                           # see transcript-model
  room_tone                bool           # seeded from ProjectSettings at creation

Track
  suppress_room_tone       bool = false

MediaFile
  room_tone_file_id        string | null
  room_tone_job_id         string | null
  room_tone_requested      bool
```

```text
function new_project(user) -> Project:
  return Project(settings = {
    room_tone_on_gap_clips: user.defaults.room_tone_on_gap_clips,
    show_wordless_media:    user.defaults.show_wordless_media })

function save_project_settings(project, changes, set_as_default: bool):
  for (k, v) in changes:
    if project.settings[k] != v:
      project.settings[k] = v
      if set_as_default: user.defaults[k] = v
  if "room_tone_on_gap_clips" in changes and any_nonempty_gap_clip(project):
    ask "Apply to existing gap clips as well?"  -> on yes: set_room_tone_on_all_gaps(project, v)
  if "show_wordless_media" in changes:
    rebuild_script_view(project)
```

Smart transitions has no project field. It is read from `user.defaults` each time a scene is added.
