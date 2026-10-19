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

That overlaps Polish Clips on import, word timings, fillers, captions, and clip cutting. It does not advertise retake detection, a Studio Sound–class denoiser, or eye contact.

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

Use it to see what a small transcript editor feels like: word objects, cut ranges, a worker for ASR, ffmpeg for decode and export, a timeline next to the transcript. Implement those ideas from [pseudocode/transcript-model.md](pseudocode/transcript-model.md) and [pseudocode/polish-pipeline.md](pseudocode/polish-pipeline.md).

One behaviour we deliberately do differently: rescript's filler control **cuts** words. Polish Clips **ignores** them (strikethrough, reversible, skipped on playback and on export). A fork that only flipped a boolean would still be a derivative work of their code. Write the ignore model ourselves.

| Approach | When it is the right call |
| --- | --- |
| Rebuild from the pseudocode | Default. Commercial product, ignore semantics, our own enhance and retake stages |
| Noncommercial spike that runs rescript | Learning the UX on a fixture. Keep it in a separate checkout, not in this repo |
| Commercial license from the author | Only after they offer one. Re-evaluate "editor foundation" then |
| Pin an old MIT tag | Only after reading that tag's license file and confirming MIT applies to the files you would use |

## What Polish Clips still adds beside any editor

- Retake detection that keeps the last take.
- A swappable enhance stage (RNNoise-class locally, or a Descript agent prompt).
- Optional Descript API backend for import, Underlord, and publish ([api-notes.md](api-notes.md)).
- Eye contact left out until a probe says the API can do it.
