# Descript: a voice that sounds like the speaker

Public help and one public changelog note. No decompiled bundles. Fetched 2026-10-19.

## Names

| Name | What the public page says | Tag |
| --- | --- | --- |
| Custom AI Speaker / voice clone | The speaker records a consent statement, then Descript can generate speech in that voice. Help title: “Create a custom voice clone.” | static |
| Regenerate | Smooth a section without changing the words, or replace words using an authorized custom AI speaker. English only. Video regenerate is limited (face visible; not sequences, B-roll, or multi-speaker). The first video regenerate asks for consent because it changes the visual performance | static |
| Overdub | A Descript changelog (Release 103) says the Overdub label was retired and that changing the script is now Regenerate, with the same voice-authorization step | static (changelog) |
| Stock AI voices | Built-in voices for voiceover, not the user’s voice | static |
| Convert recorded audio to AI speech | Replaces recorded script audio with a stock or custom AI speaker | static |

“Overdub” in older Polish Clips notes means this family of features. The current help name for the clone is **custom AI Speaker**. The current help name for fixing or rewriting a line is **Regenerate**.

## Consent (static, summarized)

Help requires a recording of the person whose voice will be cloned, in English, reading Descript’s consent statement, before speech generation is enabled. The statement authorizes an artificial version of that voice. The full wording is on the help page; it is not copied here.

Help says a clone may be created by the person or by someone with that person’s recorded authorization. Help says Descript will not clone a deceased person, a person who does not consent, a person who cannot record the statement, or audio that is already synthetic. Bypassing the process is described as a terms breach.

Help also says you cannot add training audio to an existing clone; a new consent recording creates a new speaker. Accent fidelity is described as uneven; help points at switching a voice-generation model in app settings and names ElevenLabs model versions as options. That is their hosted stack, not a library we vendor.

## API

Staging OpenAPI 1.2 has no speaker, consent, clone, regenerate, or TTS schema (**static**). Credits for Underlord edits are documented; help’s API overview lists captions, filler words, Studio Sound, scenes, and highlight reels, then “anything else Underlord can do.” A prompt that asks to clone a voice or regenerate a line is **unverified**. Do not send someone else’s audio to that prompt.

## Polish Clips rule

A synthetic voice that sounds like a person ships only with **that person’s** recorded consent and samples they provided. The default way to fix a line is a punch-in [voiceover](../pseudocode/editor/voiceover.md). The consent gate is [../pseudocode/voice-consent.md](../pseudocode/voice-consent.md).
