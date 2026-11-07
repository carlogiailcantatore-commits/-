#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Source parsers for grading vocabularies (PDF/HTML)."""
import re, io

def parse_source(name, data, src):
    fn = {
        'goethe_pdf': parse_goethe,
        'profilo_html': parse_profilo,
        'pcic_html': parse_pcic,
        'torfl_pdf': parse_torfl,
        'hsk_xls': parse_hsk_xls,
    }.get(name)
    if not fn:
        raise RuntimeError('UNKNOWN_PARSER: ' + name)
    return fn(data, src)

# ---------------- German: Goethe Wortliste PDF ----------------
def parse_goethe(data, src):
    import pymupdf
    level = src.get('level', 'A1')
    doc = pymupdf.open(stream=data, filetype='pdf')
    out = {}
    for page in doc:
        for b in page.get_text('dict').get('blocks', []):
            if b.get('type') != 0:
                continue
            for line in b.get('lines', []):
                txt = ''.join(s.get('text', '') for s in line.get('spans', [])).strip()
                if not txt:
                    continue
                txt = re.sub(r'\s{2,}.*$', '', txt)  # cut example column
                txt = txt.strip()
                if not txt or len(txt) > 60:
                    continue
                if re.search(r'[.!?]', txt) and not re.search(r',\s*-', txt):
                    continue
                if txt.isupper():
                    continue
                if not (re.match(r'^(der|die|das|sich)\s', txt) or re.match(r'^[a-zäöüß]', txt)):
                    continue
                if re.match(r'^(Seite|VS_|Goethe|Wortliste|Alphabetische|Inventare|Inhalt|WORTLISTE)', txt):
                    continue
                head = re.split(r',\s*-', txt)[0]
                head = re.split(r'\s{2,}', head)[0].strip()
                head = re.sub(r'\s+', ' ', head)
                if not head or len(head) > 30:
                    continue
                if ' ' in head:
                    head = re.sub(r'^sich\s+', '', head)
                    if ' ' in head:
                        continue
                head = head.strip(' ,;:-')
                if not re.match(r'^[a-zäöüß-]{2,30}$', head):
                    continue
                out[head.lower()] = level
    doc.close()
    return out

def split_variants(head):
    head = re.sub(r'^\(sich\)\s*', 'sich ', head)
    head = re.sub(r'^(der|die|das)\s+', '', head)
    head = head.strip(' /')
    parts = [p.strip() for p in re.split(r'\s*/\s*', head) if p.strip()]
    return parts

# ---------------- Italian: Profilo della lingua italiana ----------------
def parse_profilo(data, src):
    level = src.get('level', 'A1')
    t = data.decode('utf-8', errors='replace')
    t = re.sub(r'<script[\s\S]*?</script>', ' ', t, flags=re.I)
    t = re.sub(r'<style[\s\S]*?</style>', ' ', t, flags=re.I)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'&nbsp;', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    out = {}
    for m in re.finditer(r'(?:^|\s)(\d{1,4})\.\s+([^()]{1,80}?)\s*\(([^()]{1,40})\)', t):
        word = m.group(2).strip()
        word = re.sub(r'\s+', ' ', word)
        word = re.sub(r'\([^)]*\)', '', word).strip()
        if not word or re.search(r'\d', word):
            continue
        for part in re.split(r'\s*/\s*', word):
            part = part.strip().lower()
            if part and len(part) <= 30 and ' ' not in part and re.match(r'^[a-zàèéìíòóùú]+$', part):
                out[part] = level
    return out

# ---------------- Spanish: PCIC inventories ----------------
def parse_pcic(data, src):
    from lxml import html as LH
    levels = src.get('levels') or ['A1', 'A2']
    root = LH.fromstring(data)
    out = {}
    import copy
    for tr in root.iter('tr'):
        tds = tr.findall('td')
        if len(tds) < 2:
            continue
        for i, lv in enumerate(levels[:2]):
            td = copy.deepcopy(tds[i])
            for em in td.xpath('.//em'):
                em.getparent().remove(em)
            txt = ' '.join(td.itertext())
            for w in re.findall(r'[a-záéíóúüñ]{2,}', txt):
                out[w] = lv
    return out

def _find_tesseract():
    import shutil, os
    for c in ('tesseract', r'C:\Program Files\Tesseract-OCR\tesseract.exe', r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
        if os.path.isabs(c):
            if os.path.exists(c): return c
        else:
            p = shutil.which(c)
            if p: return p
    return None

def _ocr_pdf_text(data, lang='rus'):
    import pymupdf, subprocess, tempfile, os
    tess = _find_tesseract()
    if not tess:
        return ''
    doc = pymupdf.open(stream=data, filetype='pdf')
    texts = []
    env = os.environ.copy()
    td = os.path.join(os.getcwd(), 'tessdata')
    if os.path.isdir(td):
        env['TESSDATA_PREFIX'] = td
    with tempfile.TemporaryDirectory() as td:
        for i in range(doc.page_count):
            pix = doc[i].get_pixmap(dpi=200)
            png = os.path.join(td, 'p%04d.png' % (i + 1))
            pix.save(png)
            try:
                r = subprocess.run([tess, png, 'stdout', '-l', lang], capture_output=True, text=True, timeout=180, env=env)
                texts.append(r.stdout)
            except Exception:
                pass
    doc.close()
    return '\n'.join(texts)

# ---------------- Russian: TORFL lexical minimum PDF ----------------
def parse_torfl(data, src):
    import pymupdf
    doc = pymupdf.open(stream=data, filetype='pdf')
    text = '\n'.join(p.get_text() for p in doc)
    doc.close()
    cyr = sum(1 for ch in text if 0x0400 <= ord(ch) <= 0x04FF)
    if cyr < max(50, len(text) * 0.15):
        text = _ocr_pdf_text(data, 'rus')
        cyr = sum(1 for ch in text if 0x0400 <= ord(ch) <= 0x04FF)
        if cyr < 50:
            raise RuntimeError('OCR_REQUIRED: PDF 文本层损坏/为扫描件，需 OCR；未内置俄语词表')
    level = src.get('level', 'B1')
    out = {}
    for line in text.split('\n'):
        line = line.strip()
        if not line or len(line) > 40:
            continue
        for w in re.findall(r'[А-Яа-яЁё\-]{2,}', line):
            out[w.lower()] = level
    return out


# ---------------- Chinese: official HSK 2.0 XLS ----------------
def parse_hsk_xls(data, src):
    import xlrd
    wb = xlrd.open_workbook(file_contents=data)
    sheet = None
    for name in ('新HSK5000词', '新HSK（六级）（5000）'):
        if name in wb.sheet_names():
            sheet = wb.sheet_by_name(name)
            break
    if sheet is None:
        sheet = wb.sheet_by_index(0)
    level_map = {'一': 'HSK1', '二': 'HSK2', '三': 'HSK3', '四': 'HSK4', '五': 'HSK5', '六': 'HSK6'}
    out = {}
    for r in range(sheet.nrows):
        raw = str(sheet.cell_value(r, 0) or '').strip()
        if not raw:
            continue
        m = re.match(r'(.+?)（([一二三四五六])级）', raw)
        if m:
            word = m.group(1).strip()
            lv = level_map.get(m.group(2))
            if word and lv:
                out[word] = lv
    if not out:
        raise RuntimeError('HSK_PARSE_EMPTY')
    return out
