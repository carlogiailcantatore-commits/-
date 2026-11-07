#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""Build bilingual BLM Markdown (and optional Notion Markdown) from work.json + translations.json.

Usage:
  build_blm.py --work work.json --translations translations.json --out bilingual.md
               [--notion notion.md] [--image-alts alts.json] [--notes-zh notes.json]
               [--meta meta.json] [--assets-prefix assets] [--strict]
"""
import sys, os, json, re, argparse

FENCE = chr(96) * 3
HEAD = {'L0': 1, 'L1': 2, 'L2': 3, 'L3': 4, 'L4': 5}
LINK_RE = re.compile(r'⟦L(\d+)⟧')
FN_RE = re.compile(r'⟦F(\d+)⟧')
IMG_RE = re.compile(r'⟦IMG(\d+)⟧')

def load_json(path):
    if path and os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    return {}

def render_text(text, item, image_alts):
    text = text or ''
    def link_sub(m):
        lid = int(m.group(1))
        l = next((x for x in (item.get('links') or []) if int(x.get('lid', 0)) == lid), None)
        if not l:
            return m.group(0)
        anchor = l.get('anchor') or l.get('url') or ''
        return '[%s](%s)' % (anchor, l.get('url') or '')
    def fn_sub(m):
        return '[注%s]' % m.group(1)
    def img_sub(m):
        i = int(m.group(1)) - 1
        imgs = item.get('images') or []
        name = imgs[i] if 0 <= i < len(imgs) else ''
        return '![%s](%s)' % (image_alts.get(name, ''), name)
    text = LINK_RE.sub(link_sub, text)
    text = FN_RE.sub(fn_sub, text)
    text = IMG_RE.sub(img_sub, text)
    return text

def zh_for(key, tr, item=None, sent=None):
    v = tr.get(key)
    if v:
        return v
    if sent is not None and sent.get('zh'):
        return sent['zh']
    if item is not None and item.get('zh'):
        return item['zh']
    return ''

def build(work, tr, out, notion=None, image_alts=None, notes_zh=None, meta=None, assets_prefix='assets', strict=False, sizes_out=None):
    image_alts = image_alts or {}
    notes_zh = notes_zh or {}
    missing = []
    lines = []
    size_blocks = []

    def add_marker(item):
        sz = item.get('size')
        if not sz:
            return
        src = float(sz) / 2.0
        kind = str(item.get('kind') or '')
        pid = item.get('pid')
        size_blocks.append({'pid': pid, 'kind': kind, 'src_pt': src})
        lines.append('<!-- blm pid=%s kind=%s src=%.1f -->' % (pid, kind, src))
    title = ''
    title_zh = ''
    for it in work.get('items', []):
        if it.get('kind') == 'L0':
            title = it.get('it') or title
            title_zh = zh_for('H:%s' % it.get('pid'), tr, it) or title_zh
            break
    m = {
        'source': work.get('source') or '',
        'source_lang': 'it',
        'target_lang': 'zh',
        'domain': '',
        'output_format': 'docx',
        'title_original': title,
        'title_zh': title_zh,
    }
    if meta:
        m.update(meta)
    src_lang = (m.get('source_lang') or 'it').strip()
    tgt_lang = (m.get('target_lang') or 'zh').strip()
    if tgt_lang not in ('zh', 'it') or src_lang == tgt_lang:
        print('PAIR_INVALID: %s -> %s (target must be zh or it, source != target)' % (src_lang, tgt_lang))
        return 2
    lines += ['---'] + ['%s: %s' % (k, m.get(k, '')) for k in ['source','source_lang','target_lang','domain','output_format','title_original','title_zh']] + ['---','']

    def heading_line(level, it, zh, notion_mode=False):
        text = it if not zh else '%s / %s' % (it, zh)
        if notion_mode and level in ('L3', 'L4'):
            return '**%s**' % text
        n = HEAD.get(level, 3)
        return '#' * (n if not notion_mode else min(n, 3)) + ' ' + text

    for it in work.get('items', []):
        kind = it.get('kind')
        if kind in ('L0','L1','L2','L3','L4'):
            zh = zh_for('H:%s' % it.get('pid'), tr, it)
            if not zh:
                missing.append('H:%s' % it.get('pid'))
            add_marker(it)
            lines.append(heading_line(kind, it.get('it') or '', zh))
            lines.append('')
            continue
        if kind == 'image':
            imgs = it.get('images') or []
            for name in imgs:
                lines.append('![%s](%s/%s)' % (image_alts.get(name, ''), assets_prefix, name))
                lines.append('')
            continue
        if kind == 'data':
            add_marker(it)
            lines.append(FENCE)
            for ln in (it.get('it') or '').split('\n'):
                if ln.strip():
                    lines.append(ln)
            lines.append(FENCE)
            lines.append('')
            continue
        if kind == 'label':
            add_marker(it)
            zh = zh_for('L:%s' % it.get('pid'), tr, it)
            text = render_text(it.get('it') or '', it, image_alts)
            lines.append('**%s**' % (text + (' / ' + zh if zh else '')))
            lines.append('')
            continue
        if kind == 'linkline':
            add_marker(it)
            lines.append(render_text(it.get('it') or '', it, image_alts))
            lines.append('')
            continue
        # body/list: one pair per sentence
        sents = it.get('sents') or []
        if not sents and it.get('it'):
            sents = [{'sid': 'p%s_0' % it.get('pid'), 'text': it.get('it'), 'tokens': []}]
        first = True
        for s in sents:
            if first:
                add_marker(it); first = False
            orig = render_text(s.get('text') or '', it, image_alts)
            zh = zh_for(s.get('sid'), tr, it, s)
            if not zh:
                missing.append(s.get('sid'))
                zh = '（待译）'
            lines.append(orig)
            lines.append('> ' + zh)
            lines.append('')
    # footnote section
    notes = work.get('notes') or []
    if notes:
        lines.append('## 注释')
        lines.append('')
        for n in notes:
            nid = n.get('nid')
            zh = notes_zh.get(str(nid)) or notes_zh.get(nid) or tr.get('FN:%s' % nid) or '（待译）'
            lines.append('**[%s]** %s' % (nid, n.get('text') or ''))
            lines.append('> ' + zh)
            lines.append('')
    text = '\n'.join(lines).rstrip() + '\n'
    if sizes_out:
        sz = {'schema_version': 1, 'body_pt': float(work.get('body_size') or 0) / 2.0, 'blocks': size_blocks}
        os.makedirs(os.path.dirname(os.path.abspath(sizes_out)), exist_ok=True)
        json.dump(sz, open(sizes_out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('OK ' + sizes_out + ' blocks=' + str(len(size_blocks)))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(text)
    print('OK ' + out + ' chars=' + str(len(text)))
    if notion:
        nlines = []
        in_yaml = False
        for line in lines:
            s = line
            if s.strip().startswith('<!-- blm '):
                continue
            mm = re.match(r'^(#{4,5})\s+(.*)$', s)
            if mm:
                s = '**' + mm.group(2) + '**'
            nlines.append(s)
        ntext = '\n'.join(nlines).rstrip() + '\n'
        open(notion, 'w', encoding='utf-8').write(ntext)
        print('OK ' + notion + ' chars=' + str(len(ntext)))
    if missing:
        print('MISSING_TRANSLATIONS %d' % len(missing))
        for k in missing[:20]:
            print('  ' + str(k))
        if strict:
            return 3
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True); ap.add_argument('--translations', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--notion')
    ap.add_argument('--image-alts'); ap.add_argument('--notes-zh'); ap.add_argument('--meta')
    ap.add_argument('--assets-prefix', default='assets'); ap.add_argument('--strict', action='store_true')
    ap.add_argument('--sizes')
    ap.add_argument('--source-lang'); ap.add_argument('--target-lang')
    a = ap.parse_args()
    w = json.load(open(a.work, encoding='utf-8'))
    tr = load_json(a.translations)
    meta = load_json(a.meta)
    if a.source_lang:
        meta['source_lang'] = a.source_lang
    if a.target_lang:
        meta['target_lang'] = a.target_lang
    return build(w, tr, a.out, a.notion, load_json(a.image_alts), load_json(a.notes_zh), meta, a.assets_prefix, a.strict, a.sizes)

if __name__ == '__main__':
    sys.exit(main())
