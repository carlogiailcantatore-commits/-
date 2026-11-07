#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Multi-language phonetic transcription.

Types: ipa (espeak-ng or Wiktionary), romaji (pykakasi), pinyin (pypinyin).
No engine or data is bundled; missing engines return status=missing_engine.
"""
import sys, os, json, re, shutil, subprocess, urllib.parse, urllib.request, time

CACHE = os.path.join(os.getcwd(), '.bilingual-phonetic-cache.json')
VOICE = {'it': 'it', 'en': 'en-us', 'de': 'de', 'fr': 'fr', 'es': 'es', 'ru': 'ru', 'la': 'la'}
ESPEAK_CANDIDATES = [
    'espeak-ng.exe', 'espeak-ng', r'C:\Program Files\eSpeak NG\espeak-ng.exe',
    r'C:\Program Files (x86)\eSpeak NG\espeak-ng.exe', 'espeak'
]
_cache = None

def load_cache():
    global _cache
    if _cache is None:
        try: _cache = json.load(open(CACHE, encoding='utf-8'))
        except Exception: _cache = {}
    return _cache

def save_cache():
    try:
        json.dump(load_cache(), open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    except Exception:
        pass

def find_espeak():
    for cand in ESPEAK_CANDIDATES:
        if os.path.isabs(cand):
            if os.path.exists(cand):
                return cand
        else:
            p = shutil.which(cand)
            if p:
                return p
    return None

def espeak_ipa(word, lang):
    exe = find_espeak()
    if not exe:
        return ''
    voice = VOICE.get(lang, lang)
    try:
        r = subprocess.run([exe, '-v', voice, '-q', '--ipa=3'], input=(word + '\n'), text=True, encoding='utf-8', capture_output=True, timeout=12)
        val = (r.stdout or '').strip() if r.returncode == 0 else ''
        return val.replace('\u200d', '').replace('\u200b', '').strip()
    except Exception:
        return ''

def extract_ipa(content):
    if not content:
        return ''
    m = re.search(r'\{\{IPA\|(?:[a-z-]+\|)?([^}|]+)', content, re.I)
    if m:
        return m.group(1).strip().strip('/[]')
    pron = re.search(r'\{\{-pron-\}\}(.*?)(?:\n\{\{-|\Z)', content, re.S)
    if pron:
        m = re.search(r'/([^/\n]{2,})/', pron.group(1))
        if m:
            return m.group(1).strip()
    return ''

def wiktionary_ipa(word, lang):
    urls = {
        'it': 'https://it.wiktionary.org/w/api.php',
        'en': 'https://en.wiktionary.org/w/api.php',
        'de': 'https://de.wiktionary.org/w/api.php',
        'fr': 'https://fr.wiktionary.org/w/api.php',
        'es': 'https://es.wiktionary.org/w/api.php',
        'ru': 'https://ru.wiktionary.org/w/api.php',
        'la': 'https://la.wiktionary.org/w/api.php',
    }
    base = urls.get(lang)
    if not base:
        return ''
    key = lang + ':' + word.lower()
    cache = load_cache()
    if cache.get(key):
        return cache[key]
    url = base + '?' + urllib.parse.urlencode({'action': 'parse', 'page': word, 'prop': 'wikitext',
                                                'format': 'json', 'formatversion': '2', 'redirects': '1'})
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'bilingual-literature-skill/0.1'})
        obj = json.loads(urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='replace'))
        val = extract_ipa((obj.get('parse') or {}).get('wikitext') or '')
        if val:
            cache[key] = val
            save_cache()
        return val
    except Exception:
        return ''

def pinyin_value(word):
    try:
        from pypinyin import pinyin, Style
        return ' '.join(x[0] for x in pinyin(word, style=Style.TONE, heteronym=False))
    except Exception:
        return ''

def romaji_value(word):
    try:
        from pykakasi import kakasi
        k = kakasi()
        parts = k.convert(word)
        return ''.join(p.get('hepburn', p.get('hira', '')) for p in parts).strip()
    except Exception:
        return ''

def transcribe(word, lang='it', allow_network=True):
    word = (word or '').strip()
    if not word:
        return {'value': '', 'type': 'none', 'source': None, 'status': 'empty'}
    if lang == 'zh':
        v = pinyin_value(word)
        return {'value': v, 'type': 'pinyin', 'source': 'pypinyin', 'status': 'ok' if v else 'missing_engine'}
    if lang == 'ja':
        v = romaji_value(word)
        return {'value': v, 'type': 'romaji', 'source': 'pykakasi', 'status': 'ok' if v else 'missing_engine'}
    v = espeak_ipa(word, lang)
    if v:
        return {'value': v, 'type': 'ipa', 'source': 'espeak-ng', 'status': 'ok'}
    if allow_network:
        v = wiktionary_ipa(word, lang)
        if v:
            return {'value': v, 'type': 'ipa', 'source': 'wiktionary-' + lang, 'status': 'ok'}
    return {'value': '', 'type': 'ipa', 'source': None, 'status': 'missing_engine'}

def batch_transcribe(words, lang='it', allow_network=True):
    out = {}
    for w in dict.fromkeys((x or '').strip() for x in words):
        if not w:
            continue
        r = transcribe(w, lang, allow_network)
        out[w] = r
    return out

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: phonetic.py <word> [--lang it] [--no-network]')
        sys.exit(2)
    lang = 'it'
    if '--lang' in sys.argv:
        lang = sys.argv[sys.argv.index('--lang') + 1]
    allow = '--no-network' not in sys.argv
    print(json.dumps(transcribe(sys.argv[1], lang, allow), ensure_ascii=False))
