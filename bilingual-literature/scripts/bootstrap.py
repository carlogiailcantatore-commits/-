#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""Create a local venv and install skill dependencies (cross-platform)."""
import os, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = os.environ.get('BILINGUAL_VENV') or os.path.join(os.getcwd(), '.bilingual-venv')
PY = os.path.join(VENV, 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join(VENV, 'bin', 'python')

def run(args):
    subprocess.check_call(args)

if not os.path.exists(PY):
    run([sys.executable, '-m', 'venv', VENV])
run([PY, '-m', 'pip', 'install', '--upgrade', 'pip'])
run([PY, '-m', 'pip', 'install', 'python-docx', 'lxml', 'PyMuPDF', 'openpyxl'])
print('VENV ' + PY)
