#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Render a book-style Gate-1 outline (headings + one-sentence body summaries).

Usage: python outline.py <units.json> <outline.md> [--structure structure.json]
Body text is NOT dumped; each heading that owns body gets:
  [内容概述]（待填：一句话概括本节正文）
The agent fills the summaries and Chinese titles.
--structure：若给出，用结构源里的 kinds 覆盖 units 的标题提示（含 synth 补标题）。
"""
import sys, os, json
from collections import Counter

LEVEL_ORDER = {'L0': 0, 'L1': 1, 'L2': 2, 'L3': 3, 'L4': 4}

def load_structure(path):
    if not path or not os.path.exists(path):
        return {}, []
    obj = json.load(open(path, encoding='utf-8'))
    kinds = {str(k): v for k, v in (obj.get('kinds') or {}).items()}
    return kinds, obj.get('synth') or []

def main():
    if len(sys.argv) < 3:
        print('usage: outline.py <units.json> <outline.md> [--structure structure.json]')
        return 2
    src, out = sys.argv[1], sys.argv[2]
    structure = sys.argv[sys.argv.index('--structure') + 1] if '--structure' in sys.argv else None
    data = json.load(open(src, encoding='utf-8'))
    override, synth = load_structure(structure)
    rows = data.get('paragraphs', [])
    # 把 synth 插到对应段之后
    if synth:
        by_after = {}
        for s in synth:
            by_after.setdefault(str(s.get('after')), []).append(s)
        new_rows = []
        for r in rows:
            new_rows.append(r)
            for s in by_after.pop(str(r.get('idx')), []):
                new_rows.append({'idx': 'synth-%s-%s' % (s.get('after'), s.get('kind')),
                                 'kind': s.get('kind', 'L1'),
                                 'text': s.get('it', ''), 'size': None, 'synth': True})
        rows = new_rows
    lines = ['# 书目录 + 正文一句话概述（骨架，待填）', '']
    lines.append('[前言概述]（待填：200–300 字总体概述）')
    lines.append('')
    current = None          # current heading row
    body_chars = 0
    preface_body = 0

    def flush():
        nonlocal body_chars, current
        if current is not None and body_chars > 0:
            indent = '  ' * LEVEL_ORDER[current['kind']]
            lines.append(indent + '  [内容概述]（待填：一句话概括本节正文；正文约 %d 字）' % body_chars)
            lines.append('')
        body_chars = 0

    for r in rows:
        kind = override.get(str(r.get('idx'))) or r.get('kind')
        if kind in LEVEL_ORDER:
            flush()
            current = r
            indent = '  ' * LEVEL_ORDER[kind]
            text = (r.get('text') or '').replace('\n', ' ')
            lines.append('%s%s  %s / （中文待填）  [p%s；%spt]' % (indent, kind, text, r['idx'], r.get('size')))
            continue
        t = (r.get('text') or '').strip()
        if not t:
            continue
        if kind in ('body', 'list') or r.get('images'):
            if current is None:
                preface_body += len(t)
            else:
                body_chars += len(t)
    flush()
    if preface_body:
        lines.append('（标题前正文约 %d 字，也需一句概述）' % preface_body)
    lines.append('')
    lines.append('## 统计（只能放最后）')
    lines.append('')
    c = Counter(override.get(str(r.get('idx'))) or r.get('kind') for r in rows)
    lines.append('- 标题：' + ' / '.join('%s=%d' % (k, c.get(k, 0)) for k in ['L0','L1','L2','L3','L4']))
    lines.append('- 正文段=%d，列表=%d，空段=%d，图片段=%d' % (c.get('body',0), c.get('list',0), c.get('empty',0), c.get('image',0)))
    lines.append('- 链接=%d，脚注=%d，图片=%d' % (len(data.get('links', [])), len(data.get('notes', [])), sum(len(r.get('images', [])) for r in rows)))
    lines.append('')
    lines.append('> 说明：只给正文写 [内容概述]，标题本身不写；概述用一句话极致缩写，代替正文供快速审阅。')
    open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('OK ' + out)
    print('headings', len([r for r in rows if (override.get(str(r.get('idx'))) or r.get('kind')) in LEVEL_ORDER]))
    return 0

if __name__ == '__main__':
    sys.exit(main())
