#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build a translation worklist from split_units.py output.

Usage: python worklist.py <units.json> <work.json> [--structure structure.json]
No paragraph numbers are hardcoded. Gate-1 structure confirmation can override kinds:
  {"kinds": {"0":"L0","72":"L1","148":"L3"}, "synth":[{"after":0,"kind":"L1","it":"Parte I: ..."}]}
or simply {"0":"L0","72":"L1"}.
"""
import sys, os, json, re, argparse

LEVELS = ('L0', 'L1', 'L2', 'L3', 'L4')
BULLETS = ('⚫', '·', '➡', '-', '–', '•')

def load_structure(path):
    kinds, synth = {}, []
    if not path or not os.path.exists(path):
        return kinds, synth
    obj = json.load(open(path, encoding='utf-8'))
    if 'kinds' in obj or 'synth' in obj:
        k = obj.get('kinds') or {}
        kinds = {str(a): str(b) for a, b in k.items()}
        synth = obj.get('synth') or []
    else:
        kinds = {str(a): str(b) for a, b in obj.items()}
    return kinds, synth

def tokens_for(text, row):
    out = []
    for m in re.finditer(r'⟦L(\d+)⟧', text):
        lid = int(m.group(1))
        link = next((l for l in (row.get('links') or []) if int(l.get('lid', 0)) == lid), None)
        out.append({'type': 'link', 'token': m.group(0), 'url': (link or {}).get('url'), 'anchor': (link or {}).get('anchor')})
    for m in re.finditer(r'⟦F(\d+)⟧', text):
        out.append({'type': 'fn', 'token': m.group(0), 'id': int(m.group(1))})
    for m in re.finditer(r'⟦IMG(\d+)⟧', text):
        idx = int(m.group(1)) - 1
        imgs = row.get('images') or []
        out.append({'type': 'img', 'token': m.group(0), 'name': imgs[idx] if 0 <= idx < len(imgs) else None})
    return out

def data_like(text):
    t = text.strip()
    if not t or len(t) > 120:
        return False
    if re.search(r'[.!?]', t):
        return False
    if re.match(r'^(Ut|Re|Mi|Fa|Sol|La|Do|ut|re|mi|fa|sol|la|do)[\s\u2013\u2014-]', t):
        return True
    if ('|' in t or '\u2013' in t or '\u2014' in t) and len(t.split()) <= 14:
        return True
    return False

def infer_kind(row, current_heading_kind):
    k = row.get('kind')
    if k in LEVELS or k in ('image', 'list'):
        return k
    text = (row.get('text') or '').strip()
    if not text:
        return 'image' if row.get('images') else 'empty'
    if text.startswith('http') or text.startswith('<http'):
        return 'linkline'
    if current_heading_kind == 'L4' and row.get('bold') and len(text) <= 80 and not re.search(r'[.!?]$', text):
        return 'label'
    if data_like(text):
        return 'data'
    return 'body'

def build(units_path, out_path, structure_path=None):
    data = json.load(open(units_path, encoding='utf-8'))
    rows = data.get('paragraphs', [])
    override, synth = load_structure(structure_path)
    synth_by_after = {}
    for s in synth:
        synth_by_after.setdefault(str(s.get('after')), []).append(s)
    items = []
    current_heading_kind = None
    for row in rows:
        pid = str(row.get('idx'))
        kind = override.get(pid) or infer_kind(row, current_heading_kind)
        if kind in LEVELS:
            current_heading_kind = kind
        text = row.get('text') or ''
        sents = row.get('sents') or []
        if kind == 'empty':
            continue
        item = {
            'pid': row.get('idx'),
            'kind': kind,
            'it': text,
            'zh': None,
            'size': row.get('size'),
            'bold': row.get('bold', False),
            'sents': [],
            'links': row.get('links') or [],
            'fns': row.get('fns') or [],
            'images': row.get('images') or [],
        }
        if kind in ('image', 'empty'):
            item['sents'] = []
        else:
            for s in sents:
                stext = s.get('text', '')
                item['sents'].append({
                    'sid': s.get('sid'),
                    'text': stext,
                    'zh': None,
                    'tokens': tokens_for(stext, row),
                })
        items.append(item)
        if pid in synth_by_after:
            for s in synth_by_after.pop(pid):
                syn = {
                    'pid': 'synth-%s-%s' % (s.get('after'), s.get('kind')),
                    'kind': s.get('kind', 'L1'),
                    'it': s.get('it', ''),
                    'zh': s.get('zh'),
                    'synth': True,
                    'sents': [{'sid': 'synth-%s-0' % s.get('after'), 'text': s.get('it', ''), 'zh': s.get('zh'), 'tokens': []}],
                    'links': [], 'fns': [], 'images': [],
                }
                items.append(syn)
    for after, lst in synth_by_after.items():
        for s in lst:
            item = {
                'pid': 'synth-%s-%s' % (after, s.get('kind')),
                'kind': s.get('kind', 'L1'), 'it': s.get('it', ''), 'zh': s.get('zh'), 'synth': True,
                'sents': [{'sid': 'synth-%s-0' % after, 'text': s.get('it', ''), 'zh': s.get('zh'), 'tokens': []}],
                'links': [], 'fns': [], 'images': [],
            }
            try:
                neg = int(after) < 0
            except (TypeError, ValueError):
                neg = False
            if neg:
                items.insert(0, item)
            else:
                items.append(item)
    out = {
        'source': data.get('source'),
        'body_size': data.get('body_size'),
        'items': items,
        'links': data.get('links', []),
        'notes': data.get('notes', []),
    }
    json.dump(out, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    from collections import Counter
    c = Counter(it['kind'] for it in items)
    nsent = sum(len(it['sents']) for it in items)
    print('OK ' + out_path)
    print('items=%d sentences=%d' % (len(items), nsent))
    print('kinds:', dict(c))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('units')
    ap.add_argument('out')
    ap.add_argument('--structure')
    args = ap.parse_args()
    return build(args.units, args.out, args.structure)
if __name__ == '__main__':
    sys.exit(main())
