#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Language-aware lemmatization (optional providers, no data bundled)."""
import sys, os

SPACY_MODEL = {
    'it': 'it_core_news_sm',
    'en': 'en_core_web_sm',
    'de': 'de_core_news_sm',
    'fr': 'fr_core_news_sm',
    'es': 'es_core_news_sm',
}
_nlp = {}
_ru = None

def _load_spacy(lang):
    if lang in _nlp:
        return _nlp[lang]
    try:
        import spacy
        _nlp[lang] = spacy.load(SPACY_MODEL[lang])
    except Exception:
        _nlp[lang] = None
    return _nlp[lang]

def lemma(word, lang, context=None):
    word = (word or '').strip()
    if not word:
        return ''
    low = word.lower()
    if lang in ('zh', 'ja'):
        return low
    if lang == 'ru':
        global _ru
        try:
            if _ru is None:
                import pymorphy3
                _ru = pymorphy3.MorphAnalyzer()
            return _ru.parse(word)[0].normal_form.lower()
        except Exception:
            return low
    if lang in SPACY_MODEL:
        nlp = _load_spacy(lang)
        if nlp is None:
            return low
        try:
            doc = nlp(context or word)
            for t in doc:
                if t.text.lower() == low and t.lemma_:
                    return t.lemma_.lower()
            if doc and doc[0].lemma_:
                return doc[0].lemma_.lower()
        except Exception:
            pass
    return low

def available(lang):
    if lang in ('zh', 'ja'):
        return True
    if lang == 'ru':
        try:
            import pymorphy3
            return True
        except Exception:
            return False
    if lang in SPACY_MODEL:
        return _load_spacy(lang) is not None
    return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: lemmatize.py <word> --lang it [--context "..."]')
        sys.exit(2)
    lang = 'it'
    if '--lang' in sys.argv:
        lang = sys.argv[sys.argv.index('--lang') + 1]
    ctx = None
    if '--context' in sys.argv:
        ctx = sys.argv[sys.argv.index('--context') + 1]
    print(lemma(sys.argv[1], lang, ctx))
