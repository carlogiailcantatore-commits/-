#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""专有名词抽取 + 注释（脚注式）生成（P2）。

用法：
  python terms.py extract <source.json|txt|md> <terms.json> [--min-count 2] [--limit 40]
  python terms.py notes <terms.json> <notes.json> [--prefix term]

抽词规则：
  - 《…》 / «…» 书名、篇名（中文/拉丁通用）；
  - 拉丁大写开头的专有名词串（如 “Dan Forrest”“St. Louis”），排除常见句首虚词；
  - 出现次数 >= --min-count（默认 2），按次数排序取前 --limit。
notes 输出可直接并入 work.json 的 notes（build_blm 会渲染成「注释」区，脚注式排版）。
"""
import argparse
import json
import os
import re
import sys

BOOK_RE = re.compile(r'[《«]([^》»]{1,60})[》»]')
CAP_RE = re.compile(r'\b([A-ZÀ-Þ][a-zà-ÿ]{2,}(?:\s+(?:of|de|del|della|di|von|van|St\.?)?\s*[A-ZÀ-Þ][a-zà-ÿ]+){0,3})\b')
STOP_CAP = set('''Il Lo La I Gli Le Un Uno Una Questo Questa Questi Queste Perché Ma Se Non E Ed O Anche
Come Quando Dove Però Quindi Alla Alle Dello Della Dei Delle Nel Nella Sul Sulla Tra Fra
The A An This That These Those And But Or If When Where Because So However Also In On At By For With
Chapter Part Preface Introduction Conclusion Note Example Esempio Parte Capitolo Prefazione'''.split())
ASCII_OK = re.compile(r'^[A-Za-zÀ-ÿ0-9 .\'\-]+$')


def read_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.json':
        data = json.load(open(path, encoding='utf-8'))
        if 'paragraphs' in data:
            return '\n'.join(p.get('text') or '' for p in data['paragraphs'])
        if 'blocks' in data:
            return '\n'.join(b.get('text') or '' for b in data['blocks'])
        return ''
    return open(path, encoding='utf-8').read()


def extract(text, min_count=2, limit=40):
    counts = {}
    types = {}

    def add(term, typ):
        t = term.strip().strip('.,;:()[]')
        if not t or len(t) < 2:
            return
        if typ == 'latin' and not ASCII_OK.match(t):
            return
        key = t
        counts[key] = counts.get(key, 0) + 1
        types.setdefault(key, typ)

    for m in BOOK_RE.finditer(text):
        add(m.group(1), 'title')
    for para in text.split('\n'):
        s = para.strip()
        for m in CAP_RE.finditer(s):
            term = m.group(1)
            head = term.split()[0]
            if head in STOP_CAP or term in STOP_CAP:
                continue
            if m.start() == 0:
                continue  # 句首大写多为普通词
            add(term, 'latin')
    items = []
    for term, c in counts.items():
        if c >= min_count:
            items.append({'term': term, 'count': c, 'type': types.get(term, 'latin')})
    items.sort(key=lambda x: (-x['count'], x['term']))
    return {'terms': items[:limit], 'total_candidates': len(items)}


def to_notes(terms_obj, prefix='term'):
    notes = []
    for i, t in enumerate(terms_obj.get('terms') or [], 1):
        notes.append({'nid': '%s-%d' % (prefix, i), 'text': t['term'], 'term': t['term'], 'count': t.get('count')})
    return {'notes': notes}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd')
    a = sub.add_parser('extract')
    a.add_argument('src'); a.add_argument('out')
    a.add_argument('--min-count', type=int, default=2)
    a.add_argument('--limit', type=int, default=40)
    b = sub.add_parser('notes')
    b.add_argument('terms'); b.add_argument('out')
    b.add_argument('--prefix', default='term')
    args = ap.parse_args()
    if args.cmd == 'extract':
        text = read_text(args.src)
        obj = extract(text, args.min_count, args.limit)
        json.dump(obj, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('OK %s terms=%d' % (args.out, len(obj['terms'])))
        for t in obj['terms'][:10]:
            print('  %-30s x%d (%s)' % (t['term'], t['count'], t['type']))
        return 0
    if args.cmd == 'notes':
        obj = json.load(open(args.terms, encoding='utf-8'))
        notes = to_notes(obj, args.prefix)
        json.dump(notes, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('OK %s notes=%d' % (args.out, len(notes['notes'])))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
