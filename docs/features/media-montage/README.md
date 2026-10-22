# Create media montage

Turn a folder of clips and photos into a music-driven montage: a trip, an event, a product, a "year in review".
- **Beat detection** sets the cut grid.
- **Shot selection** picks the best and most varied moments.
- A **pacing curve** shapes the energy.
- **Ken Burns** moves give stills life.

Pseudocode: [../../pseudocode/media-montage.md](../../pseudocode/media-montage.md).

## Evidence

- **Descript.** No montage tool was observed. The closest tools are `generate_video` / `generate_images` and the stock providers ([stock-asset-providers](../../pseudocode/editor/stock-asset-providers.md)). This feature is **design**.
- **Public research.**
  - Beat tracking:
    - librosa `beat_track` ([docs](https://librosa.org/doc/0.11.0/generated/librosa.beat.beat_track.html))
    - madmom DBN beat/downbeat tracking ([madmom](https://github.com/CPJKU/madmom))
    - Beat This! ([arXiv 2407.21658](https://arxiv.org/abs/2407.21658)), state of the art without a DBN post-processor
  - Aesthetic and quality scoring with CLIP-style embeddings, e.g. the LAION aesthetic predictor ([GitHub](https://github.com/christophschuhmann/improved-aesthetic-predictor)).
  - Shot boundaries: TransNetV2 ([2008.04838](https://arxiv.org/abs/2008.04838)).

## User stories

- I select 80 clips and 40 photos from a weekend and a song, choose "60 s, energetic", and get a montage with:
  - cuts on beats and drops, faster cuts in the chorus
  - no blurry or shaky shots, no near-duplicates
  - people's faces shown more than empty scenery
  - photos panning gently toward faces
- I choose "Follow the story" and the montage goes in time order (by capture time). "Best first" opens with the strongest shots.
- I pin 3 must-include shots and exclude one person's shots.

## UX (design)

- **Setup.**
  - Media picker (folder / selection / project).
  - Music (library / mine / none).
  - Duration: song length, or a target, or the beat-snapped nearest bar.
  - Aspect.
  - Vibe: Calm / Balanced / Energetic / Custom curve.
  - Order: Chronological / Best first / Mixed.
  - Toggles: Include photos, Use clip audio (dialogue moments), Title card.
- **Result.**
  - A timeline with beat markers and the pacing curve drawn above it.
  - Each slot shows the chosen shot plus 3 alternates (click to swap).
  - Drag the curve's control points to re-pace; the system re-solves.
  - Lock slots.
- **Alerts.** "Not enough distinct footage for 90 s at Energetic: 47 s max, or reuse shots?"

## Inputs / outputs

```text
input: media[] (video, image), music?, target_s?, aspect, vibe | curve, order, pins[], excludes[], use_clip_audio
output: Montage { slots: [{t0, t1, asset, in_s, out_s, motion?: KenBurns, transition}], music, composition_id }
```

## Algorithm (design)

1. **Music analysis.**
   - Beats, downbeats, tempo, and section boundaries (self-similarity novelty on chroma + MFCC: intro, verse, chorus, drop).
   - A per-beat energy curve (onset strength + RMS).
   - Without music: a fixed grid at the vibe tempo (Calm 70, Balanced 100, Energetic 128 BPM), with no audio.
2. **Pacing curve.** The target shot length in beats for each section:
   - Calm: 4–8 beats.
   - Balanced: 2–4.
   - Energetic: 1–2, with ½-beat stutters on drops.

   The curve is modulated by the music energy: `len_beats = base · (1.5 − energy_norm)`, quantized to {½, 1, 2, 4, 8}. Section boundaries always cut, and the strongest shots go at the chorus and drop. A user-drawn curve overrides this.
3. **Slots.** Walk the beat grid with the curve to produce slots `[t0, t1]` aligned to beats (downbeats preferred for longer slots). Total = the target (trim or fade the music at a bar boundary).
4. **Shot pool.** Per video: shots via the [visual track](../visual-descriptions/README.md) or TransNetV2. Each shot is split into sub-candidates of 0.5–6 s around its "best" window (max of sharpness × motion interest × face presence). Per photo: one candidate. Features:
   - **quality**: blur, exposure, shake, noise; reject below thresholds
   - **aesthetic** score
   - **interest**: faces + expression, motion energy, visual-track salience
   - **embedding** (SigLIP) for variety
   - **capture time** (EXIF / QuickTime creation date) for ordering
   - **orientation** fit to the aspect
   - **audio interest**: laughter or a spoken highlight, used when `use_clip_audio`
5. **Assignment.** This is a sequence assignment problem:
   - **Maximize** `Σ fit(slot, shot) − variety penalties`.
   - `fit`:
     - quality × aesthetic × interest
     - motion intensity matched to slot energy (high-motion shots in high-energy slots)
     - shot duration ≥ slot length (photos always fit)
     - an orientation penalty
   - **Variety:**
     - no shot reused
     - adjacent shots must have embedding cosine < 0.85
     - in any window of 5 slots, at most 2 from the same source file
     - a scene-type rotation (people / place / detail) via visual-track `shot_size` and entities
   - **Order constraint:** for chronological, monotone in capture time, solved by DP over (slot, time-sorted shot index). For best-first or mixed, a greedy pass with lookahead 3, then local swaps.
   - Pins are placed first, at the nearest-time slot (chronological) or the highest-energy slot (best first).
6. **In-shot timing.** For video, choose the in-point so the shot's motion peak or action lands on the slot's downbeat (or ~⅓ in). Speed: 1.0 by default. Energetic allows speed ramps 0.5–1.5 on high-motion shots and slow-mo for 60/120 fps sources.
7. **Ken Burns for stills.**
   - Start and end rectangles at the aspect.
   - Zoom 1.00→1.12 (Calm) up to 1.00→1.25 (Energetic).
   - Pan toward the salient region: faces first, else the saliency map. Direction alternates between consecutive stills.
   - Easing in-out cubic; duration = the slot.
   - Never crop a face partly out.
   - Portrait photos in landscape slots: blurred-fill background plus a gentle move.
8. **Transitions.**
   - Hard cut by default (on the beat).
   - Crossfade between sections in Calm.
   - Whip/flash on drops in Energetic.
   - Match cuts (later): when adjacent shots have similar composition or motion direction, use a straight cut.
9. **Audio.**
   - Music bed normalized to −14 LUFS (platform loudness).
   - With `use_clip_audio`, a chosen dialogue or laugh moment ducks the music by −10 dB for its duration.
   - Fade the music on the last bar.
10. **Assemble** as a composition: slots as ranges or image layers with keyframes. One commit.

## Models / APIs

- Beats: Beat This! (MIT), madmom, librosa as the CPU fallback.
- Aesthetic: the LAION aesthetic predictor on CLIP ViT-L/14, or a SigLIP-based variant.
- Faces: SCRFD.
- Saliency: a simple spectral-residual method or a learned saliency model.
- No paid APIs required. An optional VLM provides "story" ordering hints.

## Data model

```text
Montage { id, params, music: {asset_id, tempo, beats: s[], downbeats: s[], sections: [{t0, t1, label, energy}]},
          curve: [{t, beats_per_shot}], slots: [{id, t0, t1, asset_id, in_s, out_s, speed, kenburns?: {from_rect, to_rect, ease},
          transition: {kind, frames}, locked, alternates: asset_ref[]}], composition_id }
ShotCandidate { asset_id, in_s, out_s, quality, aesthetic, interest, motion, emb, capture_time, orientation }
```

## Edge cases

- **Too little footage.** Reuse the best shots at different in-points, or shorten the montage. Ask the user; the default is to shorten.
- **All photos.** A slideshow mode: Ken Burns on every slot; slot length ≥ 2 beats so movement is readable.
- **Clips without capture time.** Order by file name, then by modification time.
- **Vertical and horizontal mix.** Choose the majority aspect or the user's; others get smart crop (faces/saliency) or blurred fill.
- **Copyright of music.** Library tracks carry license metadata. "Mine" music shows a reminder that the platform may mute it.
- **Long song vs short target.** Choose a contiguous song section that ends on a phrase (the chorus end) instead of fading mid-phrase.

## Eval / metrics

- Beat-alignment error of cuts (p95 ≤ 20 ms).
- Reject-rate audit: no blurry or shaky shots in output ≥ 98%.
- Variety (adjacent cosine distribution).
- Human ratings for "feels on-beat", "shows the best moments" and "not repetitive".
- Pairwise preference vs. random-on-beat and vs. a capture-time-only baseline.

## MVP vs later

- **MVP:** beats + downbeats; a vibe presets curve; quality filter; greedy assignment with variety rules; chronological and best-first; Ken Burns for stills; hard cuts; music fade.
- **Later:** section detection; a user-drawn curve; speed ramps; match cuts; clip-audio moments; story ordering via VLM; per-person include/exclude (face clustering, opt-in, never named without the user).
