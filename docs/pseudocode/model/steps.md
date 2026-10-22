# Steps

Evidence: **decompiled** (step migration `oldStepToStep`, type guards, step builder),
**observed** (public flow step keys).

```
StepType = Image 1 | Video 2 | Overlay 3 | Empty 4

BaseStep { id, name?, hiddenFromNavigation?, skipped? }

MediaStepCommon (Image | Video) {
  url                         # image URL or video source (HLS .m3u8 after processing)
  size {width, height}
  assetId?                    # media-library asset
  clickContext?, pageContext? # from capture, feeds AI
  panAndZoom?                 # pan-zoom-and-image-edits.md
  coverAndFit {}
  syntheticVoice?             # variables-translations-voice.md
  cameraRecording?            # face bubble: {url, enabled, placement:"bottom-right"|…, size:"medium"|…,
                              #   shape:"circle"|…, audioOnly, startTimeFrac, endTimeFrac, playbackRate,
                              #   offsetStartTimeFrac, processing}
  cta?                        # step-level CTA button
  mobileButton? {color, targetId}   # tap target on mobile layout
  description?, textColor?, mobileMediaAlignment?, isMobileRecording?, flowWrapper?, flowAspectRatio?
  showLogo?, autoplay?, title?, subtitle?
}

ImageStep : MediaStepCommon {
  type: 1
  originalImageUrl            # pre-edit image (blur/crop are re-applied to this)
  blurhash
  hasHTML                     # HTML capture available
  imageEditorState? { redaction: Rect[], crop: {x,y,width,height} }
  hotspots: Hotspot[]         # usually 1; 0 for final step
  startTimeFrac?              # legacy
}

VideoStep : MediaStepCommon {
  type: 2
  duration                    # seconds of the WHOLE source video
  startTimeFrac, endTimeFrac  # trim window as fractions of duration
  clipDuration?
  playbackRate                # 1, 1.5, 2.5 …
  muted
  videoProcessing             # true until transcode done
  streamUrl?                  # HLS URL
  videoThumbnailUrl           # derived from Mux thumbnail at start time
  videoPanAndZooms[]          # timed zooms
  targetId?                   # where to go when the clip ends (branching)
  captions?, aiProcessing?
  hotspots: Hotspot[]         # observed: callouts on video steps exist in current data;
                              # the legacy migration emptied them (decompiled)
}

OverlayStep {                  # chapter / start / end card, form, embed
  type: 3
  title, subtitle             # markdown-ish rich text
  theme: "dark" | "light" | "custom"; customTheme?
  blur: "none" | "small" | "medium"     # background blur of preview image
  variant: "buttons" | "form" | "embeds"
  textAlign: "left" | …
  showPreviewImage, previewImage { type:"step", stepId }   # background = blurred other step
  showLogo, logo?
  paths: Path[]               # buttons (variant buttons) / submit button (form)
  formFields?: FormField[]    # variant form
  embedCode?                  # variant embeds (HubSpot, Calendly, Typeform, Marketo …)
  autoplay?
  # legacy single-button form: buttonText, buttonType "next_step"|"url", actionUrl,
  #   buttonColor, buttonTextColor
}

EmptyStep { type: 4 }          # placeholder; skipped by navigation
```

Helper semantics (decompiled):
- `getFirstNonEmptyStep`, next/prev non-empty step with optional wrap-around (restart).
- `hasBlur(step)` = image step with non-empty `imageEditorState.redaction`.
- `isCropped(step)` = crop rect differs from full `size`.
- Legacy docs used `imageUrl` → migrated to `url` + type Image; legacy `labelColor` on
  hotspots → `bgColor`, text colour = inverted label colour.
- Video thumbnail fallback: replace `stream`→`image` and `.m3u8`→`/thumbnail.png?time=<startFrac×duration>`.
