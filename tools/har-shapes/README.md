# har-shapes

`har_shapes.py OUT_DIR *.har` turns HAR captures into type skeletons: REST routes,
Firestore listen targets, documents and writes, and Next.js page props. It produced the
`observed-network` evidence in `docs/arcade-analysis/observed-network.md`.

Never commit HARs or OUT_DIR. HARs contain auth tokens, cookies and account PII.
