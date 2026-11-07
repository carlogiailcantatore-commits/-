#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: GPL-3.0-or-later
"""OCR a scanned PDF into text (one block per page).
Usage: python ocr_pdf.py <input.pdf> <out.txt> [--lang ita+eng]
Exit codes: 0 ok; 3 OCR tool missing; 2 usage.
"""
import sys, os, subprocess, shutil, tempfile

def find_tesseract():
    for c in ('tesseract', r'C:\Program Files\Tesseract-OCR\tesseract.exe', r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
        if os.path.isabs(c):
            if os.path.exists(c): return c
        else:
            p = shutil.which(c)
            if p: return p
    return None

def tess_env():
    env = os.environ.copy()
    td = os.path.join(os.getcwd(), 'tessdata')
    if os.path.isdir(td):
        env['TESSDATA_PREFIX'] = td
    return env

def main():
    if len(sys.argv) < 3:
        print('usage: ocr_pdf.py <input.pdf> <out.txt> [--lang ita+eng]'); return 2
    src, out = sys.argv[1], sys.argv[2]
    lang = 'ita+eng'
    if '--lang' in sys.argv:
        lang = sys.argv[sys.argv.index('--lang') + 1]
    tess = find_tesseract()
    if not tess:
        print('OCR_MISSING: tesseract 不可用；先询问用户是否授权安装（scripts/install_tools.ps1 -Tool tesseract -Authorized）或换文件格式')
        return 3
    try:
        import fitz
    except Exception as e:
        print('PYMUPDF_MISSING: ' + str(e)); return 3
    doc = fitz.open(src)
    chunks = []
    with tempfile.TemporaryDirectory() as td:
        for i in range(doc.page_count):
            pix = doc[i].get_pixmap(dpi=200)
            png = os.path.join(td, 'p%04d.png' % (i + 1))
            pix.save(png)
            r = subprocess.run([tess, png, 'stdout', '-l', lang], capture_output=True, text=True, env=tess_env())
            chunks.append('===== PAGE %d =====\n%s' % (i + 1, r.stdout.strip()))
    doc.close()
    open(out, 'w', encoding='utf-8').write('\n\n'.join(chunks) + '\n')
    print('OK ' + out)
    return 0

if __name__ == '__main__':
    sys.exit(main())
