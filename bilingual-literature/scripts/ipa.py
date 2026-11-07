#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: GPL-3.0-or-later
"""IPA transcription helper.

Backends:
  1. espeak-ng / espeak CLI (if installed)
  2. Italian Wiktionary API fallback (optional, cached)
  3. empty string when unavailable (caller decides how to display)
"""
import sys, os, json, re, subprocess, urllib.parse, urllib.request, time

CACHE = os.path.join(os.getcwd(), '.bilingual-ipa-cache.json')
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

VOICE = {'it':'it','en':'en-us','fr':'fr','de':'de','es':'es','ru':'ru','ja':'ja','ko':'ko'}

def extract_ipa(content):
    if not content:
        return ''
    m = re.search(r'\{\{IPA\|(?:it\|)?([^}|]+)', content, re.I)
    if m:
        return m.group(1).strip().strip('/[]')
    # many Italian entries put IPA inline under {{-pron-}}, e.g. /ko.ˈmu.ne/
    pron = re.search(r'\{\{-pron-\}\}(.*?)(?:\n\{\{-|\Z)', content, re.S)
    if pron:
        m = re.search(r'/([^/\n]{2,})/', pron.group(1))
        if m:
            return m.group(1).strip()
    return ''

def espeak_ipa(word, lang):
    exe = None
    for cand in ('espeak-ng', 'espeak'):
        try:
            r = subprocess.run([cand, '--version'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                exe = cand; break
        except Exception:
            pass
    if not exe:
        return ''
    voice = VOICE.get(lang, lang)
    try:
        r = subprocess.run([exe, '-v', voice, '--ipa=3', '-q', word], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return (r.stdout or '').strip()
    except Exception:
        pass
    return ''

def wiktionary_ipa(word, lang='it'):
    if lang != 'it':
        return ''
    key = lang + ':' + word.lower()
    cache = load_cache()
    if key in cache and cache[key]:
        return cache[key]
    url = 'https://it.wiktionary.org/w/api.php?' + urllib.parse.urlencode({
        'action': 'parse', 'page': word, 'prop': 'wikitext', 'format': 'json',
        'formatversion': '2', 'redirects': '1'})
    for attempt in range(3):
        try:
            time.sleep(0.35 + attempt * 1.5)
            req = urllib.request.Request(url, headers={'User-Agent': 'bilingual-literature-skill/0.1'})
            raw = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='replace')
            obj = json.loads(raw)
            wt = (obj.get('parse') or {}).get('wikitext') or ''
            val = extract_ipa(wt)
            if val:
                cache[key] = val
                save_cache()
                return val
            return ''
        except Exception:
            continue
    return ''

def batch_transcribe(words, lang='it', allow_network=True):
    """Transcribe many words, using a single MediaWiki query per ~40 titles for Italian."""
    words = [w for w in dict.fromkeys((x or '').strip() for x in words) if w]
    if not words:
        return {}
    cache = load_cache()
    out = {}
    for w in words:
        k = lang + ':' + w.lower()
        if cache.get(k):
            out[w] = cache[k]
    todo = [w for w in words if w not in out]
    if not todo:
        return out
    # local espeak first (fast, offline)
    local = espeak_ipa(todo[0], lang)
    if local:
        for w in todo:
            out[w] = espeak_ipa(w, lang)
        return out
    if not allow_network or lang != 'it':
        return out
    for i in range(0, len(todo), 40):
        chunk = todo[i:i+40]
        titles = '|'.join(chunk)
        url = 'https://it.wiktionary.org/w/api.php?' + urllib.parse.urlencode({
            'action': 'query', 'prop': 'revisions', 'rvslots': 'main', 'rvprop': 'content',
            'format': 'json', 'formatversion': '2', 'redirects': '1', 'titles': titles})
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'bilingual-literature-skill/0.1'})
            obj = json.loads(urllib.request.urlopen(req, timeout=30).read().decode('utf-8', errors='replace'))
            pages = (obj.get('query') or {}).get('pages') or []
            for page in pages:
                title = (page.get('title') or '').lower()
                content = ''
                revs = page.get('revisions') or []
                if revs:
                    content = ((revs[0].get('slots') or {}).get('main') or {}).get('content') or ''
                val = extract_ipa(content)
                if val:
                    cache[lang + ':' + title] = val
                    for w in chunk:
                        if w.lower() == title:
                            out[w] = val
            save_cache()
        except Exception:
            pass
        time.sleep(0.3)
    return out

def transcribe(word, lang='it', allow_network=True):
    word = (word or '').strip()
    if not word:
        return ''
    val = espeak_ipa(word, lang)
    if val:
        return val
    if allow_network:
        val = wiktionary_ipa(word, lang)
        if val:
            return val
    return ''

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: ipa.py <word> [--lang it] [--no-network]')
        sys.exit(2)
    lang = 'it'
    if '--lang' in sys.argv:
        lang = sys.argv[sys.argv.index('--lang') + 1]
    allow = '--no-network' not in sys.argv
    print(transcribe(sys.argv[1], lang, allow))
