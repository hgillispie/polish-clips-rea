# Descript: skin smoothing (appearance touch-up)

Public help only. No decompiled bundles. Fetched 2026-10-19 from the Descript help center.

## What the product is called

The help page is titled **“Touch up your appearance with skin smoothing.”** The effect name in the UI steps is **Skin smoothing**. There is no separate help article whose title is “AI touch-up.”

Skin smoothing is one item among several “look good” tools. It is not the same feature as:

| Help name | What the page says it does | Tag |
| --- | --- | --- |
| Skin smoothing | Finds a face and softens targeted areas, with a strength slider and region controls | static |
| Eye Contact | Redirects gaze toward the lens. Single clear face. Needs a network connection and AI credits | static |
| Center Active Speaker (beta) | Reframes toward whoever is talking. Needs video and audio on the same track | static |
| Green Screen | Removes the background without a physical screen. Chroma Key is the separate effect when a real screen is present | static |

Polish Clips still treats **Eye Contact** as a research note, not a pipeline stage. This page does not change that. Skin smoothing is the appearance touch-up.

## Behaviour (static, help text)

- Select the video layer, Effects, Skin smoothing.
- Strength runs from low to high. A Regions control targets areas.
- Also available from the Properties panel.
- Help states it detects general facial location (forehead, eyes, jawline) so the blur lands in the right place, and that it does not use or store a faceprint.
- Weaker on small faces, three or more people, hats, glasses, hands, coverings, turned heads, low light, and non-faces (illustrations, statues, pets).

Help does not publish the model, the resolution, or whether frames leave the machine. Those details are **unknown**.

## API

The staging OpenAPI 1.2 (2026-10-19) has no skin-smoothing, eye-contact, or framing operation and no example prompt for them (**static**). Agent edits are a free-text `prompt` on `POST /jobs/agent`. Help for the API says Underlord can do “anything else Underlord can do,” which does not name skin smoothing (**static** wording, **inferred** that a prompt might be tried and might no-op).

AI credits are mentioned for Look Good tools as a group. A live probe would be required to see whether a skin-smoothing prompt spends credits or changes the project. Until then the API path is **unverified**.

## What we will not copy

No effect implementation, no UI screenshot assets, no model weights. The local spec is [../pseudocode/skin-smoothing.md](../pseudocode/skin-smoothing.md).
