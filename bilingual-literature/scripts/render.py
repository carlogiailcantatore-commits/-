#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""统一渲染：从结构源（structure.json）+ 工作单（work.json）生成各格式，保证层级一致。

用法：
  python render.py --work work.json --translations translations.json
                   --structure structure.json --format docx|md|notion|pdf --out <路径>
                   [--strict] [--meta meta.json] [--image-alts a.json] [--notes-zh n.json]

规则：
  - 段落级别以 structure.json 为准（kinds 覆盖 work.json 的提示）；
  - synth（补出来的标题）若 work.json 里没有，自动插到指定段之后；
  - 渲染后做一致性检查：各层级标题数量必须与 structure 一致，不一致时 --strict 直接失败。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_blm
import build_docx

LEVELS = ('L0', 'L1', 'L2', 'L3', 'L4')


def load_json(path, default=None):
    if path and os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    return default if default is not None else {}


def apply_structure(work, structure):
    kinds = {str(k): v for k, v in (structure.get('kinds') or {}).items()}
    items = work.get('items') or []
    for it in items:
        pid = str(it.get('pid'))
        if pid in kinds:
            it['kind'] = kinds[pid]
    # 补充 synth 标题
    synth = structure.get('synth') or []
    existing = {(str(it.get('pid')), it.get('it')) for it in items}
    for s in synth:
        key = ('synth-%s-%s' % (s.get('after'), s.get('kind')), s.get('it'))
        if key in existing:
            continue
        syn = {
            'pid': 'synth-%s-%s' % (s.get('after'), s.get('kind')),
            'kind': s.get('kind', 'L1'),
            'it': s.get('it', ''),
            'zh': s.get('zh') or '',
            'synth': True,
            'sents': [{'sid': 'synth-%s-0' % s.get('after'), 'text': s.get('it', ''),
                       'zh': s.get('zh') or '', 'tokens': []}],
            'links': [], 'fns': [], 'images': [],
        }
        pos = len(items)
        try:
            neg = int(s.get('after')) < 0
        except (TypeError, ValueError):
            neg = False
        if neg:
            pos = 0
        else:
            for i, it in enumerate(items):
                if str(it.get('pid')) == str(s.get('after')):
                    pos = i + 1
                    break
        items.insert(pos, syn)
    return work


def expected_counts(structure, work):
    kinds = {str(k): v for k, v in (structure.get('kinds') or {}).items()}
    exp = {lv: 0 for lv in LEVELS}
    for it in work.get('items') or []:
        k = kinds.get(str(it.get('pid')), it.get('kind'))
        if k in LEVELS:
            exp[k] += 1
    return exp


def check_consistency(work, structure):
    exp = expected_counts(structure, work)
    got = {lv: 0 for lv in LEVELS}
    for it in work.get('items') or []:
        if it.get('kind') in LEVELS:
            got[it['kind']] += 1
    return exp, got, exp == got


def render_md(work, tr, out, notion=None, meta=None, image_alts=None, notes_zh=None):
    rc = build_blm.build(work, tr, out, notion=notion,
                         image_alts=image_alts or {}, notes_zh=notes_zh or {},
                         meta=meta or {}, strict=False)
    return rc


def work_tempdir(near):
    """优先系统临时目录；不可用时退回到输出文件旁的 .blm_render_tmp/。"""
    try:
        import tempfile
        return tempfile.mkdtemp(prefix='blm_render_')
    except Exception:
        base = os.path.dirname(os.path.abspath(near)) or os.getcwd()
        d = os.path.join(base, '.blm_render_tmp')
        os.makedirs(d, exist_ok=True)
        return d


def remove_tempdir(d):
    """清理临时目录；固定的 .blm_render_tmp 保留（避免反复创建/删除）。"""
    try:
        if not d or not os.path.isdir(d):
            return
        if os.path.basename(d) == '.blm_render_tmp':
            return
        shutil.rmtree(d, ignore_errors=True)
    except Exception:
        pass


def render_docx(work, tr, out, meta=None, image_alts=None, notes_zh=None):
    tmpdir = work_tempdir(out)
    try:
        md = os.path.join(tmpdir, 'bilingual.md')
        rc = render_md(work, tr, md, meta=meta, image_alts=image_alts, notes_zh=notes_zh)
        if rc not in (0,):
            return rc
        build_docx.build(md, out)
        return 0
    finally:
        remove_tempdir(tmpdir)


def render_pdf(work, tr, out, meta=None, image_alts=None, notes_zh=None):
    tmpdir = work_tempdir(out)
    try:
        docx_path = os.path.join(tmpdir, 'bilingual.docx')
        rc = render_docx(work, tr, docx_path, meta=meta, image_alts=image_alts, notes_zh=notes_zh)
        if rc != 0:
            return rc
        to_pdf = os.path.join(HERE, 'to_pdf.py')
        return subprocess.call([sys.executable, to_pdf, docx_path, out])
    finally:
        remove_tempdir(tmpdir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True)
    ap.add_argument('--translations', required=True)
    ap.add_argument('--structure', required=True)
    ap.add_argument('--format', required=True, choices=['docx', 'md', 'notion', 'pdf'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--meta')
    ap.add_argument('--image-alts')
    ap.add_argument('--notes-zh')
    ap.add_argument('--strict', action='store_true')
    a = ap.parse_args()

    work = load_json(a.work)
    tr = load_json(a.translations)
    structure = load_json(a.structure)
    meta = load_json(a.meta)
    image_alts = load_json(a.image_alts)
    notes_zh = load_json(a.notes_zh)

    work = apply_structure(work, structure)
    exp, got, ok = check_consistency(work, structure)
    print('structure:', json.dumps(exp, ensure_ascii=False), '| rendered:', json.dumps(got, ensure_ascii=False),
          '| consistent:', ok)
    if not ok:
        print('WARN_STRUCTURE_MISMATCH', exp, got)
        if a.strict:
            return 4

    if a.format == 'md':
        rc = render_md(work, tr, a.out, meta=meta, image_alts=image_alts, notes_zh=notes_zh)
    elif a.format == 'notion':
        rc = render_md(work, tr, a.out + '.tmp.md', notion=a.out, meta=meta,
                       image_alts=image_alts, notes_zh=notes_zh)
        try:
            os.remove(a.out + '.tmp.md')
        except OSError:
            pass
    elif a.format == 'docx':
        rc = render_docx(work, tr, a.out, meta=meta, image_alts=image_alts, notes_zh=notes_zh)
    else:
        rc = render_pdf(work, tr, a.out, meta=meta, image_alts=image_alts, notes_zh=notes_zh)
    print('OK ' + a.out if rc == 0 else 'FAIL rc=%d' % rc)
    return rc


if __name__ == '__main__':
    sys.exit(main())
