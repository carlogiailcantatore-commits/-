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
ABBR = re.compile(r'(?:\b(?:P|S|S\.t|N|n|nn|pag|pagg|p|pp|sec|secc|segg|cfr|ecc|etc|Id|ibid|op|cit|ed|ediz|vol|voll|cap|capp|fig|tav|art|artt|num|sig|sigg|prof|dott|mons)\.)$')
# 版式弱信号：编号型章节标题（原文没加粗/没放大时补一个结构提示）
HEAD_HINT = re.compile(r'^(?:第[一二三四五六七八九十百]+[章节部分篇]|Parte\s+[IVXLC\d]+|Capitolo\s+\d+|'
                       r'Chapter\s+\d+|Prefazione\s+\d+|序[一二三四五六七八九十]?[、.．]?\s*)', re.I)

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

# 引号/括号配对：未闭合时不切句（避免「阿们！阿们！」被切开）
QUOTE_OPEN = {'「': '」', '『': '』', '“': '”', '«': '»', '〈': '〉', '《': '》',
              '【': '】', '（': '）', '(': ')', '[': ']', '{': '}'}
CLOSE_CHARS = '”’」』）】》>)'
LEAD_PUNCT = '，、；：,;:'

def _scan_sentences(text, classical=False):
    """按标点切句，返回 [(句子, reason)]。

    reason: punct / eol / merge（并回前句）
    规则：
      1. 引号/括号未闭合时不切（QUOTE_OPEN 配对栈）；
      2. 切点后若余下以逗号类标点开头，并回前句；
      3. 拉丁句点仍走缩写/数字/大写判定（ABBR）；
      4. classical=True 时中文逗号/分号/冒号也作为切点。
    """
    out, buf, stack, i, n = [], [], [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch in QUOTE_OPEN:
            buf.append(ch); stack.append(QUOTE_OPEN[ch]); i += 1; continue
        if stack and ch == stack[-1]:
            buf.append(ch); stack.pop(); i += 1; continue
        buf.append(ch)

        is_cjk_stop = ch in '。！？'
        is_latin_stop = ch in '.?!'
        is_classical_stop = classical and ch in '，；：'
        if not (is_cjk_stop or is_latin_stop or is_classical_stop):
            i += 1; continue

        # 计算切点位置：吸掉紧跟的闭引号/闭括号
        j = i + 1
        while j < n and text[j] in CLOSE_CHARS:
            j += 1
        rest = text[j:]
        if not rest.strip():
            i = j
            continue

        # 引号内不切
        if stack:
            i += 1
            continue

        if is_latin_stop:
            m = re.match(r'\s+', rest)
            if not m:
                i += 1
                continue
            nxt = rest[m.end():]
            before = ''.join(buf)
            is_abbr = bool(ABBR.search(before)) or bool(re.search(r'(?:^|[\s(])[A-Z]\.$', before))
            is_num = bool(nxt) and nxt[0].isdigit()
            starts_upper = bool(nxt) and (nxt[0].isupper() or nxt[0].isdigit() or nxt[0] in '«"“‘⟦(')
            if is_abbr or is_num or not starts_upper:
                i += 1
                continue

        out.append([''.join(buf).strip(), 'punct'])
        buf = []
        i = j
        while i < n and text[i] in ' \t\r\n':
            i += 1

    tail = ''.join(buf).strip()
    if tail:
        out.append([tail, 'eol'])

    # 切点后以逗号类标点开头 → 并回前句；前句以冒号结尾 → 与后句合并（冒号后是列举/引语）
    merged = []
    for sent, reason in out:
        if merged and sent and sent[:1] in tuple(LEAD_PUNCT):
            merged[-1][0] += sent
            merged[-1][1] = 'merge'
        elif merged and merged[-1][0].endswith(('：', ':')):
            merged[-1][0] += sent
            merged[-1][1] = 'merge'
        else:
            merged.append([sent, reason])
    return [(s, r) for s, r in merged]

def split_sentences_ex(text, classical=False):
    """返回 [(句子, reason)]，供需要可解释切分依据的调用方使用。"""
    return _scan_sentences(text, classical)

def split_sentences(text, classical=False):
    """兼容旧接口：只返回句子文本。"""
    return [s for s, _ in _scan_sentences(text, classical)]

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
        elif HEAD_HINT.match(t) and len(t) <= 48 and not re.search(r'[。！？.!?]$', t) \
                and not t.startswith(BULLETS):
            kind = 'L1' if re.match(r'^(?:第[一二三四五六七八九十百]+[部分篇]|Parte|Prefazione|序)', t, re.I) else 'L2'
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
            row['sents'] = [{'sid': 'p%d_0' % idx, 'text': t, 'reason': 'heading'}]
        else:
            pairs = split_sentences_ex(t, classical)
            # 保真检查：切分后拼接必须和原文一致（忽略空白）；不一致则整段不切
            a = re.sub(r'\s+', '', t)
            b = re.sub(r'\s+', '', ''.join(p[0] for p in pairs))
            if a != b:
                print('WARN_SPLIT_MISMATCH p%d' % idx)
                pairs = [(t, 'fallback_whole')]
            row['sents'] = [{'sid': 'p%d_%d' % (idx, k), 'text': s, 'reason': r}
                            for k, (s, r) in enumerate(pairs)]
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
