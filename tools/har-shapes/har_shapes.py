#!/usr/bin/env python3
"""Derive request/response *shapes* (field -> type) from HAR files.

Usage: har_shapes.py OUT_DIR file1.har [file2.har ...]

Writes OUT_DIR/routes.json, firestore.json and nextdata.json. Only the types are
written, never values. Ids in paths are templated as {id}. Keep the HARs and OUT_DIR
outside the repo: the HARs hold tokens, cookies and PII. The outputs can still hold
map keys that are ids, so review them before you copy anything into docs.
"""
import base64, collections, json, os, re, sys, urllib.parse

KEEP = re.compile(r'(^|\.)arcade\.(software|show)$|firestore\.googleapis\.com|'
                  r'firebasestorage\.googleapis\.com|identitytoolkit|securetoken')
STATIC = re.compile(r'\.(js|css|png|jpe?g|gif|svg|woff2?|ttf|ico|webp|mp4|m3u8|ts|map|avif|mp3)(\?|$)'
                    r'|/_next/static/|/_next/image|/ingest/static/')
IDSEG = re.compile(r'[A-Za-z0-9]{20}|[0-9a-f-]{36}|\d+|(workspace|team|user)-[a-z0-9]+|[A-Za-z0-9_\-]{24,}')
IDKEY = re.compile(r'[A-Za-z0-9_\-]{8,}')

def tmpl(path):
    return '/'.join('{id}' if IDSEG.fullmatch(s) else s for s in path.split('/'))

def is_id_map(keys):
    return len(keys) > 3 and all(IDKEY.fullmatch(k) and not re.fullmatch(r'[a-z][a-zA-Z]+', k) for k in keys)

def shape(v, d=0):
    if d > 14: return '...'
    if v is None: return 'null'
    if isinstance(v, bool): return 'bool'
    if isinstance(v, (int, float)): return 'num'
    if isinstance(v, str):
        if re.fullmatch(r'\d{4}-\d\d-\d\dT[\d:.]+Z?', v): return 'iso'
        return 'url' if v.startswith('http') else 'str'
    if isinstance(v, list):
        m = None
        for x in v[:50]: m = merge(m, shape(x, d + 1))
        return [m] if m is not None else []
    if isinstance(v, dict):
        if is_id_map(list(v)):
            m = None
            for k in list(v)[:50]: m = merge(m, shape(v[k], d + 1))
            return {'{key}': m}
        return {k: shape(x, d + 1) for k, x in v.items()}
    return type(v).__name__

def merge(a, b):
    if a is None: return b
    if b is None: return a
    if isinstance(a, dict) and isinstance(b, dict):
        out = {}
        for k in set(a) | set(b):
            v = merge(a.get(k), b.get(k))
            if (k not in a or k not in b) and isinstance(v, str) and not v.endswith('?'): v += '?'
            out[k] = v
        return out
    if isinstance(a, list) and isinstance(b, list):
        return [merge(a[0] if a else None, b[0] if b else None)] if (a or b) else []
    if a == b: return a
    ta = a if isinstance(a, str) else ('object' if isinstance(a, dict) else 'array')
    tb = b if isinstance(b, str) else ('object' if isinstance(b, dict) else 'array')
    return '|'.join(sorted(set(ta.split('|')) | set(tb.split('|'))))

FS_SCALAR = {'stringValue': 'str', 'integerValue': 'int', 'doubleValue': 'num', 'booleanValue': 'bool',
             'nullValue': 'null', 'timestampValue': 'ts', 'referenceValue': 'ref', 'geoPointValue': 'geo',
             'bytesValue': 'bytes'}

def fs_shape(v, d=0):
    (t, x), = v.items()
    if t == 'mapValue':
        f = x.get('fields', {})
        if is_id_map(list(f)):
            m = None
            for k in list(f)[:60]: m = merge(m, fs_shape(f[k], d + 1))
            return {'{key}': m}
        return {k: fs_shape(y, d + 1) for k, y in f.items()}
    if t == 'arrayValue':
        m = None
        for y in x.get('values', [])[:80]: m = merge(m, fs_shape(y, d + 1))
        return [m] if m is not None else []
    return FS_SCALAR.get(t, t)

def fs_coll(name):
    p = name.split('/documents/', 1)[-1].split('/')
    return '/'.join(s if i % 2 == 0 else '{id}' for i, s in enumerate(p))

def webchannel_chunks(text):
    i = 0
    while i < len(text):
        m = re.match(r'(\d+)\n', text[i:])
        if not m: return
        n = int(m.group(1)); i += m.end(); yield text[i:i + n]; i += n

def jbody(text, enc=None):
    if not text: return None
    if enc == 'base64':
        try: text = base64.b64decode(text).decode('utf8', 'replace')
        except Exception: return None
    try: return json.loads(text)
    except Exception: return None

def channel_payloads(entry):
    for k, v in urllib.parse.parse_qsl((entry['request'].get('postData') or {}).get('text') or ''):
        if k.endswith('__data__'):
            j = jbody(v)
            if j is not None: yield j

def main(out, files):
    routes = collections.OrderedDict()
    docs, writes, targets = {}, {}, collections.Counter()
    pages = {}
    for f in files:
        for e in json.load(open(f))['log']['entries']:
            r = e['request']; u = urllib.parse.urlparse(r['url'])
            c = e['response'].get('content', {})
            if u.netloc == 'app.arcade.software' and (c.get('mimeType') or '').startswith('text/html'):
                nd = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', c.get('text') or '', re.S)
                if nd:
                    j = json.loads(nd.group(1))
                    pages[j['page']] = merge(pages.get(j['page']), shape(j['props'].get('pageProps', {})))
            if not KEEP.search(u.netloc) or STATIC.search(u.path): continue
            if 'firestore.googleapis.com' in u.netloc:
                for j in channel_payloads(e):
                    t = j.get('addTarget') or {}
                    if 'query' in t:
                        sq = t['query']['structuredQuery']
                        fields = sorted(set(re.findall(r'"fieldPath": "([^"]+)"', json.dumps(sq.get('where', {})))))
                        targets[json.dumps(['query', '/'.join(x['collectionId'] for x in sq['from']), fields,
                                            [o['field']['fieldPath'] for o in sq.get('orderBy', [])], sq.get('limit')])] += 1
                    for dn in t.get('documents', {}).get('documents', []):
                        targets[json.dumps(['doc', fs_coll(dn)])] += 1
                    for w in j.get('writes', []):
                        if 'update' in w:
                            k = fs_coll(w['update']['name']); W = writes.setdefault(k, {'shape': None, 'mask': set()})
                            W['shape'] = merge(W['shape'], fs_shape({'mapValue': {'fields': w['update'].get('fields', {})}}))
                            W['mask'].update(w.get('updateMask', {}).get('fieldPaths', []))
                            W['mask'].update('transform:' + x.get('fieldPath', '') for x in w.get('updateTransforms', []))
                for ch in webchannel_chunks(c.get('text') or ''):
                    arr = jbody(ch) or []
                    for item in arr:
                        if isinstance(item, list) and len(item) > 1 and isinstance(item[1], list):
                            for m in item[1]:
                                if isinstance(m, dict) and 'documentChange' in m:
                                    d = m['documentChange']['document']; k = fs_coll(d['name'])
                                    docs[k] = merge(docs.get(k), fs_shape({'mapValue': {'fields': d.get('fields', {})}}))
                continue
            if u.netloc == 'app.arcade.software' and not (u.path.startswith('/api/') or u.path.startswith('/_next/data')):
                continue
            key = f"{r['method']} {u.netloc}{tmpl(u.path)}"
            R = routes.setdefault(key, {'count': 0, 'status': set(), 'query': set(), 'headers': set(), 'req': None, 'res': None})
            R['count'] += 1; R['status'].add(e['response']['status'])
            R['query'].update(k for k, _ in urllib.parse.parse_qsl(u.query, keep_blank_values=True))
            R['headers'].update(h['name'].lower() for h in r['headers'] if h['name'].lower().startswith('x-arcade'))
            rq = jbody((r.get('postData') or {}).get('text'))
            if rq is not None: R['req'] = merge(R['req'], shape(rq))
            rs = jbody(c.get('text'), c.get('encoding'))
            if rs is not None: R['res'] = merge(R['res'], shape(rs))
    os.makedirs(out, exist_ok=True)
    ser = lambda o: sorted(o) if isinstance(o, set) else o
    json.dump({k: {kk: ser(vv) for kk, vv in v.items()} for k, v in routes.items()}, open(f'{out}/routes.json', 'w'), indent=1)
    json.dump({'targets': [json.loads(k) + [n] for k, n in targets.items()], 'documents': docs,
               'writes': {k: {'shape': v['shape'], 'mask': sorted(v['mask'])} for k, v in writes.items()}},
              open(f'{out}/firestore.json', 'w'), indent=1)
    json.dump(pages, open(f'{out}/nextdata.json', 'w'), indent=1)
    for k, v in routes.items(): print(k, v['count'], sorted(v['status']))

if __name__ == '__main__':
    if len(sys.argv) < 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
