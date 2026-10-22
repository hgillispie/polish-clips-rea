# Show wordless media in script (Beta)

> **Signed-in result (2026-10-22):** the project stored `wordlessMediaEllipses: false` explicitly at creation, and both wordless flags were at their defaults. The font file is still not located. Details: [signed-in-gaps.md](signed-in-gaps.md).

## Keys and defaults (decompiled)

| Layer | Key | Default |
| --- | --- | --- |
| Local preference (new-project default) | `Project.showWordlessMedia` (redux `project.defaultShowWordlessMedia`) | `false` |
| Project document | `settings.wordlessMediaEllipses` | absent (off) |
| Effective switch | `isStoryboard && settings.wordlessMediaEllipses === true` | Only new-model ("storyboard") projects can show it |
| Flags | `wordless-media-ellipses` (default false), `wordless-media-ellipses-kill-switch` (default true) | See [README.md](README.md#where-each-toggle-lives-decompiled) |

Project actions: `TOGGLE_WORDLESS_MEDIA` flips the setting. The Project Settings dialog dispatches it on save when the value changed. `SET_WORDLESS_MEDIA {on}` sets it unless the project stored an explicit `false`; the flag watcher uses it. A toggle first **saves the project** and then refreshes the script ("save project before refreshing and applying wordless media changes"), because the script text model is rebuilt with or without the extra runs.

UI copy: Preferences: "If on, new projects will visualize sections of the script that don't contain speech as waveforms." Project Settings: "Show waveforms to indicate sections of the script that don't contain speech." Both carry a Beta badge.

## What counts as wordless media (decompiled)

Computed per script clip, only on the **main composition track**:

| Clip kind | Wordless runs |
| --- | --- |
| AI speech, gap clips | None (gap clips keep their own pause representation) |
| Non-script clips without an alignment that are not scratch text | None |
| Clips with **no transcript words** (b-roll, music, untranscribed or still-transcribing media), or script clips | **One run for the whole clip**, if it is at least 0.2 s long. A cut ("ignored") clip uses its full audio duration |
| Transcribed clips | **Leading:** from the clip start to the first word, if ≥ 0.2 s. **Between words and trailing:** a gap of `g` seconds between words (or from the last word to the clip end) makes a run when `g ≥ 0.7 s`. The run covers `g − 0.5 s`, starting 0.5 s after the previous word, so short natural pauses stay plain text |

Constants: bar width `0.2 s` per glyph, padding `0.5 s`. Thresholds: `0.2 s` (leading, or no words) and `0.7 s` (between or after words).

## How it becomes script text (decompiled)

Descript's script is a rich-text document whose characters map to media time. Wordless media is **inserted as text** into each clip's rendered string, interleaved with the clip's other inline components (markers, notes, embedded tracks) in time order.

1. **Bar values.** For each run, the client reads the source file's precomputed **energy envelope** (`audio.energies`: unsigned 16-bit loudness samples at `hz` per second, computed locally per file and cached). It averages them into one value per 0.2 s, treats values below a noise floor (65 of 65535) as 0, and normalizes by a ceiling of 6 % of full scale (20 % for script clips, which we read as clips that embed another composition, **inferred**), clamped to 1. Then it scales by the clip's gain over the maximum gain of 4. While energies are still being computed, bars are `-1` (rendered flat and pulsing).
2. **Glyphs.** Each bar value becomes one of six box-drawing characters chosen by sixths of the range: `─ ━ │ ┃ ┄ ┅`, low to high. A run is `" " + glyphs + " "` (prefix and suffix spaces depend on position).
3. **Font.** The run is styled with a custom webfont, **`DescriptWordlessMedia`**, in the secondary foreground color (**static-bundle**, CSS). The font redraws those six code points as waveform bars of increasing height. So the "waveform" is literally text, and selection, the caret, the playhead and copy all work with no special layout.
4. **Attributes on the run** (`WordlessMedia`): `isBlankCardGap` (an empty scene card's gap), `firstWordlessMediaOfTauId` (set on the first run of a clip, used to anchor a transcription-progress badge), `isStillComputingEnergies`, `isBlocked`.
5. **Decoration states** (**static-bundle** CSS plus **decompiled** component):
   - **cut**: line-through,
   - **transcribing or computing**: a 3 s stepped opacity pulse, plus a "transcribing N %" badge above the first run,
   - **playhead inside**: blue caret,
   - **hover**: the hover-word overlay skips wordless runs. The playhead overlay draws as a slim bar instead of a word chip.
6. **Paragraph shape.** A clip that is only wordless media can render as its own block (`wordlessMediaScriptClipWithNewline` renders as a `div`). Otherwise the run is an inline `span`.

## Editing rules (decompiled)

- Typing inside a wordless run is refused: "Writing is not allowed in word gaps." While the clip transcribes: "Writing is not allowed while audio is transcribing."
- Transcript correction on a run is refused: "Word gaps cannot be corrected."
- Selecting a run and deleting or cutting it works like any text range: it maps back to that media time range. Splits caused by wordless runs (`didWordlessMediaSplit`) are tracked so a deletion that spans one stays consistent.
- Drag and drop has its own target, `ScriptPinToWordlessMedia`, so a track can be pinned to a wordless span the same way it pins to a word.
- Underlord: with `underlord-wordless-media-no-match` on, agent text anchors that only match across wordless spans are rejected instead of resolving to a much longer range.
