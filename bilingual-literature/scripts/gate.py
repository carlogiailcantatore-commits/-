#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""结构关卡：suggest（建议）→ apply（确认落地）→ check（校验）

用法：
  python gate.py suggest <units.json> <structure.suggest.json>
         [--min-chars 600] [--target-chars 1200] [--sim-threshold 0.05]
  python gate.py apply <structure.suggest.json> <structure.json> [--decisions decisions.json]
  python gate.py check <structure.json> <units.json>

structure.json 是全流程唯一结构源：
  {"version":1, "source":..., "kinds":{"12":"L1"}, "synth":[{"after":12,"kind":"L1","it":"","zh":""}],
   "reason":{"12":"bold+short"}, "chapters":[{"level":1,"it":"","zh":"","paras":[12,30]}]}
"""
import json
import os
import re
import sys
from collections import Counter

LEVELS = ('L0', 'L1', 'L2', 'L3', 'L4')
HEAD_RE = re.compile(r'^(?:第[一二三四五六七八九十百]+[章节部分篇]|Parte\s+[IVXLC\d]+|Capitolo\s+\d+|Chapter\s+\d+|'
                     r'[一二三四五六七八九十]+[、.．]|\d+[、.．]\s|序[一二三四五六七八九十]?[、.．]?)', re.I)
STOP = set('的了在是有和就不人都一这那为以于而且与或及等之其所以因为但是可以我们你们他们这个那个没有自己什么'
           'il lo la i gli le un uno una di a da in con su per tra fra che è sono non più come anche questo questa '
           'the a an of to in on for and or with is are was were be been that this these those it its as at by from')


def load(path):
    return json.load(open(path, encoding='utf-8'))


def bigrams(text):
    t = re.sub(r'\s+', '', text.lower())
    t = re.sub(r'[^\w\u4e00-\u9fff]+', '', t)
    return {t[i:i + 2] for i in range(len(t) - 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def keywords(text, n=2):
    s = re.sub(r'[^\w\u4e00-\u9fff]+', ' ', text)
    cand = Counter()
    for w in s.split():
        w = w.lower()
        if re.fullmatch(r'[a-z]{3,}', w) and w not in STOP:
            cand[w] += 2
    zh = re.sub(r'[^\u4e00-\u9fff]', '', s)
    skip = set('的了在和是有就不人都这那为以于而且与或及等之其所以因为但是可以我们你们他们这个那个没有自己什么'
               '里最不个上中下也都还会把被让给对从到就才又很呢吧啊吗')
    for i in range(len(zh) - 1):
        g = zh[i:i + 2]
        if g[0] in skip or g[1] in skip:
            continue
        cand[g] += 1
    if not cand:
        return ''
    out = []
    for min_c in (2, 1):
        for w, c in cand.most_common(400):
            if c < min_c:
                break
            if any((w in x) or (x in w) for x in out):
                continue
            if any(set(w) & set(x) for x in out):
                continue
            out.append(w)
            if len(out) >= n:
                return ' · '.join(out)
    return ' · '.join(out)


def body_rows(units):
    rows = []
    for p in units.get('paragraphs', []):
        kind = p.get('kind')
        text = (p.get('text') or '').strip()
        if kind in ('image', 'empty') or not text:
            continue
        rows.append({'pid': p.get('idx'), 'kind': kind, 'text': text, 'len': len(text)})
    return rows


def suggest(units, min_chars=600, target_chars=1200, thr=0.05):
    rows = body_rows(units)
    kinds, synth, reason, chapters = {}, [], {}, []

    # 1) 沿用已有的标题提示（L1–L4）
    headings = [r for r in rows if r['kind'] in LEVELS and r['kind'] != 'L0']
    title = next((r for r in rows if r['kind'] == 'L0'), None)
    # split_units 会把第一段当 L0；三种情形要纠正：
    #   a) 这段很长 → 原文没有标题，降为正文
    #   b) 这段以句末标点结尾（是一句话而非标题）→ 降为正文
    #   c) 这段本身是编号标题（第一章/序四…）→ 降为正文，后面按编号重新定级
    if title and (title['len'] > 60 or re.search(r'[。！？.!?]$', title['text'])):
        kinds[str(title['pid'])] = 'body'
        title = None
    elif title and HEAD_RE.match(title['text']):
        kinds[str(title['pid'])] = 'body'
        title = None
    for r in headings:
        kinds[str(r['pid'])] = r['kind']
        reason[str(r['pid'])] = 'layout:heading_hint'

    # 2) 标题足够多 → 不做语义分章
    if len(headings) >= 3:
        return _pack(units, kinds, synth, reason, chapters, title, 'layout', 0.9)

    # 3) 分章：已有标题 / 编号标题 / 语义切点（长度 + 相邻相似度）
    def head_kind(text):
        return 'L1' if re.match(r'^(?:第[一二三四五六七八九十百]+[部分篇]|Parte|Prefazione|序)', text, re.I) else 'L2'

    seq = [r for r in rows if r['pid'] != (title or {}).get('pid')]
    if not seq:
        return _pack(units, kinds, synth, reason, chapters, title, 'layout', 0.9)

    cur = None
    for r in seq:
        k = kinds.get(str(r['pid'])) or r['kind']
        is_layout_heading = k in LEVELS and k != 'L0'
        is_numbered = bool(HEAD_RE.match(r['text'])) and r['len'] <= 48
        if is_layout_heading or is_numbered:
            if cur:
                chapters.append(cur)
            lv = k if is_layout_heading else head_kind(r['text'])
            kinds[str(r['pid'])] = lv
            reason[str(r['pid'])] = 'layout:heading_hint' if is_layout_heading else 'layout:numbered_heading'
            cur = {'level': int(lv[1]), 'it': r['text'].strip(), 'zh': '',
                   'paras': [r['pid'], r['pid']], 'heading_pid': r['pid'],
                   'chars': 0, 'first_text': '', 'last_text': ''}
            continue
        if cur is None:
            cur = {'level': 1, 'it': '', 'zh': '', 'paras': [r['pid'], r['pid']],
                   'heading_pid': None, 'chars': 0, 'first_text': r['text'], 'last_text': ''}
        acc = cur['chars']
        sim = jaccard(bigrams(cur['last_text']), bigrams(r['text'])) if cur['last_text'] else 1.0
        if acc and (acc >= target_chars or (acc >= min_chars and sim < thr)):
            chapters.append(cur)
            cur = {'level': 1, 'it': '', 'zh': '', 'paras': [r['pid'], r['pid']],
                   'heading_pid': None, 'chars': 0, 'first_text': r['text'], 'last_text': ''}
        cur['paras'][1] = r['pid']
        cur['chars'] += r['len']
        cur['last_text'] = r['text']
        if not cur['first_text']:
            cur['first_text'] = r['text']
    if cur:
        chapters.append(cur)

    level = 'L1'
    pid_text = {r['pid']: r['text'] for r in rows}
    for gi, c in enumerate(chapters):
        if c['heading_pid'] is None:
            span = ' '.join(pid_text[p] for p in range(c['paras'][0], c['paras'][1] + 1) if p in pid_text)[:800]
            title_text = keywords(span, 2) or ('第%d部分' % (gi + 1))
            after = c['paras'][0] - 1 if c['paras'][0] > 0 else -1
            synth.append({'after': after, 'kind': level, 'it': title_text, 'zh': '', 'auto': True})
            reason['synth-%d' % c['paras'][0]] = 'semantic:topic_shift'
            c['it'] = title_text
        c.pop('heading_pid', None)
        c.pop('chars', None)
        c.pop('first_text', None)
        c.pop('last_text', None)
    conf = 0.55 if len(chapters) > 1 else 0.35
    return _pack(units, kinds, synth, reason, chapters, title, 'semantic', conf)


def _pack(units, kinds, synth, reason, chapters, title, mode, conf):
    stats = Counter()
    for p in units.get('paragraphs', []):
        k = kinds.get(str(p.get('idx')), p.get('kind'))
        stats[k] += 1
    return {
        'version': 1,
        'source': units.get('source'),
        'mode': mode,
        'confidence': conf,
        'kinds': kinds,
        'synth': synth,
        'reason': reason,
        'chapters': chapters,
        'stats': dict(stats),
    }


def apply(suggest_obj, decisions_path=None):
    dec = {}
    if decisions_path and os.path.exists(decisions_path):
        dec = load(decisions_path)
    kinds = dict(suggest_obj.get('kinds') or {})
    kinds.update({str(k): v for k, v in (dec.get('kinds') or {}).items()})
    synth = list(suggest_obj.get('synth') or [])
    if 'synth' in dec:
        synth = list(dec['synth'])
    chapters = list(suggest_obj.get('chapters') or [])
    if 'chapters' in dec:
        chapters = list(dec['chapters'])
    return {
        'version': 1,
        'source': suggest_obj.get('source'),
        'mode': suggest_obj.get('mode'),
        'kinds': kinds,
        'synth': synth,
        'reason': suggest_obj.get('reason') or {},
        'chapters': chapters,
    }


def check(structure, units):
    errors, warnings = [], []
    rows = units.get('paragraphs', [])
    pids = {str(p.get('idx')) for p in rows}
    kinds = {str(k): v for k, v in (structure.get('kinds') or {}).items()}
    synth_at = {}
    for s in structure.get('synth') or []:
        try:
            pos = int(s.get('after')) + 1
        except (TypeError, ValueError):
            pos = 0
        synth_at.setdefault(pos, []).append(s)

    unknown = [k for k in kinds if k not in pids]
    if unknown:
        errors.append({'code': 'UNKNOWN_PID', 'pids': unknown[:10]})

    # 层级：不能跳级（L1→L3）；synth 视为插入点处的 L1
    prev = 0
    for p in rows:
        pid = p.get('idx')
        for _ in synth_at.get(pid, []):
            prev = prev or 1
        k = kinds.get(str(pid), p.get('kind'))
        if k in LEVELS and k != 'L0':
            lv = int(k[1]) + 1
            if prev and lv - prev > 1:
                errors.append({'code': 'LEVEL_JUMP', 'pid': pid, 'from': prev, 'to': lv})
            prev = lv

    # 孤儿段：正文出现在第一个标题（含 synth）之前
    seen_heading = False
    for p in rows:
        pid = p.get('idx')
        if synth_at.get(pid):
            seen_heading = True
        k = kinds.get(str(pid), p.get('kind'))
        if k in LEVELS:
            seen_heading = True
        elif k == 'body' and not seen_heading:
            errors.append({'code': 'ORPHAN_BODY', 'pid': pid})

    # synth 必须带原文标题
    for s in structure.get('synth') or []:
        if not (s.get('it') or '').strip():
            errors.append({'code': 'EMPTY_SYNTH_TITLE', 'after': s.get('after')})
        if not (s.get('zh') or '').strip():
            warnings.append({'code': 'SYNTH_NO_ZH', 'after': s.get('after')})

    return {'ok': not errors, 'errors': errors, 'warnings': warnings}


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == 'suggest':
        units = load(argv[2])
        opts = {}
        for i, a in enumerate(argv):
            if a == '--min-chars':
                opts['min_chars'] = int(argv[i + 1])
            elif a == '--target-chars':
                opts['target_chars'] = int(argv[i + 1])
            elif a == '--sim-threshold':
                opts['thr'] = float(argv[i + 1])
        out = suggest(units, **opts)
        json.dump(out, open(argv[3], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('OK ' + argv[3])
        print('mode=%s confidence=%.2f chapters=%d synth=%d'
              % (out['mode'], out['confidence'], len(out['chapters']), len(out['synth'])))
        return 0
    if cmd == 'apply':
        sug = load(argv[2])
        dec = None
        if '--decisions' in argv:
            dec = argv[argv.index('--decisions') + 1]
        st = apply(sug, dec)
        json.dump(st, open(argv[3], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('OK ' + argv[3])
        return 0
    if cmd == 'check':
        st = load(argv[2])
        units = load(argv[3])
        rep = check(st, units)
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        return 0 if rep['ok'] else 1
    print('unknown command: ' + cmd)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
