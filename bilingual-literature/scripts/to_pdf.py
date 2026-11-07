#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Convert DOCX to PDF with LibreOffice headless (never Word).
Usage: python to_pdf.py <docx> <out.pdf> [--print-install-command]
Exit codes: 0 ok; 2 LibreOffice missing.
"""
import sys, os, subprocess, shutil

CANDIDATES = [
    r'C:\Program Files\LibreOffice\program\soffice.com',
    r'C:\Program Files\LibreOffice\program\soffice.exe',
    r'C:\Program Files (x86)\LibreOffice\program\soffice.com',
    r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
    '/Applications/LibreOffice.app/Contents/MacOS/soffice',
    '/usr/bin/libreoffice',
    '/usr/bin/soffice',
]

def find_soffice():
    for p in CANDIDATES:
        if os.path.exists(p):
            return p
    return shutil.which('soffice') or shutil.which('soffice.exe')

def main():
    if len(sys.argv) < 3:
        print('usage: to_pdf.py <docx> <out.pdf>'); return 2
    src, out = sys.argv[1], sys.argv[2]
    exe = find_soffice()
    if not exe:
        print('LIBREOFFICE_MISSING')
        print('Install command (requires user authorization): winget install --id TheDocumentFoundation.LibreOffice -e')
        print('Or download from https://www.libreoffice.org/download/')
        return 2
    outdir = os.path.join(os.getcwd(), '.bilingual-lo-out')
    try: os.makedirs(outdir, exist_ok=True)
    except Exception: outdir = os.path.dirname(os.path.abspath(out)) or '.'
    profile = os.path.join(os.getcwd(), '.bilingual-lo-profile')
    tmpdir = os.path.join(os.getcwd(), '.bilingual-lo-tmp')
    try:
        os.makedirs(profile, exist_ok=True)
        os.makedirs(tmpdir, exist_ok=True)
    except Exception:
        profile = None
        tmpdir = None
    cmd = [exe, '--headless', '--norestore']
    if profile:
        uri = 'file:///' + profile.replace('\\', '/')
        cmd.append('-env:UserInstallation=' + uri)
    cmd += ['--convert-to', 'pdf', '--outdir', outdir, src]
    env = os.environ.copy()
    if tmpdir:
        env['TMP'] = tmpdir
        env['TEMP'] = tmpdir
        env['TMPDIR'] = tmpdir
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    if r.returncode != 0:
        print('PDF_CONVERT_FAILED')
        print(r.stdout); print(r.stderr)
        return 3
    expected = os.path.join(outdir, os.path.splitext(os.path.basename(src))[0] + '.pdf')
    if not os.path.exists(expected):
        print('PDF_NOT_CREATED'); return 3
    if os.path.abspath(expected) != os.path.abspath(out):
        shutil.move(expected, out)
    print('OK ' + out)
    return 0

if __name__ == '__main__':
    sys.exit(main())
