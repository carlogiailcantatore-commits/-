#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""Build sentence units + structure hints from extract.py output.

Usage: python split_units.py <source.json> <units.json> [--body-size N]
Hints only: L0/L1/L2/L3/L4/body/list/image/empty; the agent still confirms structure.
"""
import sys, os, json, re
from collections import Counter

BULLETS = ('⚫', '·', '➡', '-', '–', '•')
LINK_TOKEN = '⟦L%d⟧'
FN_TOKEN = '⟦F%d⟧'
IMG_TOKEN = '⟦IMG%d⟧'
ABBR = re.compile(r'(?:\b(?:P|S|S\.t|N|n|nn|pag|pagg|sec|secc|cfr|ecc|etc|Id|cfr)\.)$')

def get_paragraphs(data):
    if 'paragraphs' in data:
        return data['paragraphs'], 'paragraph'
    out = []
    for i, b in enumerate(data.get('blocks', [])):
        out.append({'index': i, 'text': b.get('text', ''), 'sizes': [b.get('size')] if b.get('size') else [],
                    'bold': b.get('bold', False), 'spans': b.get('spans') or [{'t': 'text', 's': b.get('text', '')}],
                    'images': [], 'links': [], 'fnrefs': []})
    return out, 'block'

def build_unit(p):
    out, links, fns, imgs = [], [], [], []
    spans = p.get('spans') or []
    if not spans:
        return p.get('text', '').replace('\xa0', ' '), links, fns, imgs
    for sp in spans:
        t = sp.get('t')
        if t == 'text':
            out.append(sp.get('s', ''))
        elif t == 'link':
            lid = len(links) + 1
            links.append({'lid': lid, 'url': sp.get('url'), 'anchor': sp.get('s', '')})
            out.append(LINK_TOKEN % lid)
        elif t == 'fn':
            fns.append({'id': sp.get('id')})
            out.append(FN_TOKEN % sp.get('id'))
        elif t == 'img':
            imgs.append(sp.get('name'))
            out.append(IMG_TOKEN % len(imgs))
    txt = ''.join(out).replace('\xa0', ' ')
    txt = re.sub(r'[ \t]+', ' ', txt)
    return txt.strip(), links, fns, imgs

def split_sentences(text, classical=False):
    out, buf, i, n = [], [], 0, len(text)
    while i < n:
        ch = text[i]
        buf.append(ch)
        if classical and ch in '，；：':
            j = i + 1
            while j < n and text[j] in '”’」』）】》':
                buf.append(text[j]); j += 1
            out.append(''.join(buf).strip())
            buf = []
            while j < n and text[j] in ' \t\r\n':
                j += 1
            i = j
            continue
        if ch in '。！？':
            j = i + 1
            while j < n and text[j] in '”’」』）】》':
                buf.append(text[j]); j += 1
            out.append(''.join(buf).strip())
            buf = []
            while j < n and text[j] in ' \t\r\n':
                j += 1
            i = j
            continue
        if ch in '.?!':
            m = re.match(r'\s+', text[i + 1:])
            if m:
                nxt = text[i + 1 + m.end():]
                before = ''.join(buf)
                is_abbr = bool(ABBR.search(before)) or bool(re.search(r'(?:^|[\s(])[A-Z]\.$', before))
                is_num = i + 1 < n and text[i + 1].isdigit()
                starts_upper = bool(nxt) and (nxt[0].isupper() or nxt[0].isdigit() or nxt[0] in '«"“‘⟦(')
                if (not is_abbr) and (not is_num) and starts_upper:
                    out.append(''.join(buf).rstrip())
                    buf = []
                    j = i + 1
                    while j < n and text[j] in ' \t':
                        j += 1
                    i = j
                    continue
        i += 1
    tail = ''.join(buf).strip()
    if tail:
        out.append(tail)
    return out

def body_size_of(paras):
    cnt = Counter()
    for p in paras:
        t = p.get('text', '')
        for s in p.get('sizes') or []:
            cnt[s] += max(1, len(t))
    return cnt.most_common(1)[0][0] if cnt else 0

def main_size_of(p):
    """Dominant size by text length (ignore stray superscript/footnote sizes)."""
    spans = p.get('spans') or []
    cnt = Counter()
    for sp in spans:
        if sp.get('t') in ('text', 'link'):
            s = sp.get('size')
            if s:
                cnt[s] += max(1, len(sp.get('s') or ''))
    if cnt:
        return cnt.most_common(1)[0][0]
    sizes = p.get('sizes') or []
    return max(sizes) if sizes else 0

def main():
    if len(sys.argv) < 3:
        print('usage: split_units.py <source.json> <units.json> [--body-size N]')
        return 2
    src, out = sys.argv[1], sys.argv[2]
    data = json.load(open(src, encoding='utf-8'))
    paras, mode = get_paragraphs(data)
    classical = '--classical' in sys.argv or '--cjk-clause' in sys.argv
    body_size = None
    if '--body-size' in sys.argv:
        body_size = int(sys.argv[sys.argv.index('--body-size') + 1])
    if body_size is None:
        body_size = data.get('body_size') or body_size_of(paras)
    # title: first non-empty paragraph (a title can share size with section headings)
    nonempty = [p for p in paras if p.get('text', '').strip() or p.get('images')]
    title_idx = nonempty[0].get('index') if nonempty else None
    # heading sizes (bold, larger than body, not title, short text)
    hsizes = set()
    for p in paras:
        if p.get('index') == title_idx:
            continue
        t = p.get('text', '').strip()
        mx = main_size_of(p)
        if p.get('bold') and mx > body_size and 0 < len(t) <= 220 and not t.startswith(BULLETS) and not t.startswith('Esempio'):
            hsizes.add(mx)
    hsorted = sorted(hsizes, reverse=True)
    hmap = {}
    for k, sz in enumerate(hsorted[:3]):
        hmap[sz] = 'L%d' % (k + 1)
    rows, links_all = [], []
    for p in paras:
        text, links, fns, imgs = build_unit(p)
        idx = p.get('index')
        mx = main_size_of(p)
        t = text.strip()
        if not t and imgs:
            kind = 'image'
        elif not t:
            kind = 'empty'
        elif idx == title_idx:
            kind = 'L0'
        elif re.match(r'^Esempio\s*\d', t):
            kind = 'L4'
        elif p.get('bold') and mx <= body_size and len(t) <= 120 and not re.search(r'[.!]$', t):
            kind = 'L3'
        elif mx in hmap:
            kind = hmap[mx]
        elif t.startswith(BULLETS) or p.get('numbered') or re.match(r'^\d+[\).]\s', t) or t.startswith('- '):
            kind = 'list'
        else:
            kind = 'body'
        for l in links:
            l['pidx'] = idx
            links_all.append(l)
        row = {'idx': idx, 'kind': kind, 'size': mx, 'bold': p.get('bold', False), 'text': t,
               'links': links, 'fns': fns, 'images': imgs}
        if kind in ('L0', 'L1', 'L2', 'L3', 'L4', 'image', 'empty'):
            row['sents'] = [{'sid': 'p%d_0' % idx, 'text': t}]
        else:
            sents = split_sentences(t, classical)
            # 保真检查：切分后拼接必须和原文一致（忽略空白）
            a = re.sub(r'\s+', '', t); b = re.sub(r'\s+', '', ''.join(sents))
            if a != b:
                print('WARN_SPLIT_MISMATCH p%d' % idx)
            row['sents'] = [{'sid': 'p%d_%d' % (idx, k), 'text': s} for k, s in enumerate(sents)]
        rows.append(row)
    notes = [{'nid': n['id'], 'text': n['text']} for n in data.get('footnotes', [])]
    json.dump({'source': data.get('file'), 'mode': mode, 'body_size': body_size,
               'heading_sizes': hsorted, 'paragraphs': rows, 'links': links_all, 'notes': notes},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    c = Counter(r['kind'] for r in rows)
    print('OK ' + out)
    print('kinds:', dict(c))
    print('sentences:', sum(len(r.get('sents', [])) for r in rows))
    print('links:', len(links_all), 'notes:', len(notes))
    return 0
if __name__ == '__main__':
    sys.exit(main())
