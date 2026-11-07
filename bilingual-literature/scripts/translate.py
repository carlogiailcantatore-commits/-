#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""Split a work.json translation worklist into chunks and merge translated chunks.

export: translate.py export work.json out_dir [--chunk-chars N]
merge : translate.py merge work.json out_dir --out translations.json [--allow-incomplete]

Chunk format:
  {"chunk": 1, "items": [{"key": "...", "kind": "...", "text": "..."}], "translations": {}}
Merge also accepts a flat JSON object mapping key -> translation.
Keys: headings are H:<pid>; sentences use their sid; optional footnotes FN:<nid>.
"""
import sys, os, json, argparse, glob

def load_work(path):
    w = json.load(open(path, encoding='utf-8'))
    items = []
    for it in w.get('items', []):
        kind = it.get('kind')
        if kind in ('L0', 'L1', 'L2', 'L3', 'L4'):
            items.append({'key': 'H:%s' % it.get('pid'), 'kind': kind, 'text': it.get('it') or ''})
            continue
        for s in it.get('sents') or []:
            items.append({'key': s.get('sid'), 'kind': kind, 'text': s.get('text') or ''})
    return w, items

def cmd_export(args):
    w, items = load_work(args.work)
    os.makedirs(args.out_dir, exist_ok=True)
    total = sum(len(i['text']) for i in items)
    chunks, cur, n = [], [], 0
    for it in items:
        if cur and n + len(it['text']) > args.chunk_chars:
            chunks.append(cur); cur = []; n = 0
        cur.append(it); n += len(it['text'])
    if cur:
        chunks.append(cur)
    # human-readable full input
    with open(os.path.join(args.out_dir, 'tr_input.txt'), 'w', encoding='utf-8') as f:
        for it in items:
            f.write('%s\t%s\t%s\n' % (it['key'], it['kind'], it['text'].replace('\n', ' ')))
    for k, chunk in enumerate(chunks, 1):
        obj = {'chunk': k, 'items': chunk, 'translations': {}}
        p = os.path.join(args.out_dir, 'tr_c%d.json' % k)
        json.dump(obj, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        # plain text view for manual/LLM translation
        with open(os.path.join(args.out_dir, 'tr_c%d.txt' % k), 'w', encoding='utf-8') as f:
            for it in chunk:
                f.write('%s\t%s\t%s\n' % (it['key'], it['kind'], it['text'].replace('\n', ' ')))
    print('OK chunks=%d items=%d chars=%d dir=%s' % (len(chunks), len(items), total, args.out_dir))
    return 0

def cmd_merge(args):
    w, items = load_work(args.work)
    expected = [i['key'] for i in items]
    exp_set = set(expected)
    tr = {}
    dup = []
    files = sorted(glob.glob(os.path.join(args.dir, 'tr_c*.json')))
    for p in files:
        try:
            obj = json.load(open(p, encoding='utf-8'))
        except Exception as e:
            print('BAD_JSON %s :: %s' % (p, e))
            continue
        m = obj.get('translations') if isinstance(obj, dict) and 'translations' in obj else obj
        if not isinstance(m, dict):
            print('SKIP_NO_TRANSLATIONS %s' % p)
            continue
        for k, v in m.items():
            if not v:
                continue
            if k in tr and tr[k] != v:
                dup.append((k, p))
            tr[k] = v
    # prefill existing work zh if no translation
    for it in w.get('items', []):
        if it.get('kind') in ('L0', 'L1', 'L2', 'L3', 'L4'):
            k = 'H:%s' % it.get('pid')
            if k not in tr and it.get('zh'):
                tr[k] = it['zh']
        else:
            for s in it.get('sents') or []:
                if s.get('sid') not in tr and s.get('zh'):
                    tr[s['sid']] = s['zh']
    miss = [k for k in expected if not tr.get(k)]
    extra = [k for k in tr if k not in exp_set and not k.startswith('FN:')]
    print('chunks=%d expected=%d translated=%d missing=%d extra=%d dup=%d' % (len(files), len(expected), len(expected) - len(miss), len(miss), len(extra), len(dup)))
    for k in miss[:20]:
        print('  MISS ' + k)
    for k in extra[:20]:
        print('  EXTRA ' + k)
    for k, p in dup[:10]:
        print('  DUP ' + k + ' :: ' + p)
    json.dump(tr, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('OK ' + args.out)
    if miss and not args.allow_incomplete:
        return 3
    return 0

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('export')
    e.add_argument('work'); e.add_argument('out_dir')
    e.add_argument('--chunk-chars', type=int, default=8000)
    m = sub.add_parser('merge')
    m.add_argument('work'); m.add_argument('dir'); m.add_argument('--out', required=True)
    m.add_argument('--allow-incomplete', action='store_true')
    args = ap.parse_args()
    if args.cmd == 'export':
        return cmd_export(args)
    return cmd_merge(args)

if __name__ == '__main__':
    sys.exit(main())
