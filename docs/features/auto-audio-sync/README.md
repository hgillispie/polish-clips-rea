# Auto audio sync

Line up N recordings of the same session by their sound. The recordings can be several cameras, a lav and a phone, or a Zoom H6 and a GoPro. The result is a synced group that multicam, highlight scoring and the timeline can use.

This feature **supersedes** [../../pseudocode/editor/audio-waveform-align.md](../../pseudocode/editor/audio-waveform-align.md), which only handles a pair, a single envelope and a 30 s window. It feeds [../../pseudocode/automatic-multicam.md](../../pseudocode/automatic-multicam.md).

## User stories

- I drop 3 camera files and 1 recorder file of a 50-minute podcast, press **Sync**, and get one multicam group in under a minute. The recorder audio is the master, and the cameras sit on angles.
- I drop a whole SD-card dump of 140 files from a shoot day. Sync sorts them into **sessions** by overlap (interview A, B-roll walk, interview B) and syncs inside each session. Files that match nothing stay in a "No match" bin.
- A camera stopped and restarted (two files). Both files snap into the same lane at the right spots.
- The GoPro drifts 0.2 s over an hour against the recorder. Sync corrects it, so lips stay in sync at minute 55.
- One clip is wrong by a frame or two. I nudge it with `,`/`.` (1 frame) or `Shift`+`,`/`.` (10 ms audio), and the confidence badge turns to "manual".

## Descript evidence (decompiled, observed-network)

**Preconditions.** Descript's Autosync works on a **sequence** and refuses when:
- fewer than 2 tracks have audio ("a muted camera cannot sync")
- any clip has a speed change

**Result shape.**
- `shiftedTrackCount`, `shiftedClipCount`, `skippedClipCount`
- `alignedScenes[{trackLabels}]`: groups of tracks that matched each other
- `loneSceneTrackLabels`: tracks that matched nothing
- `noOpReason ∈ not_enough_tracks | all_lone_scenes | already_synced | playback_speed_adjusted`

**Apply and run.**
- Applying is one commit, `{prependSeconds, shifts}`.
- The work is server-side. A legacy `/multi_track_sync/sync` endpoint is being replaced by a "multi_track_sync prediction model" behind the `multi-track-sync-predictions` flag (off on Hunter's account).
- The agent tool `autosync_sequence {sequenceRefId}` gives up after 8 minutes.
- A separate manual A/V offset input exists (`ed-av-sync-option` true).

**What we take.**
- Clusters ("scenes") plus lone tracks are the right result model.
- One undoable commit.
- An explicit no-op reason in the toast.

**What we do differently (design).**
- **Speed-changed clips.** We do not refuse them. We sync on source time, before speed is applied.
- **Batch grouping.** Large file sets are grouped automatically.
- **Drift correction.** Built in.
- **Confidence and nudge.** A per-clip confidence score with a manual nudge.
- **Silent clips.** A path for clips with no audio.

## UX (design)

- **Entry points.**
  - The media bin: select files, then "Sync by audio".
  - The timeline: select clips on different tracks, then "Sync".
  - The import dialog: a "Sync these files" checkbox, on when files share a folder and their creation times overlap.
- **Progress.** "Analyzing audio 3/7… Matching… Placing…" with a Cancel button. Results stream in per session.
- **Result panel.**
  - One row per session, with a lane per device.
  - Each clip has a confidence chip: green ≥ 0.8, amber 0.5–0.8, red < 0.5 (not placed), grey = manual.
  - A drift note appears when one was applied ("+38 ppm corrected").
  - Actions: **Apply**, **Choose master audio**, **Re-sync selected**, **Unsync**.
- **Nudge.** When a clip is selected in a synced group, the arrow keys nudge it relative to the master. A waveform overlay of master and clip shows the alignment, and the zoom auto-centres on the nearest transient.
- **No match.**
  - These clips are listed with the reason: "no shared sound found", "no audio track", or "audio too quiet".
  - Options: "Place by timecode", "Place by file time", or "Place manually".

## Inputs / outputs

```text
input:
  clips: MediaClip[]            # files or timeline clips; each may lack audio
  options:
    master: clip_id | "auto"    # auto = best SNR + longest + external recorder heuristics
    max_offset_s: number | null # null = unbounded (session-level search)
    drift: "auto" | "off" | "force"
    use_timecode: bool = true
    use_file_time: bool = true
output:
  SyncResult { sessions: SyncSession[], unplaced: Unplaced[], report }
```

## Algorithm (design)

1. **Features per clip.** Mono at 8 kHz, 10 ms hop:
   - an **onset-strength envelope** (spectral flux on a log-mel spectrogram)
   - **chroma** (12-bin, for music-heavy material)
   - **loudness**
   - **landmark fingerprints**: spectrogram peak pairs (Wang 2003), which are robust to level, EQ and distance

   Each clip is computed once and cached.
2. **Hints.**
   - **Embedded timecode** (SMPTE from QuickTime `tmcd`, or BWF `time_reference`) is decisive when it is present and consistent across devices, but it is still confirmed by audio.
   - **File creation and modification time** narrows the search window to ±(drift budget + 120 s).
   - Both hints are recorded and none is trusted alone.
3. **Candidate pairs.**
   - Few files (n ≤ 8): all pairs.
   - Many files: first an **inverted landmark index**. Each file's hashes vote for `(other_file, offset)`. Only pairs with at least K = 20 consistent votes go on. This is how fingerprint search scales without O(n²) correlation.
4. **Coarse offset per pair.**
   - FFT cross-correlation of the onset envelopes, with GCC-PHAT weighting by default (Knapp & Carter 1976). PHAT whitens the spectrum, which sharpens the peak under room reverb and different mic colour.
   - Compute it over the full overlap allowed by the hints.
   - Keep the top 3 peaks.
5. **Fine offset.**
   - Around each coarse peak (±50 ms), run GCC-PHAT on 8 kHz PCM, then 48 kHz PCM, with parabolic interpolation for **sub-sample** precision.
   - The target is ≤ 1 ms. Under 1/4 frame at 60 fps is about 4 ms.
6. **Confidence per pair.**
   - Combine three things: the peak-to-sidelobe ratio (PSR) of the fine correlation, agreement between the envelope lag and the landmark-vote lag (≤ 20 ms), and an **overlap-window consistency check**. The consistency check splits the overlap into 4 windows, estimates the lag in each, and needs a spread of ≤ 10 ms after drift correction.
   - Map the result to 0..1 with a logistic fitted on labelled pairs.
7. **Drift.**
   - Use the per-window lags from step 6. Fit `lag(t) = a + b·t` with RANSAC.
   - If `|b| > 5 ppm`, R² > 0.9 and the overlap is over 10 min, apply a **speed factor** `1 + b` to the clip. It is resampled on playback and render, never baked.
   - Reject `|b| > 500 ppm`, which signals a wrong match or variable-frame-rate weirdness, and fall back to piecewise placement.
   - Clock tolerances of tens of ppm are typical for consumer devices (design assumption; measure on fixtures). That is enough to drift a few frames per hour.
8. **Global placement per session.** This is a graph:
   - nodes are clips
   - edges are confident pair offsets with weight = confidence
   - connected components (with edges ≥ 0.5) are **sessions**

   Within a session, solve **least squares** for each clip's start time, `t_j − t_i = offset_ij` weighted by confidence, with the master fixed at 0. Then drop edges whose residual is over 15 ms and re-solve. A chain of overlaps (A–B, B–C, where A and C never overlap) syncs correctly through B.
9. **Same-device continuation.**
   - Clips from the same device (matched by camera model, serial and filename pattern) **cannot overlap** in time. Add that as a constraint.
   - A clip that matched nothing but belongs to a device lane with known neighbours is placed by file time inside that lane and marked `placed_by: file_time`.
10. **No-audio fallback,** in this order:
    1. Timecode.
    2. **Visual sync.** Cross-correlate the frame-difference energy (flash, clap, slate, cut-in) with another camera's motion energy. Use it only when a visual event peak is sharp (PSR ≥ 6).
    3. File time.
    4. Manual.

    Each placement is labelled with its method.
11. **Apply.**
    - One commit: create or update the `SyncGroup`, set clip offsets and speed factors, and set the group's master audio.
    - Mute the non-master audio by default, keeping the audio so it can be switched on later.
    - Word timings of any transcript on moved media are re-anchored, so they stay right without re-transcribing.

## Models / APIs (options)

All of this is classical DSP, with no paid models: numpy/scipy FFT and librosa onset/chroma. Landmark fingerprints can be our own simple Wang-style implementation. Chromaprint is an option, but it is tuned for file identity rather than offsets.

Prior art for comparison:
- BBC `audio-offset-finder` ([GitHub](https://github.com/bbc/audio-offset-finder)): MFCC cross-correlation
- DaVinci Resolve's "auto sync audio based on waveform"
- PluralEyes

Our differences are the clustering of many files, drift handling, confidence scores and the silent-clip path.

Papers:
- Knapp & Carter, "The generalized correlation method for estimation of time delay", IEEE TASSP 1976 ([doi](https://doi.org/10.1109/TASSP.1976.1162830))
- Wang, "An Industrial-Strength Audio Search Algorithm", ISMIR 2003 ([PDF](https://www.ee.columbia.edu/~dpwe/papers/Wang03-shazam.pdf))

## Data model

```text
SyncGroup
  id, name, master_audio_clip_id
  members: [{ clip_id, media_id, device_key, offset_s, speed, confidence, placed_by, residual_ms }]
      placed_by ∈ audio | timecode | visual | file_time | manual
  sessions_detected_at, algo_version
  hints: [{ clip_id, kind: "timecode"|"file_time", value }]
SyncResult.report
  pairs_tested, pairs_matched, drift_applied: [{clip_id, ppm}], unplaced: [{clip_id, reason}]
  no_op_reason?: "not_enough_audio" | "no_overlap" | "already_synced"
```

## Edge cases

| Case | Behaviour |
| --- | --- |
| Identical music playing in two separate sessions (event DJ) | Several strong peaks. Require a consistent lag across all 4 windows, and prefer the session with matching file time. Otherwise ask the user |
| Repeated sound (metronome, loop) | PSR is low, so the clip is amber. Landmark votes break the tie; if they cannot, place by file time |
| One clip with a speed change already applied | Sync source time before speed. Recompute the timeline position afterwards |
| Variable frame rate phone video | Audio is the clock. Video maps through presentation timestamps (PTS), so VFR does not affect the offset |
| Clip fully inside another | Normal case. The overlap equals the shorter clip |
| Very long files (4 h stream) | Coarse step on 50 ms envelopes over the full length, then the fine step only near peaks. Memory is O(length/10 ms) |
| Muted camera with on-camera mic far away | It works: the PHAT weighting copes with low SNR. Very low SNR leaves it amber |
| Master has gaps (recorder stopped) | The session solve still works through the other overlaps |

## Eval / metrics

- **Fixtures:** 30 owned multi-device sessions with ground-truth offsets from a clap slate, plus synthetic tests: known offsets with added reverb and noise at 0–20 dB SNR, speed perturbation of ±200 ppm, cut-up files.
- **Metrics:**
  - offset error p50/p95 (targets ≤ 2 ms / ≤ 10 ms)
  - wrong-match rate (error > 100 ms): target < 0.5%
  - session-grouping adjusted Rand index
  - drift error in ppm
  - runtime per hour of audio
  - share of clips needing a manual nudge
- **Product:** time from drop to synced group; how often users nudge after an auto sync.

## MVP vs later

- **MVP:**
  - onset envelope + GCC-PHAT coarse and fine
  - pair confidence
  - least-squares placement for ≤ 8 clips
  - drift on/off
  - one commit
  - nudge keys
  - a no-match list
- **Later:**
  - landmark index for 100+ files
  - device-lane constraints
  - visual sync for silent clips
  - timecode reading
  - chroma for music
  - auto-session naming from transcripts
  - multi-track recorder polyphonic files (pick the best channel)
