#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""BLM Markdown -> plain TXT (original line + indented translation line)."""
import sys, re
FENCE = chr(96) * 3

def parse(path):
    lines = open(path, 'r', encoding='utf-8').read().split('\n')
    meta = {}
    i = 0
    if lines and lines[0].strip() == '---':
        i = 1
        while i < len(lines) and lines[i].strip() != '---':
            if ':' in lines[i]:
                k, v = lines[i].split(':', 1); meta[k.strip()] = v.strip()
            i += 1
        i += 1
    blocks = []
    in_code = False; code = []
    for line in lines[i:]:
        if line.strip().startswith(FENCE):
            if in_code:
                blocks.append(('code', '\n'.join(code))); code = []; in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code.append(line); continue
        blocks.append(('raw', line))
    if code: blocks.append(('code', '\n'.join(code)))
    return meta, blocks

def build(md, out):
    meta, blocks = parse(md)
    lines = []
    pending = None
    for kind, val in blocks:
        if kind == 'code':
            if pending is not None:
                lines.append(pending); pending = None
            for ln in val.split('\n'):
                if ln.strip():
                    lines.append(ln)
            lines.append('')
            continue
        s = val.strip()
        if not s:
            continue
        if s.startswith('<!-- blm '):
            continue
        m = re.match(r'^(#{1,5})\s+(.*)$', s)
        if m:
            if pending is not None:
                lines.append(pending); pending = None
            lines.append(''); lines.append(m.group(2).strip()); lines.append('')
            continue
        if s.startswith('>'):
            trans = s[1:].strip()
            if pending is not None:
                lines.append(pending); lines.append('  ' + trans); lines.append(''); pending = None
            else:
                lines.append('  ' + trans); lines.append('')
            continue
        if s.startswith('!['):
            mm = re.match(r'!\[[^\]]*\]\(([^)]+)\)', s)
            if mm:
                if pending is not None:
                    lines.append(pending); pending = None
                lines.append('[图片: ' + mm.group(1) + ']'); lines.append('')
            continue
        bm = re.match(r'^\*\*(.+)\*\*$', s)
        if bm:
            if pending is not None:
                lines.append(pending); pending = None
            lines.append(''); lines.append(bm.group(1).strip()); lines.append('')
            continue
        lm = re.match(r'^[-*]\s+(.*)$', s)
        if lm:
            if pending is not None:
                lines.append(pending); pending = None
            lines.append('  - ' + lm.group(1))
            continue
        if pending is not None:
            lines.append(pending); lines.append('')
        pending = s
    if pending is not None:
        lines.append(pending); lines.append('')
    txt = '\n'.join(lines)
    txt = re.sub(r'\n{3,}', '\n\n', txt).strip() + '\n'
    open(out, 'w', encoding='utf-8').write(txt)
    print('OK ' + out)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: build_txt.py <bilingual.md> <out.txt>'); sys.exit(2)
    build(sys.argv[1], sys.argv[2])
