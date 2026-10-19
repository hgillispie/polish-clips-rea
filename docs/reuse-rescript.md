# Reuse or rebuild: wassgha/rescript

[wassgha/rescript](https://github.com/wassgha/rescript) is a browser transcript editor (also packaged with Electron). The 2026-10-19 session reported roughly 944 GitHub stars. Product site: [getrescript.com](https://getrescript.com/). This note is from the public README and `LICENSE` on `master`, read 2026-10-19. No rescript source is copied into this repo.

## What it already does (public README)

- Local transcription with word timestamps (transformers.js Whisper in a worker; WebGPU, WASM fallback) and pyannote speaker labels.
- Import an existing SRT, VTT, or JSON transcript.
- Delete words → cut ranges on the original media. Preview skips those ranges. Export concatenates kept ranges with ffmpeg.wasm.
- One-click filler cut (`um`, `uh`, and similar) and silence cut (pauses at or above 0.3 s).
- Timeline: waveform, word bar, split, trim, draggable word edges.
- Export video, audio, captions (SRT/VTT/JSON and document formats), and a few NLE timelines.
- Stack: Next.js, React, TypeScript, Tailwind, zustand, Electron.

That overlaps Polish Clips on import, word timings, fillers, captions, and clip cutting. It does not advertise retake detection, a Studio Sound–class denoiser, caption burn-in styling, a multi-track mixer, or eye contact.

## Public modules that line up with our specs

File names below are from the public tree of `wassgha/rescript` on `main`, listed 2026-10-19 (**static** filenames only). No file bodies are copied here. Commercial Polish Clips still cannot vendor them: the `LICENSE` on that tree is PolyForm Noncommercial 1.0.0.

| Their path | Lines up with | Gap we still specify ourselves |
| --- | --- | --- |
| `components/Timeline.tsx` | [pseudocode/editor/timeline-model.md](pseudocode/editor/timeline-model.md), [ui-surface.md](pseudocode/editor/ui-surface.md) | Our tracks are video, audio, caption, overlay. Their timeline is a word bar plus cut ranges |
| `components/TranscriptPanel.tsx`, `TranscriptTextLayer.tsx`, `TranscriptToolsMenu.tsx`, `TranscriptScrollIndicator.tsx` | Transcript panel wires in [ui-surface.md](pseudocode/editor/ui-surface.md) | Strikethrough ignore, not hard delete |
| `hooks/useTranscriptSelection.ts`, `hooks/useTranscriptPlayheadFollow.ts`, `hooks/useCutRanges.ts` | [selection-and-edits.md](pseudocode/editor/selection-and-edits.md) | Ripple / roll / slip plus restore of ignored words |
| `lib/transcript.ts`, `lib/transcriptText.ts`, `lib/parseTranscript.ts` | [pseudocode/transcript-model.md](pseudocode/transcript-model.md) | `ignored`, filler, and retake flags |
| `lib/serializeTranscript.ts`, `lib/serializeTimeline.ts` | `polish.transcript.v1` and `polish.project.v1` | Our JSON shapes, not theirs. Tests next to those files show they serialize export formats |
| `lib/ffmpeg.ts`, `electron/ffmpegRunner.ts`, `workers/transcription.worker.ts` | Decode, ASR worker, export encode in [export-render.md](pseudocode/editor/export-render.md) and [caption-burnin.md](pseudocode/caption-burnin.md) | ASS / drawtext burn-in and the layer composite |
| `lib/fillers.ts`, `lib/silences.ts`, `lib/edits.ts` | Filler and cut behaviour | We ignore fillers; they cut them. Silence removal is not a Polish Clips MVP stage |
| `components/Editor.tsx`, `MediaPreview.tsx`, `ExportDialog.tsx` | Preview and export regions | Inspector for `CaptionStyle` and the mixer |
| `lib/exportArgs.ts` | Encode argument construction | Our presets in export-render |

Study those names to see how a small editor is split. Implement from our pseudocode.

## License (read this before copying anything)

GitHub's license field for the repo is **"Other"**. The `LICENSE` file on `master` is **PolyForm Noncommercial 1.0.0** ([polyformproject.org/licenses/noncommercial/1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0)).

The README states the practical consequence: use, modification, and sharing are for noncommercial purposes; commercial use, including reselling or redistributing for a fee, is not granted; the copyright notice must be retained; commercial licensing is a separate conversation with the author. The same README says **older releases that were published under MIT stay MIT for those versions only**.

So:

- Do not vendor, subtree, or paste current `master` into Polish Clips.
- A commercial MVP does not get to "just depend on the package" either, unless the author grants a commercial license.
- An MIT-tagged historical release is a different artifact. If someone later wants that code, they pin the exact tag, read that tag's `LICENSE`, and record the decision. This PR does not do that.
- Noncommercial experiments (personal study, a public-research prototype with no commercial plan) fit the current license. Polish Clips as a product does not assume that.

## Recommendation

**Rebuild the editor concepts. Study rescript as a behavioural reference.**

Use it to see how a small transcript editor is split: timeline component, transcript panel, ffmpeg helpers, serializers. Implement the editor from [pseudocode/editor/overview.md](pseudocode/editor/overview.md) and the pipeline from [pseudocode/polish-pipeline.md](pseudocode/polish-pipeline.md).

One behaviour we deliberately do differently: rescript's filler control **cuts** words. Polish Clips **ignores** them (strikethrough, reversible, skipped on playback and on export). A fork that only flipped a boolean would still be a derivative work of their code. Write the ignore model ourselves.

| Approach | When it is the right call |
| --- | --- |
| Rebuild from the pseudocode | Default. Commercial product, ignore semantics, our own enhance and retake stages |
| Noncommercial spike that runs rescript | Learning the UX on a fixture. Keep it in a separate checkout, not in this repo |
| Commercial license from the author | Only after they offer one. Re-evaluate "editor foundation" then |
| Pin an old MIT tag | Only after reading that tag's license file and confirming MIT applies to the files you would use |

## What Polish Clips still adds beside any editor

- Retake detection that keeps the last take.
- A swappable enhance stage (RNNoise-class locally, or a Descript agent prompt), including a clip effect node.
- Local caption style and optional burn-in. Their export writes sidecar captions; it does not take a `CaptionStyle`.
- Multi-track layers and a mixer (gain, fades, highpass / lowpass).
- Optional Descript API backend for import, Underlord, and publish ([api-notes.md](api-notes.md)).
- Eye contact left out until a probe says the API can do it.
