#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Single-entry launcher for the bilingual-literature skill."""
import os, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'scripts')
MAP = {
    'extract': 'extract.py',
    'split-units': 'split_units.py',
    'outline': 'outline.py',
    'worklist': 'worklist.py',
    'translate': 'translate.py',
    'build-blm': 'build_blm.py',
    'verify-md': 'verify_md.py',
    'widths': 'widths.py',
    'ipa': 'ipa.py',
    'phonetic': 'phonetic.py',
    'lemmatize': 'lemmatize.py',
    'build-docx': 'build_docx.py',
    'build-txt': 'build_txt.py',
    'to-pdf': 'to_pdf.py',
    'verify': 'verify.py',
    'check-tools': 'check_tools.py',
    'ocr-pdf': 'ocr_pdf.py',
    'vocab': 'vocab.py',
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print('usage: run.py <command> [args...]')
        print('commands: ' + ', '.join(MAP))
        return 0
    cmd = sys.argv[1]
    script = MAP.get(cmd)
    if not script:
        print('UNKNOWN_COMMAND: ' + cmd)
        return 2
    path = os.path.join(SCRIPTS, script)
    args = [sys.executable, path] + sys.argv[2:]
    return subprocess.call(args)

if __name__ == '__main__':
    sys.exit(main())
