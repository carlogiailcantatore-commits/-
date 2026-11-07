#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Externalized vocabulary database for the bilingual-literature skill.

Layout (workspace-relative by default):
  vocab/vocab.db              SQLite grading datasets + glossary? (glossary separate)
  vocab/docs/<doc>.vocab.json document vocabulary (reusable asset)
  vocab/glossary.<lang>.json  term base (per language)

Commands:
  catalog
  init --lang it [--system CEFR] [--db PATH]
  status [--db PATH]
  extract --md FILE --lang it --min B1 [--system CEFR] [--out FILE] [--db PATH]
  build --words FILE --format excel|word --out FILE
  glossary add --lang it --term ... --translation ... [--domain ...]
  glossary list --lang it
"""
import sys, os, json, re, csv, io, argparse, sqlite3, datetime, urllib.request, subprocess, tempfile, hashlib, shutil, importlib.util, ipa, phonetic, lemmatize

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(BASE, 'references', 'grading-catalog.json')
CWD = os.getcwd()
DEFAULT_DB = os.path.join(CWD, 'vocab', 'vocab.db')
POINTER = os.path.join(CWD, '.bilingual-vocab.json')

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS datasets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lang TEXT NOT NULL,
  system TEXT NOT NULL,
  name TEXT,
  levels TEXT,
  sources TEXT,
  note TEXT,
  fetched_at TEXT,
  word_count INTEGER,
  UNIQUE(lang, system)
);
CREATE TABLE IF NOT EXISTS words (
  dataset_id INTEGER NOT NULL,
  word TEXT NOT NULL,
  lemma TEXT,
  level TEXT,
  pos TEXT,
  phonetic TEXT,
  notes TEXT,
  PRIMARY KEY (dataset_id, word)
);
CREATE INDEX IF NOT EXISTS idx_words_word ON words(word);
CREATE INDEX IF NOT EXISTS idx_words_lemma ON words(lemma);
"""

def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def load_catalog():
    with open(CATALOG, encoding='utf-8') as f:
        return json.load(f)

def resolve_system(cat, lang, system=None):
    if lang not in cat:
        raise SystemExit('NO_LANG: ' + lang)
    systems = cat[lang].get('systems', [])
    if not systems:
        raise SystemExit('NO_SYSTEM: ' + lang)
    if system:
        for s in systems:
            if s['id'] == system:
                return s
        raise SystemExit('NO_SYSTEM: ' + lang + '/' + system)
    if len(systems) > 1:
        raise SystemExit('SYSTEM_REQUIRED: ' + lang + ' 有多个体系：' + ', '.join(s['id'] for s in systems))
    return systems[0]

def display_system(lang, spec):
    return lang + ' / ' + (spec.get('display') or spec['id'])

def db_pointer_read():
    if os.path.exists(POINTER):
        try:
            obj = json.load(open(POINTER, encoding='utf-8'))
            if obj.get('db_path'):
                return obj['db_path']
        except Exception:
            pass
    return None

def db_pointer_write(path):
    try:
        os.makedirs(os.path.dirname(POINTER), exist_ok=True)
        json.dump({'db_path': os.path.abspath(path), 'updated_at': now()}, open(POINTER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    except Exception as e:
        print('WARN_POINTER_WRITE_FAILED: ' + str(e))

def resolve_db(args, require_confirm=False):
    p = getattr(args, 'db', None)
    if p:
        return os.path.abspath(p)
    envp = os.environ.get('BILINGUAL_VOCAB_DB')
    if envp:
        return os.path.abspath(envp)
    ptr = db_pointer_read()
    if ptr:
        return os.path.abspath(ptr)
    if require_confirm:
        print('DB_PATH_CONFIRM_REQUIRED')
        print('DEFAULT_DB=' + DEFAULT_DB)
        print('请确认默认路径，或用 --db 指定另一个路径后重跑 init。')
        raise SystemExit(4)
    return os.path.abspath(DEFAULT_DB)

def connect_db(path, create=False):
    if not os.path.exists(path) and not create:
        return None
    if create:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    con = sqlite3.connect(path)
    con.execute('PRAGMA journal_mode=WAL')
    con.executescript(SCHEMA)
    cols = [r[1] for r in con.execute('PRAGMA table_info(words)').fetchall()]
    if 'phonetic' not in cols:
        con.execute('ALTER TABLE words ADD COLUMN phonetic TEXT')
        con.commit()
    return con

def fetch_source(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'bilingual-literature'})
    try:
        return urllib.request.urlopen(req, timeout=90).read()
    except Exception:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.bin')
        tmp.close()
        try:
            curl = shutil.which('curl') or ('curl.exe' if os.name == 'nt' else 'curl')
            r = subprocess.run([curl, '-L', '--max-time', '180', '-sS', '-o', tmp.name, url], capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError('curl failed: ' + (r.stderr or '')[:200])
            with open(tmp.name, 'rb') as f:
                return f.read()
        finally:
            try: os.unlink(tmp.name)
            except Exception: pass

def parse_csv_levels(text, word_col, level_col):
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        w = (row.get(word_col) or '').strip()
        lv = (row.get(level_col) or '').strip()
        if w and lv:
            out[w.lower()] = lv
    return out

def parse_tsv_levels(text, word_col, level_col):
    out = {}
    for row in csv.DictReader(io.StringIO(text), delimiter='\t'):
        w = (row.get(word_col) or '').strip()
        lv = (row.get(level_col) or '').strip()
        if w and lv:
            out[w.lower()] = lv
    return out

def collect_words(lang, system_id, spec, refresh=False):
    levels = spec.get('levels') or ['A1','A2','B1','B2','C1','C2']
    merged = {}
    def add(word, lv):
        word = word.strip().lower()
        if not word:
            return
        if word not in merged:
            merged[word] = lv
        else:
            try:
                if levels.index(lv) < levels.index(merged[word]):
                    merged[word] = lv
            except ValueError:
                pass
    sources = spec.get('sources') or []
    if not sources:
        msg = 'NO_SOURCE: ' + lang + '/' + system_id
        ptr = spec.get('pointers') or []
        if ptr:
            msg += '；指路：' + ' ; '.join(ptr)
        raise SystemExit(msg + '；请补 catalog 或提供本地词表')
    for src in sources:
        rawb = fetch_source(src['url'])
        parser = src.get('parser')
        fmt = src.get('format', 'csv')
        raw = rawb.decode('utf-8', errors='replace')
        if parser:
            import parsers
            try:
                part = parsers.parse_source(parser, rawb, src)
            except Exception as e:
                raise SystemExit('SOURCE_PARSE_FAILED: ' + parser + ' ' + src.get('url', '') + ' :: ' + str(e))
        elif fmt == 'csv':
            part = parse_csv_levels(raw, src.get('word_column', 'headword'), src.get('level_column', 'CEFR'))
        elif fmt == 'tsv':
            part = parse_tsv_levels(raw, src.get('word_column', 'word'), src.get('level_column', 'level'))
        elif fmt == 'json':
            part = {}
            obj = json.loads(raw)
            if isinstance(obj, list):
                for it in obj:
                    w = it.get(src.get('word_column', 'word')); lv = it.get(src.get('level_column', 'level'))
                    if w and lv:
                        part[str(w).lower()] = str(lv)
        else:
            raise SystemExit('SOURCE_NEEDS_PARSER: ' + fmt + ' ' + src.get('url', ''))
        for w, lv in part.items():
            add(w, lv)
    return merged

def phonetic_for(lang, word):
    if lang == 'zh':
        try:
            from pypinyin import pinyin, Style
            return ' '.join(x[0] for x in pinyin(word, style=Style.TONE, heteronym=False))
        except Exception:
            return ''
    return ''

def save_dataset(con, lang, spec, words):
    levels = spec.get('levels') or ['A1','A2','B1','B2','C1','C2']
    cur = con.execute('SELECT id FROM datasets WHERE lang=? AND system=?', (lang, spec['id']))
    row = cur.fetchone()
    sources_json = json.dumps([s.get('url') for s in (spec.get('sources') or [])], ensure_ascii=False)
    if row:
        did = row[0]
        con.execute('UPDATE datasets SET name=?, levels=?, sources=?, note=?, fetched_at=?, word_count=? WHERE id=?',
                    (spec.get('name',''), json.dumps(levels), sources_json, spec.get('note',''), now(), len(words), did))
        con.execute('DELETE FROM words WHERE dataset_id=?', (did,))
    else:
        cur = con.execute('INSERT INTO datasets(lang,system,name,levels,sources,note,fetched_at,word_count) VALUES(?,?,?,?,?,?,?,?)',
                          (lang, spec['id'], spec.get('name',''), json.dumps(levels), sources_json, spec.get('note',''), now(), len(words)))
        did = cur.lastrowid
    con.executemany('INSERT OR IGNORE INTO words(dataset_id,word,lemma,level,phonetic) VALUES(?,?,?,?,?)',
                    [(did, w, w, lv, phonetic_for(lang, w)) for w, lv in words.items()])
    con.commit()
    return did

def load_language_packs():
    for rel in ('data/language-packs.json', 'references/language-packs.json'):
        p = os.path.join(BASE, rel)
        if os.path.exists(p):
            try: return json.load(open(p, encoding='utf-8'))
            except Exception: return {}
    return {}

def provider_available(p):
    if not p:
        return False
    typ = p.get('type')
    if typ == 'builtin':
        return True
    if typ == 'cli':
        probe = p.get('probe') or []
        if probe and probe[0] in ('espeak-ng', 'espeak'):
            try: return bool(phonetic.find_espeak())
            except Exception: return False
        return bool(probe and shutil.which(probe[0]))
    if typ == 'python':
        probe = p.get('probe') or ''
        if 'spacy.load' in probe:
            mm = re.search(r'spacy\.load\("([^"]+)"\)', probe)
            if mm:
                try:
                    import spacy
                    spacy.load(mm.group(1))
                    return True
                except Exception:
                    return False
        m = re.search(r'import\s+([A-Za-z0-9_\.]+)', probe)
        if m:
            try: return importlib.util.find_spec(m.group(1).split('.')[0]) is not None
            except Exception: return False
        return False
    if typ == 'online':
        return True
    return False

def precheck_lang(lang, system=None, dbp=None, skip_grading=False):
    packs = load_language_packs()
    src = (packs.get('sources') or {}).get(lang)
    missing = []
    if not src:
        return {'ok': False, 'lang': lang, 'missing': [{'capability': 'language_pack', 'provider': None, 'install': None}]}
    prov = packs.get('providers') or {}
    for cap in ('tokenizer', 'lemmatizer', 'phonetic'):
        spec = src.get(cap) or {}
        if not spec.get('required'):
            continue
        names = spec.get('providers') or []
        if not any(provider_available(prov.get(n, {})) for n in names):
            missing.append({'capability': cap, 'providers': names,
                            'install': [prov.get(n, {}).get('install') for n in names]})
    grading = src.get('grading') or {}
    if grading.get('required') and not skip_grading:
        db = dbp or resolve_db(argparse.Namespace(db=None))
        found = False
        if os.path.exists(db):
            try:
                con = connect_db(db)
                row = con.execute('SELECT 1 FROM datasets WHERE lang=? AND system=?', (lang, grading.get('system'))).fetchone()
                con.close()
                found = bool(row)
            except Exception:
                found = False
        if not found:
            missing.append({'capability': 'grading', 'system': grading.get('system'), 'install': None})
    return {'ok': not missing, 'lang': lang, 'system': (system or grading.get('system')), 'missing': missing}

def cmd_precheck(args):
    dbp = resolve_db(args)
    out = precheck_lang(args.lang, args.system, dbp)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out.get('ok') else 5

def cmd_catalog(args):
    cat = load_catalog()
    dbp = resolve_db(args)
    con = connect_db(dbp) if os.path.exists(dbp) else None
    rows = []
    for lang, info in cat.items():
        systems = info.get('systems', [])
        for idx, s in enumerate(systems):
            initialized = False
            count = 0
            if con is not None:
                r = con.execute('SELECT word_count FROM datasets WHERE lang=? AND system=?', (lang, s['id'])).fetchone()
                if r:
                    initialized = True; count = r[0]
            rows.append({
                'lang': lang, 'language': info.get('name'), 'system': s['id'],
                'name': s.get('name',''), 'display': s.get('display') or s['id'], 'levels': s.get('levels', []),
                'current': idx == 0, 'initialized': initialized, 'words': count,
                'note': s.get('note','')
            })
    if con is not None:
        con.close()
    print(json.dumps({'db': dbp, 'systems': rows}, ensure_ascii=False, indent=1))

def cmd_init(args):
    cat = load_catalog()
    spec = resolve_system(cat, args.lang, args.system)
    dbp = resolve_db(args, require_confirm=True)
    print('语言: ' + cat[args.lang].get('name', args.lang) + ' | 体系: ' + spec['id'] + ' | DB: ' + dbp)
    print('源: ' + ', '.join(s.get('url','') for s in (spec.get('sources') or [])))
    print('等级: ' + ', '.join(spec.get('levels') or []))
    print('抓取解析中...')
    words = collect_words(args.lang, spec['id'], spec)
    con = connect_db(dbp, create=True)
    save_dataset(con, args.lang, spec, words)
    con.close()
    db_pointer_write(dbp)
    from collections import Counter
    cnt = Counter(words.values())
    print('INIT_OK')
    print('词数: ' + str(len(words)))
    print('分布: ' + ', '.join(k + '=' + str(cnt.get(k,0)) for k in (spec.get('levels') or [])))
    print('DB_PATH=' + dbp)

def cmd_status(args):
    dbp = resolve_db(args)
    if not os.path.exists(dbp):
        print(json.dumps({'db': dbp, 'initialized': False}, ensure_ascii=False, indent=1))
        return
    con = connect_db(dbp)
    rows = con.execute('SELECT lang, system, name, levels, fetched_at, word_count, note FROM datasets ORDER BY lang, system').fetchall()
    con.close()
    out = [{'lang': r[0], 'system': r[1], 'name': r[2], 'levels': json.loads(r[3]) if r[3] else [], 'fetched_at': r[4], 'words': r[5], 'note': r[6]} for r in rows]
    print(json.dumps({'db': dbp, 'datasets': out}, ensure_ascii=False, indent=1))

FENCE = chr(96) * 3
ELIDED = set(['l','lo','la','i','gli','le','un','uno','una','d','di','del','della','dei','degli','delle','dell','all','alla','allo','agli','alle','nell','nella','nello','negli','nelle','sull','sulla','sullo','sugli','sulle','dall','dalla','dallo','dagli','dalle','coll','colla','collo','cogli','colle','quest','questa','questo','questi','queste','c','ci','ne','gl','mi','ti','si','vi','dov','com','quand','tutt','sant','mezz','anch'])

def tokenize(text, lang):
    if lang == 'ja':
        try:
            import fugashi
            tagger = fugashi.Tagger()
            out = []
            for t in tagger(text):
                surface = (t.surface or '').strip()
                if not surface or not re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', surface):
                    continue
                lemma = getattr(getattr(t, 'feature', None), 'lemma', None) or surface
                out.append((surface, lemma, ''))
            if out:
                return out
        except Exception:
            pass
    if lang == 'zh':
        try:
            import jieba
            toks = [t.strip() for t in jieba.cut(text) if t.strip()]
            return [(t, t, '') for t in toks if re.search(r'[\u4e00-\u9fff]', t)]
        except Exception:
            pass
    toks = re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)*", text, re.UNICODE)
    out = []
    for t in toks:
        t = t.strip()
        if not t:
            continue
        lemma = t.lower(); note = ''
        if lang == 'it' and ('\u2019' in t or "'" in t):
            parts = re.split(r"['\u2019]", t)
            if len(parts) >= 2 and parts[0].lower() in ELIDED:
                lemma = parts[-1].lower()
                note = '省音/缩合（' + parts[0] + '\u2019）'
        if lang not in ('zh', 'ja'):
            lemma = lemmatize.lemma(lemma, lang, text)
        out.append((t, lemma, note))
    return out

def parse_blm(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    i = 0
    if lines and lines[0].strip() == '---':
        i = 1
        while i < len(lines) and lines[i].strip() != '---':
            i += 1
        i += 1
    blocks = []; in_code = False; skip = False
    for line in lines[i:]:
        s = line.strip()
        if s.startswith(FENCE):
            in_code = not in_code
            continue
        if in_code:
            continue
        if re.match(r'^#{1,5}\s+', s):
            head = re.sub(r'^#{1,5}\s+', '', s)
            if re.search(r'Riferimenti|参考文献|Link utili|注释|附录', head):
                skip = True
            blocks.append(('heading', head))
            continue
        if skip:
            continue
        if not s or s.startswith('>') or s.startswith('![') or s.startswith('**') or s.startswith('<'):
            continue
        blocks.append(('text', s))
    return blocks

def extract_all_words(md, lang):
    entries = {}
    for kind, text in parse_blm(md):
        if kind != 'text':
            continue
        for surface, lemma, note in tokenize(text, lang):
            key = (lemma or surface).lower()
            e = entries.setdefault(key, {'lemma': lemma or surface, 'forms': {}, 'notes': set()})
            e['forms'][surface] = e['forms'].get(surface, 0) + 1
            if note:
                e['notes'].add(note)
    out = []
    for key, e in entries.items():
        forms = sorted(e['forms'].items(), key=lambda x: (-x[1], x[0]))
        notes = list(e['notes'])
        if len(forms) > 1:
            notes.append('文中形式：' + '、'.join(f for f, _ in forms))
        out.append({'original': forms[0][0], 'phonetic': '', 'ipa': '', 'ipa_lemma': '',
                    'inflection': '；'.join(notes), 'lemma': e['lemma'], 'level': 'ALL', 'translation': ''})
    if out:
        pmap = phonetic.batch_transcribe([x['original'] for x in out], lang)
        for x in out:
            r = pmap.get(x['original']) or pmap.get(x['original'].lower()) or {}
            if not r.get('value'):
                r = pmap.get(x['lemma']) or pmap.get(x['lemma'].lower()) or r
            x['phonetic'] = r.get('value') or ''
            x['phonetic_type'] = r.get('type') or 'none'
            x['phonetic_source'] = r.get('source')
            x['phonetic_status'] = r.get('status') or 'missing'
            if x['phonetic_type'] == 'ipa':
                x['ipa'] = x['phonetic']
                x['ipa_lemma'] = x['phonetic']
    out.sort(key=lambda x: x['original'].lower())
    return out

def cmd_extract(args):
    target_lang = getattr(args, 'target', None) or ('it' if args.lang == 'zh' else 'zh')
    if target_lang not in ('zh', 'it') or target_lang == args.lang:
        print('PAIR_INVALID: %s -> %s' % (args.lang, target_lang))
        raise SystemExit(2)
    all_mode = bool(getattr(args, 'all', False) or args.lang == 'la')
    if all_mode:
        if not getattr(args, 'skip_precheck', False):
            pc = precheck_lang(args.lang, None, None, skip_grading=True)
            if not pc.get('ok'):
                print('VOCAB_PRECHECK_FAILED')
                print(json.dumps(pc, ensure_ascii=False, indent=1))
                raise SystemExit(5)
        out = extract_all_words(args.md, args.lang)
        outpath = args.out or os.path.join(CWD, 'vocab', 'docs', os.path.splitext(os.path.basename(args.md))[0] + '.vocab.json')
        os.makedirs(os.path.dirname(os.path.abspath(outpath)), exist_ok=True)
        json.dump({'doc': os.path.basename(args.md), 'lang': args.lang, 'target_lang': target_lang,
                   'system': 'ALL', 'min': 'ALL', 'all': True, 'entries': out},
                  open(outpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('ALL_WORDS lang=' + args.lang + ' target=' + target_lang + ' entries=' + str(len(out)))
        print('OK ' + outpath)
        return
    if not args.min:
        print('BAD_LEVEL: --min required for graded languages')
        raise SystemExit(2)
    cat = load_catalog()
    spec = resolve_system(cat, args.lang, args.system)
    levels = spec.get('levels') or ['A1','A2','B1','B2','C1','C2']
    if args.min not in levels:
        raise SystemExit('BAD_LEVEL: ' + args.min)
    dbp = resolve_db(args)
    if not getattr(args, 'skip_precheck', False):
        pc = precheck_lang(args.lang, spec['id'], dbp)
        if not pc.get('ok'):
            print('VOCAB_PRECHECK_FAILED')
            print(json.dumps(pc, ensure_ascii=False, indent=1))
            raise SystemExit(5)
    if not os.path.exists(dbp):
        print('DATASET_NOT_INITIALIZED: DB 不存在 ' + dbp)
        print('先运行: vocab.py init --lang ' + args.lang + ' --system ' + spec['id'] + ' --db <path>')
        raise SystemExit(3)
    con = connect_db(dbp)
    r = con.execute('SELECT id FROM datasets WHERE lang=? AND system=?', (args.lang, spec['id'])).fetchone()
    if not r:
        con.close()
        print('DATASET_NOT_INITIALIZED: ' + args.lang + '/' + spec['id'] + ' 未初始化')
        print('先运行: vocab.py init --lang ' + args.lang + ' --system ' + spec['id'] + ' --db ' + dbp)
        raise SystemExit(3)
    did = r[0]
    table = {w: (lv, lemma, phon) for w, lv, lemma, phon in con.execute('SELECT word, level, lemma, phonetic FROM words WHERE dataset_id=?', (did,))}
    con.close()
    minidx = levels.index(args.min)
    entries = {}
    for kind, text in parse_blm(args.md):
        if kind != 'text':
            continue
        for surface, lemma, note in tokenize(text, args.lang):
            key = lemma
            e = entries.setdefault(key, {'lemma': lemma, 'forms': {}, 'level': None, 'notes': set(), 'phonetic': ''})
            e['forms'][surface] = e['forms'].get(surface, 0) + 1
            if note:
                e['notes'].add(note)
            hit = table.get(lemma) or table.get(surface.lower())
            if hit and not e['level']:
                e['level'] = hit[0]
                e['phonetic'] = hit[2] if len(hit) > 2 else ''
    out = []
    for key, e in entries.items():
        lv = e['level']
        if not lv or lv not in levels or levels.index(lv) < minidx:
            continue
        forms = sorted(e['forms'].items(), key=lambda x: (-x[1], x[0]))
        notes = list(e['notes'])
        if len(forms) > 1:
            notes.append('文中形式：' + '、'.join(f for f, _ in forms))
        out.append({'original': forms[0][0], 'phonetic': e.get('phonetic') or '', 'ipa': '', 'ipa_lemma': '', 'inflection': '；'.join(notes), 'lemma': e['lemma'], 'level': lv, 'translation': ''})
    if out and args.lang == 'zh':
        for x in out:
            x['phonetic_type'] = 'pinyin'
            x['phonetic_source'] = 'HSK/pypinyin'
            x['phonetic_status'] = 'ok' if x.get('phonetic') else 'missing'
    elif not getattr(args, 'no_ipa', False) and out:
        words = []
        for x in out:
            words.append(x['original'])
            words.append(x['lemma'])
        pmap = phonetic.batch_transcribe(words, args.lang)
        for x in out:
            r = pmap.get(x['original']) or pmap.get(x['original'].lower()) or {}
            if not r.get('value'):
                r = pmap.get(x['lemma']) or pmap.get(x['lemma'].lower()) or r
            x['phonetic'] = r.get('value') or ''
            x['phonetic_type'] = r.get('type') or 'none'
            x['phonetic_source'] = r.get('source')
            x['phonetic_status'] = r.get('status') or 'missing'
            if x['phonetic_type'] == 'ipa':
                x['ipa'] = x['phonetic']
                x['ipa_lemma'] = x['phonetic']
    out.sort(key=lambda x: (levels.index(x['level']), x['lemma']))
    ipa_missing = sum(1 for x in out if x.get('phonetic_status') not in (None, 'ok') or not x.get('phonetic'))
    print('使用体系：' + display_system(args.lang, spec) + '    门槛：' + args.min + '及以上')
    if ipa_missing and args.lang != 'zh':
        print('PHONETIC_MISSING %d/%d（检查 espeak-ng / pykakasi / pypinyin）' % (ipa_missing, len(out)))
    print('按当前体系过滤；要换体系请指定体系名称或询问我可用体系')
    outpath = args.out or os.path.join(CWD, 'vocab', 'docs', os.path.splitext(os.path.basename(args.md))[0] + '.vocab.json')
    os.makedirs(os.path.dirname(os.path.abspath(outpath)), exist_ok=True)
    json.dump({'doc': os.path.basename(args.md), 'lang': args.lang, 'target_lang': target_lang, 'system': spec['id'], 'min': args.min, 'entries': out},
              open(outpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('OK ' + outpath + ' entries=' + str(len(out)))

def cmd_fill(args):
    data = json.load(open(args.words, encoding='utf-8'))
    entries = data.get('entries', data)
    tr = json.load(open(args.translations, encoding='utf-8'))
    miss = 0
    for e in entries:
        key = e.get('lemma') or e.get('original') or ''
        val = tr.get(key) or tr.get((e.get('original') or '')) or tr.get(key.lower())
        if val:
            e['translation'] = val
        elif not e.get('translation'):
            miss += 1
    out = args.out or args.words
    json.dump(data, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('OK ' + out + ' entries=' + str(len(entries)) + ' missing_translation=' + str(miss))
    return 0

def cmd_build(args):
    data = json.load(open(args.words, encoding='utf-8'))
    entries = data.get('entries', data)
    lang = data.get('lang') or 'it'
    target = data.get('target_lang') or ('it' if lang == 'zh' else 'zh')
    base_pt = float(data.get('base_pt') or 11)
    phon_label = {'zh': '拼音', 'ja': '罗马字'}.get(lang, 'IPA')
    source_font = {'zh': 'SimSun', 'ja': 'Yu Mincho'}.get(lang, 'Times New Roman')
    target_font = 'KaiTi' if target == 'zh' else 'Times New Roman'
    if args.format == 'excel':
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = 'Vocabulary'
        use_inf = lang not in ('zh', 'ja') and any(e.get('inflection') for e in entries)
        use_lemma = lang not in ('zh', 'ja') and any((e.get('lemma') or '').lower() != (e.get('original') or '').lower() for e in entries)
        headers = ['原文', phon_label]
        if use_inf: headers.append('变位说明')
        if use_lemma: headers.append('原型')
        headers.append('译文')
        ws.append(headers)
        for e in entries:
            o = e.get('original',''); ph = e.get('phonetic') or e.get('ipa') or ''
            inf = e.get('inflection',''); lem = e.get('lemma','')
            row = [o, ph]
            if use_inf: row.append(inf)
            if use_lemma: row.append(lem if lem.lower() != o.lower() else '')
            row.append(e.get('translation',''))
            ws.append(row)
        for i, h in enumerate(headers, 1):
            width = max([len(str(h))] + [len(str(r[i-1])) for r in ws.iter_rows(min_row=2, values_only=True)]) if ws.max_row > 1 else len(h)
            ws.column_dimensions[chr(64+i)].width = min(40, max(10, width + 2))
        wb.save(args.out)
    else:
        from docx import Document
        from docx.shared import Pt
        doc = Document()
        for e in entries:
            o = e.get('original','')
            ph = e.get('phonetic') or e.get('ipa') or ''
            inf = e.get('inflection','')
            lem = e.get('lemma','')
            tr = e.get('translation','')
            parts = [o]
            if ph: parts.append(ph)
            if lang not in ('zh', 'ja'):
                if inf: parts.append('（' + inf + '）')
                if lem and lem.lower() != o.lower(): parts.append(lem)
            head = '/'.join(parts)
            p = doc.add_paragraph()
            r = p.add_run(head); r.bold = True; r.font.size = Pt(base_pt); r.font.name = source_font
            p2 = doc.add_paragraph()
            r2 = p2.add_run(tr or '（待译）'); r2.font.size = Pt(base_pt); r2.font.name = target_font
            doc.add_paragraph('')
        doc.save(args.out)
    print('OK ' + args.out)

def glossary_path(lang):
    return os.path.join(CWD, 'vocab', 'glossary.' + lang + '.json')

def cmd_glossary(args):
    p = glossary_path(args.lang)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    data = []
    if os.path.exists(p):
        try: data = json.load(open(p, encoding='utf-8'))
        except Exception: data = []
    if args.gcmd == 'add':
        data.append({'term': args.term, 'translation': args.translation, 'domain': args.domain or '', 'notes': args.notes or '', 'created_at': now()})
        json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('OK ' + p)
    else:
        print(json.dumps(data, ensure_ascii=False, indent=1))

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd')
    c = sub.add_parser('catalog'); c.add_argument('--db')
    i = sub.add_parser('init'); i.add_argument('--lang', required=True); i.add_argument('--system'); i.add_argument('--db')
    s = sub.add_parser('status'); s.add_argument('--db')
    p = sub.add_parser('precheck'); p.add_argument('--lang', required=True); p.add_argument('--system'); p.add_argument('--db')
    e = sub.add_parser('extract'); e.add_argument('--md', required=True); e.add_argument('--lang', required=True); e.add_argument('--system')
    e.add_argument('--min'); e.add_argument('--all', action='store_true'); e.add_argument('--out'); e.add_argument('--db'); e.add_argument('--target'); e.add_argument('--no-ipa', action='store_true'); e.add_argument('--skip-precheck', action='store_true')
    f = sub.add_parser('fill'); f.add_argument('--words', required=True); f.add_argument('--translations', required=True); f.add_argument('--out')
    b = sub.add_parser('build'); b.add_argument('--words', required=True); b.add_argument('--format', choices=['excel','word'], default='excel'); b.add_argument('--out', required=True)
    g = sub.add_parser('glossary'); g.add_argument('gcmd', choices=['add','list']); g.add_argument('--lang', required=True)
    g.add_argument('--term'); g.add_argument('--translation'); g.add_argument('--domain'); g.add_argument('--notes')
    args = ap.parse_args()
    if args.cmd == 'catalog': cmd_catalog(args)
    elif args.cmd == 'init': cmd_init(args)
    elif args.cmd == 'status': cmd_status(args)
    elif args.cmd == 'precheck': return cmd_precheck(args)
    elif args.cmd == 'extract': cmd_extract(args)
    elif args.cmd == 'fill': cmd_fill(args)
    elif args.cmd == 'build': cmd_build(args)
    elif args.cmd == 'glossary': cmd_glossary(args)
    else: ap.print_help()

if __name__ == '__main__':
    main()
