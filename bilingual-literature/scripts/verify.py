#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify DOCX output against source.json, with declared degradations and JSON report.

Usage: verify.py <source.json> <out.docx> [--degradations d.json] [--report r.json]
"""
import sys, os, json, re, zipfile

def norm(s):
    s = (s or '').replace('\u00a0', ' ')
    return re.sub(r'\s+', '', s)

def docx_text(path):
    from lxml import etree
    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml')
    root = etree.fromstring(xml)
    body = root.find(W + 'body')
    parts = []
    skipped = 0
    for p in body.findall(W + 'p'):
        for r in p.iter(W + 'r'):
            rPr = r.find(W + 'rPr')
            skip = False
            if rPr is not None:
                col = rPr.find(W + 'color')
                if col is not None and (col.get(W + 'val') or '').upper() == '1F4E79':
                    skip = True
            if skip:
                skipped += 1
                continue
            for t in r.findall(W + 't'):
                parts.append(t.text or '')
    return norm(''.join(parts)), skipped

def docx_stats(path):
    from docx import Document
    doc = Document(path)
    links = 0
    try:
        for rel in doc.part.rels.values():
            if rel.reltype.endswith('/hyperlink'):
                links += 1
    except Exception:
        pass
    images = 0
    notes = 0
    with zipfile.ZipFile(path) as z:
        images = len([n for n in z.namelist() if n.startswith('word/media/')])
        if 'word/footnotes.xml' in z.namelist():
            try:
                from lxml import etree
                W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
                root = etree.fromstring(z.read('word/footnotes.xml'))
                notes = len([f for f in root.findall(W + 'footnote') if int(f.get(W + 'id') or 0) > 0])
            except Exception:
                pass
    return {'images': images, 'links': links, 'footnotes': notes}

def source_stats(data):
    paragraphs = data.get('paragraphs') or data.get('blocks') or []
    links = 0
    for p in paragraphs:
        links += len(p.get('links') or [])
    return {'images': len(data.get('media', [])), 'links': links, 'footnotes': len(data.get('footnotes', []))}

def load_degradations(path):
    if not path or not os.path.exists(path):
        return []
    try:
        obj = json.load(open(path, encoding='utf-8'))
        return obj.get('degradations', obj if isinstance(obj, list) else [])
    except Exception:
        return []

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print('usage: verify.py <source.json> <out.docx> [--degradations d.json] [--report r.json]')
        return 2
    src, out = args[0], args[1]
    deg_path = args[args.index('--degradations') + 1] if '--degradations' in args else None
    report_path = args[args.index('--report') + 1] if '--report' in args else None
    data = json.load(open(src, encoding='utf-8'))
    out_text, skipped = docx_text(out)
    out_markers = len(set(re.findall(r'\[注\d+\]', out_text)))
    out_text = re.sub(r'\[注\d+\]', '', out_text)
    ss = source_stats(data)
    os_ = docx_stats(out)
    os_['footnotes'] = max(os_.get('footnotes', 0), out_markers)
    degradations = load_degradations(deg_path)
    allowed = {'MISSING_IMAGE', 'MISSING_FOOTNOTE', 'PAGE_BREAK'}
    dec = {}
    for d in degradations:
        code = d.get('code')
        if code in allowed and d.get('accepted_by_user', True):
            dec[code] = dec.get(code, 0) + int(d.get('count') or 1)
    failures = []
    missing = []
    paragraphs = data.get('paragraphs') or data.get('blocks') or []
    checked = 0
    for p in paragraphs:
        t = p.get('text', '').strip()
        if len(t) < 15:
            continue
        checked += 1
        if norm(t) not in out_text:
            missing.append(t[:80])
    if missing:
        failures.append({'code': 'TEXT_LOSS', 'count': len(missing), 'items': missing[:20]})
    expected_images = ss['images'] - dec.get('MISSING_IMAGE', 0)
    if expected_images != os_['images']:
        failures.append({'code': 'MISSING_IMAGE', 'expected': expected_images, 'actual': os_['images']})
    expected_notes = ss['footnotes'] - dec.get('MISSING_FOOTNOTE', 0)
    if expected_notes != os_['footnotes']:
        failures.append({'code': 'MISSING_FOOTNOTE', 'expected': expected_notes, 'actual': os_['footnotes']})
    if ss['links'] != os_['links']:
        failures.append({'code': 'LINK_MISMATCH', 'expected': ss['links'], 'actual': os_['links']})
    status = 'FAIL' if failures else ('PASS_DEGRADED' if dec else 'PASS')
    report = {
        'schema_version': 1,
        'status': status,
        'checks': {
            'source_fragments': 'fail' if missing else 'pass',
            'images': 'fail' if any(f['code'] == 'MISSING_IMAGE' for f in failures) else 'pass',
            'footnotes': 'fail' if any(f['code'] == 'MISSING_FOOTNOTE' for f in failures) else 'pass',
            'links': 'fail' if any(f['code'] == 'LINK_MISMATCH' for f in failures) else 'pass',
        },
        'source': ss,
        'output': os_,
        'output_note_markers': out_markers,
        'translation_runs_skipped': skipped,
        'degradations': [d for d in degradations if d.get('code') in dec],
        'warnings': [],
        'failures': failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if report_path:
        json.dump(report, open(report_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('VERIFY ' + status)
    return 0 if status != 'FAIL' else 1

if __name__ == '__main__':
    sys.exit(main())
