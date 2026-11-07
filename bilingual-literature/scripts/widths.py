#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure whether each heading's 'IT / 中文' fits on one line.

Usage: widths.py --work work.json --translations translations.json --out widths.tsv
       [--usable-pt 481.9] [--sizes 22,18,16,14,13]
Reads work.json + translations.json; no hardcoded heading list.
"""
import sys, os, json, argparse, csv

SIZES = {'L0': 22, 'L1': 18, 'L2': 16, 'L3': 14, 'L4': 13}

def is_cjk(ch):
    o = ord(ch)
    return 0x4e00 <= o <= 0x9fff

def width_estimate(text, size_pt):
    cjk = sum(1 for c in text if is_cjk(c))
    lat = sum(1 for c in text if c.isascii() and c.isalnum())
    oth = len(text) - cjk - lat
    return (cjk * 1.0 + lat * 0.5 + oth * 0.35) * size_pt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True); ap.add_argument('--translations', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--usable-pt', type=float, default=481.9)
    ap.add_argument('--sizes', default='')
    a = ap.parse_args()
    w = json.load(open(a.work, encoding='utf-8'))
    tr = json.load(open(a.translations, encoding='utf-8'))
    sizes = dict(SIZES)
    if a.sizes:
        vals = [float(x) for x in a.sizes.split(',')]
        for k, v in zip(['L0','L1','L2','L3','L4'], vals):
            sizes[k] = v
    rows = []
    for it in w.get('items', []):
        k = it.get('kind')
        if k not in sizes:
            continue
        itxt = it.get('it') or ''
        zh = tr.get('H:%s' % it.get('pid')) or it.get('zh') or ''
        merged = itxt + ('/' + zh if zh else '')
        est = width_estimate(merged, sizes[k])
        rows.append({'pid': it.get('pid'), 'level': k, 'size_pt': sizes[k], 'width_pt': round(est, 1),
                     'limit_pt': round(a.usable_pt * 0.90, 1), 'short': est <= a.usable_pt * 0.90,
                     'it': itxt, 'zh': zh})
    with open(a.out, 'w', encoding='utf-8', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=['pid','level','size_pt','width_pt','limit_pt','short','it','zh'], delimiter='\t')
        wr.writeheader(); wr.writerows(rows)
    longn = sum(1 for r in rows if not r['short'])
    print('OK ' + a.out + ' headings=%d short=%d long=%d' % (len(rows), len(rows)-longn, longn))
    for r in rows:
        if not r['short']:
            print('LONG %s %s %.1fpt > %.1fpt :: %s / %s' % (r['level'], r['pid'], r['width_pt'], r['limit_pt'], r['it'], r['zh']))
    return 0

if __name__ == '__main__':
    sys.exit(main())
