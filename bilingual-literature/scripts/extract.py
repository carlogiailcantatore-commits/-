#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""Extract span-level structure from DOCX / PDF / TXT into JSON.

Usage: python extract.py <input> <out.json>
DOCX output keeps paragraph text plus ordered spans:
  {"t":"text","s":"...","b":false,"size":24}
  {"t":"link","s":"...","url":"...","b":false,"size":24}
  {"t":"fn","id":1}
  {"t":"img","name":"image1.jpeg"}
Exit codes: 0 ok; 2 unsupported; 3 PDF has no text layer (OCR required).
"""
import sys, os, json, re
from collections import Counter

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
def q(t): return W + t

def text_of(el):
    return ''.join((t.text or '') for t in el.iter(q('t')))

def run_style(r):
    rPr = r.find(q('rPr'))
    size = None
    bold = False
    italic = False
    color = None
    if rPr is not None:
        s = rPr.find(q('sz'))
        if s is not None:
            try: size = int(s.get(q('val')) or 0)
            except Exception: pass
        b = rPr.find(q('b'))
        if b is not None and b.get(q('val')) not in ('0', 'false'):
            bold = True
        i = rPr.find(q('i'))
        if i is not None and i.get(q('val')) not in ('0', 'false'):
            italic = True
        c = rPr.find(q('color'))
        if c is not None:
            color = c.get(q('val'))
    return {'b': bold, 'i': italic, 'size': size, 'color': color}

def paragraph_spans(p, relmap):
    spans = []
    sizes = []
    bold_any = False
    italic_any = False
    for child in p:
        tag = child.tag
        if tag == q('r'):
            st = run_style(child)
            if st['size']:
                sizes.append(st['size'])
            if st['b']:
                bold_any = True
            if st['i']:
                italic_any = True
            # footnote refs
            for f in child.findall(q('footnoteReference')):
                try:
                    spans.append({'t': 'fn', 'id': int(f.get(q('id')))})
                except Exception:
                    spans.append({'t': 'fn', 'id': f.get(q('id'))})
            # drawings
            for e in child.iter():
                if e.get(R + 'embed'):
                    tgt = relmap.get(e.get(R + 'embed'))
                    if tgt:
                        spans.append({'t': 'img', 'name': os.path.basename(tgt)})
            # ordered text nodes
            for node in child.iter():
                if node.tag == q('t'):
                    spans.append({'t': 'text', 's': (node.text or ''), 'b': st['b'], 'i': st['i'], 'size': st['size'], 'color': st['color']})
                elif node.tag == q('br'):
                    spans.append({'t': 'text', 's': '\n', 'b': st['b'], 'i': st['i'], 'size': st['size'], 'color': st['color']})
                elif node.tag == q('tab'):
                    spans.append({'t': 'text', 's': '\t', 'b': st['b'], 'i': st['i'], 'size': st['size'], 'color': st['color']})
        elif tag == q('hyperlink'):
            rid = child.get(R + 'id')
            anchor = child.get(W + 'anchor')
            tgt = relmap.get(rid) if rid else ('#' + anchor if anchor else None)
            txt = text_of(child)
            st = {'b': False, 'i': False, 'size': None, 'color': None}
            for r in child.iter(q('r')):
                st2 = run_style(r)
                if st2['size']: sizes.append(st2['size'])
                if st2['b']: bold_any = True
                if st2['i']: italic_any = True
                st = st2
            spans.append({'t': 'link', 's': txt, 'url': tgt, 'b': st['b'], 'i': st['i'], 'size': st['size'], 'color': st['color']})
    return spans, sizes, bold_any, italic_any

def extract_docx(path):
    import zipfile
    from lxml import etree
    with zipfile.ZipFile(path) as z:
        doc = z.read('word/document.xml')
        rels = z.read('word/_rels/document.xml.rels')
        foot = z.read('word/footnotes.xml') if 'word/footnotes.xml' in z.namelist() else None
        media = [n for n in z.namelist() if n.startswith('word/media/')]
    root = etree.fromstring(doc)
    body = root.find(q('body'))
    relmap = {x.get('Id'): x.get('Target') for x in etree.fromstring(rels)}
    paras = []
    for i, p in enumerate(body.findall(q('p'))):
        spans, sizes, bold_any, italic_any = paragraph_spans(p, relmap)
        pPr = p.find(q('pPr'))
        style = None
        align = None
        numpr = False
        if pPr is not None:
            ps = pPr.find(q('pStyle'))
            if ps is not None: style = ps.get(q('val'))
            jc = pPr.find(q('jc'))
            if jc is not None: align = jc.get(q('val'))
            if pPr.find(q('numPr')) is not None: numpr = True
        paras.append({
            'index': i,
            'spans': spans,
            'text': text_of(p),
            'sizes': sorted(set(sizes)),
            'bold': bold_any,
            'italic': italic_any,
            'style': style,
            'align': align,
            'numbered': numpr,
            'images': [s['name'] for s in spans if s['t'] == 'img'],
            'links': [{'text': s['s'], 'target': s['url']} for s in spans if s['t'] == 'link'],
            'fnrefs': [s['id'] for s in spans if s['t'] == 'fn'],
        })
    notes = []
    if foot is not None:
        fr = etree.fromstring(foot)
        for fn in fr.findall(q('footnote')):
            try: fid = int(fn.get(q('id')))
            except Exception: continue
            if fid < 1: continue
            txt = ' '.join(text_of(x) for x in fn.findall(q('p'))).strip()
            if txt:
                notes.append({'id': fid, 'text': txt})
    sect = root.find('.//' + q('sectPr'))
    page = {}
    if sect is not None:
        pg = sect.find(q('pgSz')); mar = sect.find(q('pgMar'))
        if pg is not None and mar is not None:
            try:
                page = {
                    'width_pt': int(pg.get(q('w'))) / 20.0,
                    'height_pt': int(pg.get(q('h'))) / 20.0,
                    'margin_left_pt': int(mar.get(q('left'))) / 20.0,
                    'margin_right_pt': int(mar.get(q('right'))) / 20.0,
                }
            except Exception:
                pass
    return {'format': 'docx', 'file': os.path.basename(path), 'paragraphs': paras, 'footnotes': notes, 'media': media, 'page': page}

def extract_pdf(path):
    import pymupdf
    doc = pymupdf.open(path)
    total = 0
    blocks = []
    for pno in range(doc.page_count):
        d = doc[pno].get_text('dict')
        for b in d.get('blocks', []):
            if b.get('type') != 0:
                continue
            for line in b.get('lines', []):
                spans = line.get('spans', [])
                txt = ''.join(s.get('text', '') for s in spans).strip()
                if not txt:
                    continue
                size = max((s.get('size') or 0) for s in spans) if spans else 0
                bold = any('Bold' in (s.get('font') or '') for s in spans)
                blocks.append({'page': pno + 1, 'text': txt, 'size': round(size, 1), 'bold': bold,
                               'spans': [{'t': 'text', 's': s.get('text', ''), 'b': 'Bold' in (s.get('font') or ''), 'size': round(s.get('size') or 0, 1)} for s in spans]})
                total += len(txt)
    if total < 50:
        doc.close()
        return {'format': 'pdf', 'error': 'no_text_layer', 'chars': total}
    cnt = Counter()
    for b in blocks:
        cnt[b['size']] += len(b['text'])
    body_size = cnt.most_common(1)[0][0] if cnt else 0
    doc.close()
    return {'format': 'pdf', 'file': os.path.basename(path), 'blocks': blocks, 'body_size': body_size, 'images_note': 'PDF images not extracted in v0.2'}
def extract_txt(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()
    parts = re.split(r'\n\s*\n', raw)
    paras = [{'index': i, 'text': p.strip(), 'spans': [{'t': 'text', 's': p.strip()}]} for i, p in enumerate(parts) if p.strip()]
    return {'format': 'txt', 'file': os.path.basename(path), 'paragraphs': paras}
def main():
    if len(sys.argv) < 3:
        print('usage: extract.py <input> <out.json>')
        return 2
    src, out = sys.argv[1], sys.argv[2]
    ext = os.path.splitext(src)[1].lower()
    if ext == '.docx':
        data = extract_docx(src)
    elif ext == '.pdf':
        data = extract_pdf(src)
        if data.get('error') == 'no_text_layer':
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            print('PDF_NO_TEXT_LAYER: OCR required')
            return 3
    elif ext in ('.txt', '.md'):
        data = extract_txt(src)
    else:
        print('UNSUPPORTED: ' + ext)
        return 2
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print('OK ' + out)
    return 0
if __name__ == '__main__':
    sys.exit(main())
