# Voice consent

Gate for any synthesizer that is meant to sound like a real person. The default fix for a bad line is a human punch-in, specified in [editor/voiceover.md](editor/voiceover.md). Descript’s clone and Regenerate behaviour is summarized in [../descript-analysis/voice-clone.md](../descript-analysis/voice-clone.md). We do not copy their consent script or their model host.

This feature is **later**. Shipping the editor does not require it.

## Types

```text
ConsentRecord
  id                 string
  speaker_label      string          # the person who spoke the consent
  statement_text     string          # the exact words they were asked to read
  audio_media_id     string          # their recording of that statement
  recorded_at        string          # ISO 8601
  locale             "en"            # consent recording is English in this version
  accepted           boolean
  # No biometric template. The audio file is the sample they provided.

VoiceProfile
  id                 string
  consent_id         string
  status             "pending" | "ready" | "refused"
  engine             "none" | "local_later" | "operator_configured"
```

## Rules

```text
function can_synthesize(profile, line_text) -> boolean:
  consent = load(profile.consent_id)
  if consent is null or not consent.accepted:
    return false
  if profile.status != "ready":
    return false
  return true

function offer_fix(composition, word_span) -> Choice:
  # Always offer punch-in first.
  return Choice(primary="record_voiceover", secondary="synthesize_if_consented")
```

Refuse, and do not call a network model, when:

- The audio was not recorded in this consent flow by the claimed speaker.
- The operator cannot produce a `ConsentRecord` for that person.
- The source clip is itself synthetic and they are asking to clone it onward.
- The person is not able to record the statement. We do not accept a typed checkbox as a substitute for the recording.

A third party may upload a consent recording only if the file is that person’s own reading of `statement_text` and the operator affirms they are acting for them. The affirmation is stored next to the `ConsentRecord` as `uploaded_for_speaker: true` plus a short note. There is no way to mark a profile ready without audio.

`statement_text` is ours, shown on screen before record, and stored verbatim with the take so a later review can hear whether they read it. Minimum content of the statement: the speaker’s name, that they authorize a synthetic voice for this project, and that they can revoke it. Do not reuse another company’s script.

Revoke sets `accepted = false` and `status = refused`, and deletes generated takes that used the profile. It does not delete the punch-in voiceovers, which are ordinary recordings.

## Generate (later)

```text
function synthesize(profile, text) -> MediaAsset:
  if not can_synthesize(profile, text):
    fail "consent missing"
  if profile.engine == "none":
    fail "no engine configured"
  pcm = engine.generate(profile, text)       # implementation chooses the engine later
  return write_wav(pcm)
```

Place the wav with [editor/voiceover.md](editor/voiceover.md) `import_voiceover` or `punch_in`. Tag the clip `synthetic: true`.

There is no OpenAPI field for this (**static**). Do not send the consent recording to `POST /jobs/agent`.

Video Regenerate is a second gate. A synthetic line needs this `ConsentRecord` before the audio exists, and a separate visual confirmation before `lip_sync` variant `imputation` ([video-regenerate.md](video-regenerate.md)). A punch-in does not need the voice record. It still needs the visual confirmation if the picture will be rebuilt. Translation lip-sync (`variant: "translation"`) is not this feature.

## Build options

| Path | When |
| --- | --- |
| Punch-in microphone | Default. No clone |
| Local engine configured by the operator, after consent | Later |
| Hosted engine the operator brings a key for, after consent | Later. The key stays in the environment |
| Descript custom AI Speaker via a prompt | Unverified and easy to misuse. Out of the default build |

## Errors

| Case | Behaviour |
| --- | --- |
| Consent audio under 5 seconds | Reject the record |
| Statement not completed (operator stopped early) | Reject. Do not create a profile |
| `can_synthesize` false | The generate button stays disabled |

No 402 on the local gate.
