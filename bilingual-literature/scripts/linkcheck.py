#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 贾国放 (Jia Guofang)
# SPDX-License-Identifier: Unlicense
"""链接硬约束检查（P2）：数量上限、去重、纯年份不挂、URL 合法。

用法：
  python linkcheck.py <bilingual.md> [--max 15] [--json report.json]
退出码：0 通过；1 有错误；2 参数错误。

规则（对应测试反馈“链接泛滥/年份也挂”）：
  - 全篇链接数 <= --max（默认 15，0 表示不限）；
  - 同一 URL 不得重复；同一 anchor+URL 不得重复；
  - anchor 是纯年份（1900 / 1900s / 1990-1995）→ 错误：年份不挂链接；
  - URL 必须是 http(s)，且不能是空串；
  - 输出按“错误 / 警告”分级，警告不影响退出码。
"""
import argparse
import json
import re
import sys

LINK_RE = re.compile(r'\[([^\]]*)\]\(([^)\s]+)\)')
YEAR_RE = re.compile(r'^[*_]*\s*(?:\d{4}|\d{4}s|\d{4}\s*[-–]\s*\d{4})\s*[*_]*$')


def check_links(text, max_links=15):
    errors, warnings = [], []
    links = LINK_RE.findall(text)
    seen_url, seen_pair = {}, {}
    for anchor, url in links:
        a = (anchor or '').strip()
        u = (url or '').strip()
        if not u:
            errors.append({'code': 'EMPTY_URL', 'anchor': a})
            continue
        if not re.match(r'^https?://', u, re.I):
            errors.append({'code': 'BAD_SCHEME', 'anchor': a, 'url': u[:80]})
        if YEAR_RE.match(a):
            errors.append({'code': 'YEAR_LINK', 'anchor': a, 'url': u[:80]})
        if u in seen_url:
            errors.append({'code': 'DUP_URL', 'url': u[:80], 'anchor': a})
        else:
            seen_url[u] = a
        key = (a, u)
        if key in seen_pair:
            errors.append({'code': 'DUP_PAIR', 'anchor': a, 'url': u[:80]})
        else:
            seen_pair[key] = 1
    if max_links and len(links) > max_links:
        errors.append({'code': 'TOO_MANY_LINKS', 'count': len(links), 'max': max_links})
    if len(links) > max_links * 0.8 and max_links:
        warnings.append({'code': 'NEAR_LINK_LIMIT', 'count': len(links), 'max': max_links})
    # 裸年份成链接文字但未写成 markdown 链接的情况无法判断，跳过
    return {'ok': not errors, 'total': len(links), 'errors': errors, 'warnings': warnings}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('md')
    ap.add_argument('--max', type=int, default=15)
    ap.add_argument('--json')
    a = ap.parse_args()
    try:
        text = open(a.md, encoding='utf-8').read()
    except OSError as e:
        print('READ_FAIL', e)
        return 2
    rep = check_links(text, a.max)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    if a.json:
        json.dump(rep, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return 0 if rep['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
