# Studio Sound–class enhance

Produce a new audio asset that sounds cleaner than the source. Keep the source file. Do not rewrite transcript timestamps: enhancement is a parallel asset, switched on at playback and export.

"Studio Sound" is Descript's product name. Polish Clips implements the same *class* of effect (denoise / voice enhance). Intensity in the Descript UI is **inferred** from product behaviour. The OpenAPI has no intensity field (static).

## Input / output

```text
input:
  asset            MediaAsset
  options
    backend        "deepfilter" | "rnnoise" | "ffmpeg_afftdn" | "descript_prompt"
    strength       "low" | "medium" | "high"     # local backends only
    project_id     string | null                 # required for descript_prompt
    composition_id string | null
output:
  enhanced         MediaAsset     # path to wav or the project's new state
  report
    backend        string
    peak_dbfs      number | null
    credits_used   integer | null
```

## Local algorithm

```text
function enhance(asset, options) -> (enhanced, report):
  wav = ffmpeg_decode(asset.path, sample_rate=48000, channels=1, format="wav")
  if options.backend == "ffmpeg_afftdn":
    out = ffmpeg_afftdn(wav, strength_to_nr(options.strength))
  else if options.backend == "rnnoise":
    out = rnnoise_denoise(wav)
  else if options.backend == "deepfilter":
    out = deepfilternet(wav, strength=options.strength)
  else:
    fail "unknown local backend"

  out = loudness_normalize(out, target_lufs=-16, true_peak_dbfs=-1.5)
  peak = measure_peak_dbfs(out)
  if peak > -0.1:
    fail "limiter failed; refuse to write a clipped master"

  enhanced = MediaAsset(
    id=new_id(),
    filename=asset.filename + ".enhanced.wav",
    path=out,
    duration_seconds=asset.duration_seconds,
    has_video=false,
    ...
  )
  return enhanced, report(backend=options.backend, peak_dbfs=peak, credits_used=null)

function strength_to_nr(strength) -> number:
  # ffmpeg afftdn noise reduction in dB. Weak baseline, not the product default.
  return { low: 6, medium: 12, high: 20 }[strength]
```

Default local backend for an MVP that cares about quality: `deepfilter` if the model file is available, else `rnnoise`. Offer `ffmpeg_afftdn` as an always-on fallback so a missing model does not block captions and cuts.

Playback when enhance is enabled uses the enhanced asset for **audio** and the original asset for **video**, aligned on the source clock (durations must match within 50 ms; if they do not, discard the enhanced file and surface an error). Cuts still come from `kept_ranges` on the transcript, applied to both.

## Descript API option

No Studio Sound operation and no strength parameter (static). Prompt:

```text
Add Studio Sound to the speech in this composition.
Use a medium intensity if you can set one. Do not change the cut or the transcript.
```

"Medium intensity" is a request, not a field. `result.agent_response` is the only description of what ran. `project_changed` must be true to count as applied; if it is false, report "agent made no edit" and do not claim the audio changed.

This spends AI credits. HTTP 402 stops the step. Full client: [underlord-agent-job.md](underlord-agent-job.md).

The API path does not return a separate wav. The enhanced audio lives inside the Descript project. A following `POST /jobs/publish` (or a local download of `download_url`) is how you hear it. Publishing is secondary; for a probe, the operator can open `project_url`.

## Errors

| Case | Behaviour |
| --- | --- |
| Decode failure | Stop the enhance stage. The rest of the pipeline can continue on the original audio |
| Model file missing | Fall back from `deepfilter` to `rnnoise`, then to `ffmpeg_afftdn`. Record the fallback in `report.backend` |
| Output duration mismatch > 50 ms | Discard `enhanced`. Leave the toggle off |
| HTTP 402 on the prompt path | Stop. Message is insufficient AI credits. Do not retry in a loop |
| HTTP 429 | Honor `Retry-After`, bounded as in the agent job spec |
| `project_changed: false` | Success of the HTTP job, failure of the effect. Surface `agent_response` |

## Build options

| Option | Cost | Quality |
| --- | --- | --- |
| DeepFilterNet-class local model | CPU/GPU time, no Descript credits | Best open default |
| RNNoise-class | Cheap CPU | Fine for stationary noise |
| ffmpeg `afftdn` | Always available | Weak; label it as a fallback in the UI |
| Underlord "add studio sound" | `ai_credits_used` on the job | Black box; may match Descript's product effect more closely. Intensity is unverified |
