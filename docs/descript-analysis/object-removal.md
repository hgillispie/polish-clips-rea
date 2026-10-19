# Descript: removing an object

Public help only. No decompiled bundles. Fetched 2026-10-19.

## Product name

Help calls this **Edit with AI**, on an **image layer**. The eraser “removes the selected area and fills it using surrounding image content.” The pencil “modifies the selected area based on your prompt” (add or restyle). It is not documented as a video inpainting effect.

The page’s known limitations say, in substance: **image layers only**. Videos, GIFs, stickers, text, and other media types are not supported (**static**).

There is no help title in the public index (llms.txt, 2026-10-19) for “remove object from video” or video inpainting. Treating Descript as a video object-removal product would invent a feature. **Unknown** whether a future release adds it; it is absent from this help snapshot.

## Behaviour (static)

- Select an image layer in the scene editor, then Edit with AI.
- Draw a region. Eraser needs no prompt. Pencil needs a short prompt. Generate.
- Each iteration writes a new file under an AI Assets folder in the project.
- Uses AI credits on current plans.
- Help suggests including the shadow or reflection when erasing, and warns that hair, glass, overlaps, and repeated edits (they suggest three or fewer) hurt quality.
- The edit stays inside the existing frame.

## API

No erase, inpaint, or “edit image” schema in the staging OpenAPI 1.2 (**static**). `POST /jobs/agent` accepts a prompt and nothing else that selects a pixel mask. Whether Underlord can erase an image region is **unverified**. The documented agent examples are filler words, Studio Sound, captions, and highlight reels, not a mask.

## Polish Clips

Video object removal is a **later** local experiment, specified so we do not pretend the Descript API does it. See [../pseudocode/object-removal.md](../pseudocode/object-removal.md). Image-only erase can share that mask contract. It is not part of the polish-clip MVP.
