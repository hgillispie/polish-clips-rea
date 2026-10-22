# HTML capture (cleaned DOM snapshot)

Evidence: **decompiled** (recording-manager `getCleanHTML`, background scrape call).
Plan gate: Enterprise "HTML capture" (static-help). Setting `captureHTML`.

Purpose: an HTML step can be re-rendered, text-edited, translated and made
responsive, unlike a screenshot. The step keeps the screenshot as `url` and sets
`hasHTML: true`; the HTML lives in storage keyed by step id.

```
getCleanHTML(doc, clickId, pageId):
  clone = doc.documentElement.cloneNode(deep)
  for each scrolled element in the live doc: clone el gets data-<ns>-scroll="x,y"
  for each input/textarea/select: copy live value / checked / selected into attributes
  remove: <script>, <noscript>, <link> except rel=stylesheet, <picture><source>,
          <meta http-equiv=Content-Security-Policy>
  <video>: absolutize src + poster
  <img>: src = currentSrc (resolved responsive choice); drop srcset
  <a href>: "#"  (links must not navigate inside the player)
  constructed / CSSOM-only stylesheets (adoptedStyleSheets, insertRule'd): serialize rules into <style>
  <canvas>: replace with <img src=canvas.toDataURL("image/png")>
  insert <base href=location.href> so relative URLs resolve
  for each <iframe>: assign id; replace src with "<id>.html";
       ask that frame (postMessage RequestHtmlFromIframe) for its own getCleanHTML, 1 s timeout
  return { pageContext, content: serialize(clone), devicePixelRatio, websiteUrl,
           iframesIds, isIframe, clickId, pageId }
```

Upload: each HTML document goes through `POST /api/extension/upload-url {type:"html"}`
then PUT. Afterwards the extension calls
`POST /api/extension/scrape { sessionId: flowId, pages: [{ websiteUrl, imageId, htmlUrl }] }`
so the server can fetch/inline remote assets (fonts, images) for offline-safe rendering
(inferred purpose).

In the final `demo-end` payload `capturedHTML` is sent as `{}` (stripped) because
the HTML has already been uploaded separately.

Our build: render HTML steps inside a sandboxed iframe (`sandbox="allow-same-origin"`,
no scripts), scale with CSS transform to the stage, restore `data-*-scroll` on load.
