# Custom variables, translations, synthetic voice, captions

Evidence: **decompiled** (variable helpers, translation hooks, flows SDK, synthetic-voice SDK),
**observed** (translation doc shape, step `syntheticVoice` keys).

## Custom variables (personalization)

- Syntax in any text (hotspot label, overlay title/subtitle, button text): `{{ name }}`;
  name matches `[a-z_\-0-9]+`, spaces allowed inside the braces.
- Definition: `flow.customVariables = { name: { fallback, createdAt } }`.
- Values come from the share/embed URL: `?variable.<name>=<value>` (the embed-code
  builder fills `INSERT_VALUE_HERE` placeholders). Missing → fallback.
- `variablesUsedInFlow(flow)` scans all text to list used names; `withCustomVariables(text, values, defs)` substitutes.
- Plan feature "Custom Variables".

## Translations

Stored per language, separate from the flow (`translations` collection; public payload
`_serializableTranslations[lang]`):

```
Translation {
  createdAt, updatedAt
  generationStatus? { status: queued|generating|…, … }
  strings: {
    name, description,
    steps: { [stepId]: {
       hotspots?: { [hotspotId]: string },
       description?, 
       chapter?: { title, subtitle, buttonTexts: { [pathId]: string } },
       syntheticVoice?: { script, url }        # per-language voiceover audio
    } }
  }
}
```
API: `POST /api/flows/{id}/translations/generate {language, mode:"missing"}` → `{started}` (async AI),
`PUT /api/flows/{id}/translations {language, translations}`, `DELETE …/translations?language=`,
`POST /api/flows/{id}/translate-strings {destinationLanguage, sourceStrings}` (ad-hoc strings).
Viewer: language picker when `showTranslation`; default from browser language;
`flow.originalLanguage` (default "en"). Two language lists exist (37 for UI, 80 for AI).
Plan: Growth+ "AI Translations" (static-help); plan-limit key `translations`.

## Synthetic voice (AI voiceover)

```
step.syntheticVoice {
  enabled, script, url (audio), playbackRate,
  timepoints: [{ markName, timeSeconds }]          # word/sentence marks for caption sync
  voice: { key, languageCode, provider: "elevenlabs"|"google", model: "eleven_v3"|…, variant }
}
```
- `POST /api/synthetic-voice` body built from `{voice, script, language, model}` → `{url, timepoints, duration}`.
  `GET /api/synthetic-voice?…` lists voices. Pronunciation dictionary per brand kit:
  `GET|PUT /api/synthetic-voice/pronunciation` (header `x-arcade-brand-kit-id`), `POST …/pronunciation/preview` → audio blob.
- "Apply voice to all" regenerates every step whose voice key/model differs or whose script changed.
- Hotspot `syncTextToVoiceover` shows the label as a caption timed by `timepoints`.
- Text-only steps: default read time = `1000 × max(DEFAULT_WAIT × chars × 0.03, DEFAULT_WAIT)` ms (autoplay pacing).
- Tones for AI script: Professional, Educational, Friendly, Minimalist, Inspirational.
- `flow.backgroundMusicUrl/Volume` mixes under voice; `keepSoundOffUntilEnabled` / "Start Muted".
- Plan: AI Voiceover is on Free (static-help); voice model selection is flagged.

## Captions

`showCaptions` (button visible) + `captionsVisible` (default on). Captions show the
voiceover script (or hotspot text synced to it). Viewer toggle reports `Caption Toggled`.
