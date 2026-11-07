#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""Verify BLM/Notion Markdown with declared degradations and JSON report."""
import sys, os, json, re
TOKEN = re.compile(r'⟦(?:L\d+|F\d+|IMG\d+)⟧')

def norm(s): return re.sub(r'\s+', '', s or '')

def load_deg(path):
    if not path or not os.path.exists(path): return []
    try:
        o=json.load(open(path,encoding='utf-8'))
        return o.get('degradations', o if isinstance(o,list) else [])
    except Exception: return []

def arg(name, default=None):
    return sys.argv[sys.argv.index(name)+1] if name in sys.argv else default

def main():
    work, md_path = arg('--work'), arg('--md')
    if not work or not md_path:
        print('usage: verify_md.py --work work.json --md bilingual.md [--degradations d.json] [--report r.json]')
        return 2
    w=json.load(open(work,encoding='utf-8'))
    md=open(md_path,encoding='utf-8').read()
    md=re.sub(r'<!-- blm .*?-->\n?', '', md)
    flat=norm(re.sub(r'\*\*|\[([^\]]*)\]\([^)]*\)', r'\1', md))
    degs=load_deg(arg('--degradations'))
    allowed={'MISSING_IMAGE','MISSING_FOOTNOTE','PAGE_BREAK'}
    dec={}
    for d in degs:
        if d.get('code') in allowed and d.get('accepted_by_user', True):
            dec[d.get('code')]=dec.get(d.get('code'),0)+int(d.get('count') or 1)
    missing=[]
    for it in w.get('items',[]):
        if it.get('kind')=='image': continue
        if it.get('kind') in ('L0','L1','L2','L3','L4','label','data','linkline'):
            frags=[it.get('it') or '']
        else:
            frags=[s.get('text') or '' for s in (it.get('sents') or [])]
        for f in frags:
            for p in TOKEN.split(f):
                p=norm(p)
                if len(p)>=4 and p not in flat:
                    missing.append((it.get('pid'),p[:70]))
    urls=set()
    for it in w.get('items',[]):
        for l in it.get('links') or []:
            if l.get('url'): urls.add(l['url'])
    not_covered=[u for u in urls if ']('+u+')' not in md]
    imgs_src=sum(len(it.get('images') or []) for it in w.get('items',[]))
    imgs_md=len(re.findall(r'!\[[^\]]*\]\([^)]*\)', md))
    notes_src=len(w.get('notes') or [])
    note_md=len(set(re.findall(r'\[注\d+\]', md)))
    lines=md.split('\n')
    bad=[(i+1,l[:50]) for i,l in enumerate(lines) if l.startswith('> ') and (i==0 or not lines[i-1].strip() or lines[i-1].startswith('> '))]
    empty=md.count('\n\n\n')
    failures=[]
    if missing: failures.append({'code':'TEXT_LOSS','count':len(missing),'items':missing[:15]})
    if not_covered: failures.append({'code':'LINK_MISMATCH','count':len(not_covered),'items':not_covered[:10]})
    if imgs_src-dec.get('MISSING_IMAGE',0)!=imgs_md: failures.append({'code':'MISSING_IMAGE','expected':imgs_src-dec.get('MISSING_IMAGE',0),'actual':imgs_md})
    if notes_src-dec.get('MISSING_FOOTNOTE',0)!=note_md: failures.append({'code':'MISSING_FOOTNOTE','expected':notes_src-dec.get('MISSING_FOOTNOTE',0),'actual':note_md})
    if bad: failures.append({'code':'ORPHAN_TRANSLATION','count':len(bad),'items':bad[:10]})
    if empty: failures.append({'code':'EMPTY_PARAGRAPH','count':empty})
    status='FAIL' if failures else ('PASS_DEGRADED' if dec else 'PASS')
    report={'schema_version':1,'status':status,'checks':{
        'source_fragments':'fail' if missing else 'pass','links':'fail' if not_covered else 'pass',
        'images':'fail' if any(f['code']=='MISSING_IMAGE' for f in failures) else 'pass',
        'footnotes':'fail' if any(f['code']=='MISSING_FOOTNOTE' for f in failures) else 'pass',
        'pairs':'fail' if bad else 'pass','empty_paragraphs':'fail' if empty else 'pass'},
        'source':{'images':imgs_src,'links':len(urls),'footnotes':notes_src},
        'output':{'images':imgs_md,'note_markers':note_md},
        'degradations':[d for d in degs if d.get('code') in dec],'warnings':[],'failures':failures}
    print(json.dumps(report,ensure_ascii=False,indent=1))
    if arg('--report'): json.dump(report,open(arg('--report'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    print('VERIFY_MD '+status)
    return 0 if status!='FAIL' else 1

if __name__=='__main__':
    sys.exit(main())
