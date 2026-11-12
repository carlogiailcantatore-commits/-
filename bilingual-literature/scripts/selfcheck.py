#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""交付前自检（P2）：一次跑完结构/切分/链接/DOCX 结构的硬检查。

用法（参数都可选，给了才查）：
  python selfcheck.py [--units units.json] [--structure structure.json]
                      [--md bilingual.md] [--docx out.docx]
                      [--max-links 15] [--json report.json]
退出码：0 全过；1 有失败。

检查项：
  1. 切分保真：units 里每段的 sents 拼接必须等于原文（忽略空白）
  2. 结构合法：复用 gate.check（跳级/孤儿段/synth 标题）
  3. 残留标记：md 里不得有 ⟦L⟧ / ⟦F⟧ / ⟦IMG⟧ token
  4. 标题层级：md 的 # 数量必须与 structure 期望一致
  5. 链接约束：复用 linkcheck（上限/去重/年份不挂）
  6. DOCX 结构：含 TOC 域、Heading 样式带大纲级别、页脚含 PAGE 域
"""
import argparse
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gate
import linkcheck

LEVELS = ('L0', 'L1', 'L2', 'L3', 'L4')
TOKEN_RE = re.compile(r'⟦(?:L\d+|F\d+|IMG\d+)⟧')


def load(path):
    return json.load(open(path, encoding='utf-8')) if path else None


def check_units(units):
    bad = []
    for p in units.get('paragraphs', []):
        text = p.get('text') or ''
        sents = p.get('sents') or []
        if not sents:
            continue
        a = re.sub(r'\s+', '', text)
        b = re.sub(r'\s+', '', ''.join(s.get('text') or '' for s in sents))
        if a != b:
            bad.append(p.get('idx'))
    return {'name': 'split_fidelity', 'ok': not bad, 'detail': {'mismatch_pids': bad[:10]}}


def check_structure(structure, units):
    rep = gate.check(structure, units)
    return {'name': 'structure', 'ok': rep['ok'],
            'detail': {'errors': rep['errors'][:10], 'warnings': rep['warnings'][:10]}}


def check_md(md_text, structure):
    tokens = TOKEN_RE.findall(md_text)
    heads = {}
    for line in md_text.split('\n'):
        m = re.match(r'^(#{1,5})\s+\S', line)
        if m:
            heads[len(m.group(1))] = heads.get(len(m.group(1)), 0) + 1
    ok = not tokens
    detail = {'residual_tokens': len(tokens), 'headings': heads}
    if structure:
        kinds = {str(k): v for k, v in (structure.get('kinds') or {}).items()}
        synth = structure.get('synth') or []
        exp = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for v in kinds.values():
            if v in LEVELS:
                exp[int(v[1]) + 1] = exp.get(int(v[1]) + 1, 0) + 1
        # synth 是结构里补的标题，不在 kinds 统计里
        for s in synth:
            lv = int(s.get('kind', 'L1')[1]) + 1
            exp[lv] = exp.get(lv, 0) + 1
        exp = {k: v for k, v in exp.items() if v}
        got = {k: v for k, v in heads.items() if v}
        if exp != got:
            ok = False
            detail['expected'] = exp
    return {'name': 'md_structure', 'ok': ok, 'detail': detail}


def check_links(md_text, max_links):
    rep = linkcheck.check_links(md_text, max_links)
    return {'name': 'links', 'ok': rep['ok'], 'detail': {'total': rep['total'], 'errors': rep['errors'][:10]}}


def check_docx(path):
    if not os.path.exists(path):
        return {'name': 'docx', 'ok': False, 'detail': {'error': 'missing file'}}
    z = zipfile.ZipFile(path)
    xml = z.read('word/document.xml').decode('utf-8')
    styles = z.read('word/styles.xml').decode('utf-8')
    footers = [n for n in z.namelist() if n.startswith('word/footer')]
    page_ok = any('PAGE' in z.read(f).decode('utf-8') for f in footers)
    toc_ok = 'TOC' in xml
    heading_ok = 'Heading1' in styles and 'outlineLvl' in styles
    ok = toc_ok and heading_ok and page_ok
    return {'name': 'docx', 'ok': ok,
            'detail': {'toc': toc_ok, 'heading_outline': heading_ok, 'page_number': page_ok}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--units')
    ap.add_argument('--structure')
    ap.add_argument('--md')
    ap.add_argument('--docx')
    ap.add_argument('--max-links', type=int, default=15)
    ap.add_argument('--json')
    a = ap.parse_args()

    units = load(a.units)
    structure = load(a.structure)
    md_text = open(a.md, encoding='utf-8').read() if a.md and os.path.exists(a.md) else None

    checks = []
    if units:
        checks.append(check_units(units))
    if units and structure:
        checks.append(check_structure(structure, units))
    if md_text is not None:
        checks.append(check_md(md_text, structure))
        checks.append(check_links(md_text, a.max_links))
    if a.docx:
        checks.append(check_docx(a.docx))

    ok = all(c['ok'] for c in checks)
    rep = {'ok': ok, 'checks': checks}
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    for c in checks:
        print(('  ✓ ' if c['ok'] else '  ✗ ') + c['name'])
    if a.json:
        json.dump(rep, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
