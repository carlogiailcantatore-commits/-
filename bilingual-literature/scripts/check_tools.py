#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""Report availability of PDF/OCR tools for the bilingual-literature skill."""
import json, os, shutil, importlib.util
try:
    import phonetic as _phonetic
    _espeak = _phonetic.find_espeak()
except Exception:
    _espeak = None
def _find_tess():
    for c in ('tesseract', r'C:\Program Files\Tesseract-OCR\tesseract.exe', r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
        if os.path.isabs(c):
            if os.path.exists(c): return c
        else:
            p = shutil.which(c)
            if p: return p
    return None
_tess = _find_tess()

def find_soffice():
    for p in [r'C:\Program Files\LibreOffice\program\soffice.exe', r'C:\Program Files (x86)\LibreOffice\program\soffice.exe']:
        if os.path.exists(p):
            return p
    return shutil.which('soffice') or shutil.which('soffice.exe')

print(json.dumps({
    'libreoffice': find_soffice(),
    'tesseract': _tess,
    'espeak_ng': _espeak,
    'jieba': bool(importlib.util.find_spec('jieba')),
    'pypinyin': bool(importlib.util.find_spec('pypinyin')),
    'xlrd': bool(importlib.util.find_spec('xlrd')),
    'fugashi': bool(importlib.util.find_spec('fugashi')),
    'spacy': bool(importlib.util.find_spec('spacy')),
    'pymorphy3': bool(importlib.util.find_spec('pymorphy3')),
    'pykakasi': bool(importlib.util.find_spec('pykakasi')),
    'winget': shutil.which('winget'),
}, ensure_ascii=False, indent=1))
