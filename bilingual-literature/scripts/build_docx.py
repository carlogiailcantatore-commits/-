#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""Build a bilingual DOCX from the BLM intermediate Markdown."""
import sys, os, re, json
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.opc.part import Part
from docx.opc.packuri import PackURI
from docx.opc.constants import RELATIONSHIP_TYPE as RT

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

# ---- 真脚注（footnotes.xml） ----
NOTE_MARK_RE = re.compile(r'\[注([A-Za-z0-9._\-]+)\]')
NOTE_HEAD_RE = re.compile(r'^##\s*注释')
NOTE_ITEM_RE = re.compile(r'^\*\*\[([^\]]+)\]\*\*\s*(.*)$')
FOOTNOTES_PARTNAME = '/word/footnotes.xml'
FOOTNOTES_CT = 'application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml'


def xml_escape(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def build_footnotes_xml(entries):
    """entries: [(fid, text)]；text 可含 \n（原文 + 译文各一行）。"""
    head = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">')
    sep = ('<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
           '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>')
    body = []
    for fid, text in entries:
        lines = [ln for ln in (text or '').split('\n')]
        paras = []
        for ln in lines:
            paras.append('<w:p><w:pPr><w:pStyle w:val="FootnoteText"/></w:pPr>'
                         '<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % xml_escape(ln))
        body.append('<w:footnote w:id="%d">%s</w:footnote>' % (fid, ''.join(paras)))
    return head + sep + ''.join(body) + '</w:footnotes>'


def attach_footnotes(doc, entries):
    part = Part(PackURI(FOOTNOTES_PARTNAME), FOOTNOTES_CT,
                build_footnotes_xml(entries).encode('utf-8'), doc.part.package)
    doc.part.relate_to(part, RT.FOOTNOTES)


def add_footnote_ref(par, fid, size_pt):
    r = par.add_run()
    rPr = r._r.get_or_add_rPr()
    rStyle = OxmlElement('w:rStyle')
    rStyle.set(qn('w:val'), 'FootnoteReference')
    va = OxmlElement('w:vertAlign')
    va.set(qn('w:val'), 'superscript')
    rPr.append(rStyle)
    rPr.append(va)
    ref = OxmlElement('w:footnoteReference')
    ref.set(qn('w:id'), str(fid))
    r._r.append(ref)


def ensure_footnote_styles(doc):
    try:
        ft = doc.styles['Footnote Text']
    except KeyError:
        ft = doc.styles.add_style('Footnote Text', WD_STYLE_TYPE.PARAGRAPH)
        ft.base_style = doc.styles['Normal']
    ft.font.size = Pt(9)
    try:
        fr = doc.styles['Footnote Reference']
    except KeyError:
        fr = doc.styles.add_style('Footnote Reference', WD_STYLE_TYPE.CHARACTER)
    fr.font.superscript = True


def split_note_blocks(blocks):
    """抽走 BLM 的「## 注释」区，返回 (剩余 blocks, notes=[{nid,text,zh}])。"""
    out, notes = [], []
    i, n = 0, len(blocks)
    while i < n:
        kind, val = blocks[i]
        if kind == 'raw' and NOTE_HEAD_RE.match(val.strip()):
            i += 1
            while i < n and blocks[i][0] == 'raw' and not blocks[i][1].strip():
                i += 1
            while i < n:
                kind2, v2 = blocks[i]
                s = v2.strip()
                if not s:
                    i += 1
                    continue
                m = NOTE_ITEM_RE.match(s)
                if not m:
                    break
                nid, text = m.group(1).strip(), m.group(2).strip()
                i += 1
                while i < n and blocks[i][0] == 'raw' and not blocks[i][1].strip():
                    i += 1
                zh = ''
                if i < n and blocks[i][0] == 'raw' and blocks[i][1].strip().startswith('>'):
                    zh = blocks[i][1].strip()[1:].strip()
                    i += 1
                notes.append({'nid': nid, 'text': text, 'zh': zh})
            continue
        out.append(blocks[i])
        i += 1
    return out, notes


def inject_term_markers(blocks, notes):
    """没有内联 [注N] 的注释（如专有名词）→ 在该词首次出现处补标记。"""
    markers = set()
    for kind, val in blocks:
        if kind == 'raw':
            markers.update(NOTE_MARK_RE.findall(val))
    for nt in notes:
        nid = str(nt.get('nid'))
        term = (nt.get('text') or '').strip()
        if not term or nid in markers:
            continue
        for idx, (kind, val) in enumerate(blocks):
            if kind != 'raw':
                continue
            s = val
            stripped = s.lstrip()
            if stripped.startswith('#') or stripped.startswith('>'):
                continue
            if term in s:
                blocks[idx] = (kind, s.replace(term, term + '[注%s]' % nid, 1))
                markers.add(nid)
                break
    return markers


def add_text_with_notes(par, text, size_pt, color, ctx):
    """把 [注N] 渲染成真脚注引用；ctx 为 None 时退化为普通文本。"""
    if not ctx or '[注' not in text:
        add_inline(par, text, size_pt, color)
        return
    pos = 0
    for m in NOTE_MARK_RE.finditer(text):
        if m.start() > pos:
            add_inline(par, text[pos:m.start()], size_pt, color)
        fid = ctx['ref'](m.group(1))
        if fid:
            add_footnote_ref(par, fid, size_pt)
        pos = m.end()
    if pos < len(text):
        add_inline(par, text[pos:], size_pt, color)

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

HEADING_SIZES = {1: 18, 2: 16, 3: 14, 4: 13}   # L1..L4 → Heading 1..4
TITLE_SIZE = 22                                  # L0 → 自定义 DocTitle（不进目录）

def ensure_heading_styles(doc):
    """L0 用自定义 DocTitle（不参与目录）；L1–L4 映射到 Word 内置 Heading 1–4，
    字号照旧但带大纲级别，导航窗格与“插入目录”才能识别。"""
    try:
        title = doc.styles['DocTitle']
    except KeyError:
        title = doc.styles.add_style('DocTitle', WD_STYLE_TYPE.PARAGRAPH)
        title.base_style = doc.styles['Normal']
    title.font.size = Pt(TITLE_SIZE)
    title.font.bold = True
    title.font.color.rgb = BLACK
    title.font.name = 'Times New Roman'
    for lv, size in HEADING_SIZES.items():
        name = 'Heading %d' % lv
        try:
            st = doc.styles[name]
        except KeyError:
            st = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            st.base_style = doc.styles['Normal']
            st.paragraph_format.outline_level = lv - 1
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = BLACK
        st.font.name = 'Times New Roman'
        rPr = st.element.get_or_add_rPr()
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is None:
            rFonts = OxmlElement('w:rFonts')
            rPr.append(rFonts)
        rFonts.set(qn('w:eastAsia'), CJK_SOURCE_FONT)
    for name in ('DocTitle',):
        rPr = doc.styles[name].element.get_or_add_rPr()
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is None:
            rFonts = OxmlElement('w:rFonts')
            rPr.append(rFonts)
        rFonts.set(qn('w:eastAsia'), CJK_SOURCE_FONT)

def add_toc(doc, title='目录'):
    """插入 TOC 域；Word 打开后右键“更新域”或按 F9 生成目录条目。"""
    p = doc.add_paragraph()
    r = p.add_run(title)
    r.bold = True
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    fp = doc.add_paragraph()
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), r'TOC \o "1-3" \h \z \u')
    rr = OxmlElement('w:r')
    t = OxmlElement('w:t')
    t.text = '（目录占位：在 Word 中右键“更新域”生成）'
    rr.append(t)
    fld.append(rr)
    fp._p.append(fld)

def add_page_number_footer(section):
    """页脚居中显示 PAGE / NUMPAGES 域。"""
    footer = section.footer
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def field(instr):
        run = p.add_run()
        b = OxmlElement('w:fldChar'); b.set(qn('w:fldCharType'), 'begin')
        it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = instr
        sep = OxmlElement('w:fldChar'); sep.set(qn('w:fldCharType'), 'separate')
        tt = OxmlElement('w:t'); tt.text = '1'
        end = OxmlElement('w:fldChar'); end.set(qn('w:fldCharType'), 'end')
        for el in (b, it, sep, tt, end):
            run._r.append(el)

    field('PAGE')
    p.add_run(' / ')
    field('NUMPAGES')

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
    style_name = 'DocTitle' if level == 1 else 'Heading %d' % min(level - 1, 4)
    if short:
        p = doc.add_paragraph(style=style_name)
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
            p = doc.add_paragraph(style=style_name)
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.keep_together = True
            p.paragraph_format.space_before = Pt(10 if not is_zh else 0)
            p.paragraph_format.space_after = Pt(4 if not is_zh else 8)
            if is_zh:
                r = p.add_run(txt); set_run_font(r, size, True, False, BLUE, east)
            else:
                add_inline(p, '**' + txt + '**', size, BLACK)

def body_pair(doc, original, translation, src_pt=None, target='zh', notes_ctx=None):
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
        add_text_with_notes(p1, original, src_size, BLACK, notes_ctx)
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
    # 抽走「## 注释」区 → 真脚注；没有内联标记的（专有名词）在首次出现处补标记
    blocks, notes = split_note_blocks(blocks)
    inject_term_markers(blocks, notes)
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
    ensure_heading_styles(doc)
    ensure_footnote_styles(doc)
    # 真脚注上下文：同一条注释被多次引用时，各给一个独立脚注 id
    fn_state = {'next': 1, 'entries': [], 'used': set()}

    def note_ref(nid_key):
        key = str(nid_key)
        note = next((n for n in notes if str(n.get('nid')) == key), None)
        if not note:
            return None
        fid = fn_state['next']
        fn_state['next'] += 1
        text = note.get('text') or ''
        if note.get('zh'):
            text += '\n' + note['zh']
        fn_state['entries'].append((fid, text))
        fn_state['used'].add(key)
        return fid

    notes_ctx = {'ref': note_ref}
    # 让 Word 打开时自动更新域（目录/页码），无需用户手动按 F9
    try:
        upd = OxmlElement('w:updateFields')
        upd.set(qn('w:val'), 'true')
        doc.settings.element.append(upd)
    except Exception:
        pass
    sec = doc.sections[0]
    sec.page_width = Cm(21.0); sec.page_height = Cm(29.7)
    sec.left_margin = Cm(2.0); sec.right_margin = Cm(2.0)
    sec.top_margin = Cm(2.0); sec.bottom_margin = Cm(2.0)
    add_page_number_footer(sec)
    usable_pt = (21.0 / 2.54 * 72) - 113.4
    pending = None
    pending_src = None
    # 原文没有 L0 标题时，直接把目录放在文档最前面
    has_title = False
    for kind, val in blocks:
        if kind == 'raw' and re.match(r'^#\s+\S', val.strip()):
            has_title = True
            break
    toc_added = False
    if not has_title:
        add_toc(doc)
        toc_added = True
    for kind, val in blocks:
        if kind == 'code':
            if pending is not None:
                body_pair(doc, pending, None, pending_src, target, notes_ctx=notes_ctx); pending = None
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
                body_pair(doc, pending, None, pending_src, target, notes_ctx=notes_ctx); pending = None
            lv = len(m.group(1))
            heading_src = pending_src if not heading_map else None
            heading(doc, lv, m.group(2).strip(), usable_pt, heading_src, target, heading_map.get('L%d' % lv))
            # 文档标题（L0）之后插入目录；标题用 DocTitle，不进目录
            if not toc_added and lv == 1:
                add_toc(doc)
                toc_added = True
            continue
        if s.startswith('!['):
            if pending is not None:
                body_pair(doc, pending, None, pending_src, target, notes_ctx=notes_ctx); pending = None
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
                body_pair(doc, pending, trans, pending_src, target, notes_ctx=notes_ctx); pending = None
            else:
                body_pair(doc, '', trans, pending_src, target, notes_ctx=notes_ctx)
            continue
        bm = re.match(r'^\*\*(.+)\*\*$', s)
        if bm:
            if pending is not None:
                body_pair(doc, pending, None, pending_src, target, notes_ctx=notes_ctx); pending = None
            p = doc.add_paragraph()
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(3)
            add_inline(p, '**' + bm.group(1) + '**', pending_src or (BODY_PT + 1), BLACK)
            continue
        am = re.match(r'^<([^>]+)>(.*)$', s)
        if am:
            s = am.group(1) + am.group(2)
        if pending is not None:
            body_pair(doc, pending, None, pending_src, target, notes_ctx=notes_ctx)
        pending = s
    if pending is not None:
        body_pair(doc, pending, None, pending_src, target, notes_ctx=notes_ctx)
    # 未被引用的注释（术语在正文没出现）退回「注释」区，避免丢内容
    unused = [n for n in notes if str(n.get('nid')) not in fn_state['used']]
    if unused:
        heading(doc, 2, '注释', usable_pt, None, target)
        for nt in unused:
            p = doc.add_paragraph()
            r = p.add_run('[%s] ' % nt.get('nid'))
            set_run_font(r, BODY_PT, True, False, BLACK)
            add_inline(p, nt.get('text') or '', BODY_PT, BLACK)
            if nt.get('zh'):
                p2 = doc.add_paragraph()
                add_inline(p2, nt['zh'], max(8, BODY_PT - 2), BLUE)
    if fn_state['entries']:
        attach_footnotes(doc, fn_state['entries'])
        print('footnotes: %d (unused notes kept in section: %d)' % (len(fn_state['entries']), len(unused)))
    doc.save(out_path)
    print('OK ' + out_path)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: build_docx.py <bilingual.md> <out.docx>')
        sys.exit(2)
    build(sys.argv[1], sys.argv[2])
