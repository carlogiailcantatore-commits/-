#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a bilingual DOCX from the BLM intermediate Markdown."""
import sys, os, re, json
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

LEVEL_SIZE = {1: 22, 2: 18, 3: 16, 4: 14, 5: 13}
BODY_PT = 12
BLUE = RGBColor(0x1F, 0x4E, 0x79)
BLACK = RGBColor(0, 0, 0)
URL_BLUE = RGBColor(0x05, 0x63, 0xC1)
KAI = '楷体'
CJK_SOURCE_FONT = 'SimSun'
FENCE = chr(96) * 3

def is_cjk(ch):
    o = ord(ch)
    return (0x4e00 <= o <= 0x9fff or 0x3400 <= o <= 0x4dbf or 0xf900 <= o <= 0xfaff or 0x3040 <= o <= 0x30ff)

def has_kana(s):
    return any(0x3040 <= ord(c) <= 0x30ff for c in s)

def source_run_font(s):
    if has_kana(s):
        return 'Yu Mincho', 'Yu Mincho'
    if has_cjk(s):
        return CJK_SOURCE_FONT, CJK_SOURCE_FONT
    return None, None

def has_cjk(s):
    return any(is_cjk(c) for c in s)

def width_estimate(text, size_pt):
    cjk = sum(1 for c in text if is_cjk(c))
    lat = sum(1 for c in text if c.isascii() and c.isalnum())
    oth = len(text) - cjk - lat
    return (cjk * 1.0 + lat * 0.5 + oth * 0.35) * size_pt

def set_run_font(run, size_pt, bold=False, italic=False, color=BLACK, east='Times New Roman', font_name=None):
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color
    name = font_name or 'Times New Roman'
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts'); rPr.append(rFonts)
    rFonts.set(qn('w:ascii'), name)
    rFonts.set(qn('w:hAnsi'), name)
    rFonts.set(qn('w:eastAsia'), east)

def add_inline(par, text, size_pt, base_color=BLACK, italic=False):
    def plain(s):
        if s:
            r = par.add_run(s)
            fname, east = source_run_font(s)
            if fname:
                set_run_font(r, size_pt, False, italic, base_color, east, fname)
            else:
                set_run_font(r, size_pt, False, italic, base_color)

    i = 0
    while i < len(text):
        nb = text.find('**', i)
        lb = text.find('[', i)
        cand = [x for x in (nb, lb) if x != -1]
        nxt = min(cand) if cand else len(text)
        if nxt > i:
            plain(text[i:nxt])
            i = nxt
            continue
        if nxt == nb:
            end = text.find('**', i + 2)
            if end == -1:
                plain(text[i:])
                break
            r = par.add_run(text[i + 2:end])
            fname, east = source_run_font(text[i + 2:end])
            if fname:
                set_run_font(r, size_pt, True, italic, base_color, east, fname)
            else:
                set_run_font(r, size_pt, True, italic, base_color)
            i = end + 2
            continue
        # link
        mid = text.find('](', i + 1)
        if mid == -1:
            plain(text[i:i + 1])
            i += 1
            continue
        label = text[i + 1:mid]
        j = mid + 2
        depth = 0
        while j < len(text):
            ch = text[j]
            if ch == '(':
                depth += 1
            elif ch == ')':
                if depth == 0:
                    break
                depth -= 1
            j += 1
        url = text[mid + 2:j]
        r = par.add_run(label)
        fname, east = source_run_font(label)
        if fname:
            set_run_font(r, size_pt, False, italic, URL_BLUE, east, fname)
        else:
            set_run_font(r, size_pt, False, italic, URL_BLUE)
        r.underline = True
        try:
            part = par.part
            link = OxmlElement('w:hyperlink')
            link.set(qn('r:id'), part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True))
            r._element.addnext(link)
            link.append(r._element)
        except Exception:
            pass
        i = j + 1

FALLBACK_HEADING = {1: 22, 2: 18, 3: 16, 4: 14, 5: 13}
FALLBACK_BODY = 12
MARKER_RE = re.compile(r'^<!--\s*blm\s+pid=([^\s]+)\s+kind=([A-Za-z0-9]+)\s+src=([0-9.]+)\s*-->$')

def load_profiles():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in ('data/style-profiles.json', 'references/style-profiles.json'):
        path = os.path.join(base, rel)
        if os.path.exists(path):
            try:
                return json.load(open(path, encoding='utf-8'))
            except Exception:
                return {}
    return {}

PROFILES = load_profiles()

def target_profile(target):
    return (PROFILES.get('targets') or {}).get(target) or {}

def heading(doc, level, text, usable_pt, src_pt=None, target='zh', level_pt=None):
    prof = target_profile(target)
    fallback = (PROFILES.get('fallback_heading_pt') or {}).get('L%d' % (level - 1))
    if fallback is None:
        fallback = FALLBACK_HEADING.get(level, 14)
    size = level_pt or src_pt or fallback
    east = prof.get('translation_font') or ('KaiTi' if target == 'zh' else 'Times New Roman')
    it = zh = None
    if ' / ' in text:
        a, b = text.split(' / ', 1)
        if target == 'it' or has_cjk(b) or not has_cjk(a):
            it, zh = a.strip(), b.strip()
    if it is None:
        it = text.strip()
    merged = (it + '/' + zh) if zh else it
    def fits(txt):
        return (not txt) or width_estimate(txt, size) <= usable_pt * 0.90
    short = fits(it) and fits(zh) and width_estimate(merged, size) <= usable_pt * 0.90
    if short:
        p = doc.add_paragraph()
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.keep_together = True
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        add_inline(p, '**' + it + '**', size, BLACK)
        if zh:
            r = p.add_run('/'); set_run_font(r, size, True, False, BLACK)
            r = p.add_run(zh); set_run_font(r, size, True, False, BLUE, east)
    else:
        for txt, is_zh in ((it, False), (zh, True)):
            if not txt:
                continue
            p = doc.add_paragraph()
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.keep_together = True
            p.paragraph_format.space_before = Pt(10 if not is_zh else 0)
            p.paragraph_format.space_after = Pt(4 if not is_zh else 8)
            if is_zh:
                r = p.add_run(txt); set_run_font(r, size, True, False, BLUE, east)
            else:
                add_inline(p, '**' + txt + '**', size, BLACK)

def body_pair(doc, original, translation, src_pt=None, target='zh'):
    prof = target_profile(target)
    src_size = src_pt or (PROFILES.get('fallback_body_pt') or FALLBACK_BODY)
    trans_size = max(8, src_size - 2) if target == 'zh' else src_size
    east = prof.get('translation_font') or ('KaiTi' if target == 'zh' else 'Times New Roman')
    if original:
        p1 = doc.add_paragraph()
        p1.paragraph_format.keep_with_next = True
        p1.paragraph_format.keep_together = True
        p1.paragraph_format.space_before = Pt(3)
        p1.paragraph_format.space_after = Pt(0)
        p1.paragraph_format.left_indent = Pt(0)
        p1.paragraph_format.first_line_indent = Pt(0)
        add_inline(p1, original, src_size, BLACK)
    if translation:
        p2 = doc.add_paragraph()
        p2.paragraph_format.keep_together = True
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(6)
        p2.paragraph_format.left_indent = Pt(0)
        p2.paragraph_format.first_line_indent = Pt(0)
        add_inline(p2, translation, trans_size, BLUE)
        for r in p2.runs:
            r.font.name = 'Times New Roman'
            rPr = r._element.get_or_add_rPr()
            rFonts = rPr.find(qn('w:rFonts'))
            if rFonts is None:
                rFonts = OxmlElement('w:rFonts'); rPr.append(rFonts)
            rFonts.set(qn('w:eastAsia'), east)
            r.font.size = Pt(trans_size)
            r.italic = False
            r.font.color.rgb = BLUE

def parse_md(path):
    lines = open(path, 'r', encoding='utf-8').read().split('\n')
    meta = {}
    i = 0
    if lines and lines[0].strip() == '---':
        i = 1
        while i < len(lines) and lines[i].strip() != '---':
            if ':' in lines[i]:
                k, v = lines[i].split(':', 1)
                meta[k.strip()] = v.strip()
            i += 1
        i += 1
    blocks = []
    in_code = False
    code = []
    for line in lines[i:]:
        if line.strip().startswith(FENCE) or line.strip().startswith('~~~'):
            if in_code:
                blocks.append(('code', '\n'.join(code))); code = []; in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code.append(line); continue
        blocks.append(('raw', line))
    if code:
        blocks.append(('code', '\n'.join(code)))
    return meta, blocks

def build(md_path, out_path):
    meta, blocks = parse_md(md_path)
    target = (meta.get('target_lang') or 'zh').strip()
    if target not in ('zh', 'it'):
        target = 'zh'
    src_map = {}
    for kind, val in blocks:
        if kind != 'raw':
            continue
        mm = MARKER_RE.match(val.strip())
        if not mm:
            continue
        k, src = mm.group(2), float(mm.group(3))
        if k.startswith('L') and k[1:].isdigit():
            lv = int(k[1:]) + 1
            if 1 <= lv <= 5 and lv not in src_map:
                src_map[lv] = src
    heading_map = {}
    present = sorted(src_map.items())
    valid = True
    for i in range(1, len(present)):
        if not (present[i - 1][1] > present[i][1]):
            valid = False
            break
    if valid and present:
        for lv, src in present:
            heading_map['L%d' % lv] = src
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0); sec.page_height = Cm(29.7)
    sec.left_margin = Cm(2.0); sec.right_margin = Cm(2.0)
    sec.top_margin = Cm(2.0); sec.bottom_margin = Cm(2.0)
    usable_pt = (21.0 / 2.54 * 72) - 113.4
    pending = None
    pending_src = None
    for kind, val in blocks:
        if kind == 'code':
            if pending is not None:
                body_pair(doc, pending, None, pending_src, target); pending = None
            for ln in val.split('\n'):
                if ln.strip() == '':
                    continue
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(0); p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.left_indent = Pt(0); p.paragraph_format.first_line_indent = Pt(0)
                r = p.add_run(ln); set_run_font(r, pending_src or BODY_PT, False, False, BLACK)
            continue
        line = val.rstrip('\n'); s = line.strip()
        if not s:
            continue
        mm = MARKER_RE.match(s)
        if mm:
            pending_src = float(mm.group(3))
            continue
        m = re.match(r'^(#{1,5})\s+(.*)$', s)
        if m:
            if pending is not None:
                body_pair(doc, pending, None, pending_src, target); pending = None
            lv = len(m.group(1))
            heading_src = pending_src if not heading_map else None
            heading(doc, lv, m.group(2).strip(), usable_pt, heading_src, target, heading_map.get('L%d' % lv))
            continue
        if s.startswith('!['):
            if pending is not None:
                body_pair(doc, pending, None, pending_src, target); pending = None
            mm = re.match(r'!\[[^\]]*\]\(([^)]+)\)', s)
            if mm:
                path = mm.group(1)
                if not os.path.isabs(path):
                    path = os.path.join(os.path.dirname(os.path.abspath(md_path)), path)
                try:
                    doc.add_picture(path, width=Cm(16.0))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                except Exception:
                    p = doc.add_paragraph(); r = p.add_run('[图片缺失: ' + os.path.basename(path) + ']')
                    set_run_font(r, BODY_PT, False, True, BLUE)
            continue
        if s.startswith('>'):
            trans = s[1:].strip()
            if pending is not None:
                body_pair(doc, pending, trans, pending_src, target); pending = None
            else:
                body_pair(doc, '', trans, pending_src, target)
            continue
        bm = re.match(r'^\*\*(.+)\*\*$', s)
        if bm:
            if pending is not None:
                body_pair(doc, pending, None, pending_src, target); pending = None
            p = doc.add_paragraph()
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(3)
            add_inline(p, '**' + bm.group(1) + '**', pending_src or (BODY_PT + 1), BLACK)
            continue
        am = re.match(r'^<([^>]+)>(.*)$', s)
        if am:
            s = am.group(1) + am.group(2)
        if pending is not None:
            body_pair(doc, pending, None, pending_src, target)
        pending = s
    if pending is not None:
        body_pair(doc, pending, None, pending_src, target)
    doc.save(out_path)
    print('OK ' + out_path)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: build_docx.py <bilingual.md> <out.docx>')
        sys.exit(2)
    build(sys.argv[1], sys.argv[2])
