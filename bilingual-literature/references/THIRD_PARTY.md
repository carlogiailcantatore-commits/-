## Third-party data and links / 第三方数据与链接

This repository does not bundle third-party datasets, models, fonts, engines, or services. URLs and install commands are provided only as pointers for users to obtain those resources under their own terms. The GPL license applies only to this repository's code and documentation; it does not grant any rights to third-party data, services, or content. Links are not endorsements or authorization to redistribute, and users are responsible for complying with the applicable source terms and local law.

本仓库不打包第三方数据集、模型、字体、引擎或服务；URL 与安装命令仅作获取入口，第三方资源仍受其自身条款约束。GPL 许可仅覆盖本仓库的代码与文档，不授予任何第三方数据、服务或内容的权利。链接不构成授权、背书或再分发许可；使用者应自行遵守来源条款与当地法律。

# Third-Party Data Sources and Notices

This project code is licensed under GNU GPL v3.0 or later (see LICENSE). It does NOT bundle third-party
vocabulary datasets; the init command fetches them at runtime from the URLs below.
You are responsible for complying with each source terms.

| Language / system | Source | Terms / notes |
|---|---|---|
| English CEFR-J | https://github.com/openlanguageprofiles/olp-en-cefrj | CEFR-J Vocabulary Profile, CC BY-SA 4.0; cite Tono Laboratory / CEFR-J. |
| Japanese JLPT | https://github.com/evanclan/OpenJLPT | Community-compiled JLPT lists; check repository license before redistribution. |
| Korean TOPIK | https://github.com/julienshim/combined_korean_vocabulary_list | Combined National Institute of Korean Language + TOPIK list; check repository terms. |
| French CEFR | https://github.com/hyunahparc/bienvenue-au-croissant | No license file found at packaging time; runtime fetch only, do not redistribute the data. |
| German Goethe | https://www.goethe.de/ | Official Goethe-Institut Wortlisten A1/A2/B1 PDFs; Goethe terms apply. |
| Italian CEFR | https://www.unistrapg.it/ and Wayback snapshots | Profilo della lingua italiana, Universita per Stranieri di Perugia; rights to the original publisher. |
| Spanish PCIC | https://cvc.cervantes.es/ | Plan Curricular del Instituto Cervantes; Instituto Cervantes terms apply. |
| Russian TORFL | https://veebiarhiiv.digar.ee/ and zlat.spb.ru | TRKI lexical minimum PDF; publisher/archive terms apply; scanned source may require OCR. |
| Chinese HSK 2.0 | https://www.chinesetest.cn/userfiles/file/HSK/HSK-2012.xls | Official HSK 2.0 syllabus; runtime fetch or user-provided; do not redistribute the XLS/TSV. |

The grading-catalog.json only contains URLs and parsing hints, not the datasets
themselves. Do not commit downloaded vocabulary files, caches, or generated
databases to a public repository.

## External data / service pointers

| Project / service | Used for | Notes |
|---|---|---|
| CEFR-J / openlanguageprofiles | English CEFR-J | CC BY-SA 4.0; cite Tono Laboratory / CEFR-J. |
| OpenJLPT / evanclan | Japanese JLPT | Community list; check repository license before redistribution. |
| combined_korean_vocabulary_list / julienshim | Korean TOPIK | Combined National Institute of Korean Language + TOPIK; check repository terms. |
| bienvenue-au-croissant / hyunahparc | French CEFR | No license file found at packaging time; runtime fetch only; do not redistribute data. |
| Goethe-Institut | German A1–B1 Wortlisten | Official PDFs; Goethe terms apply. |
| Profilo della lingua italiana / Università per Stranieri di Perugia | Italian CEFR | Publisher rights apply; runtime uses Wayback snapshots. |
| PCIC / Instituto Cervantes | Spanish CEFR | Instituto Cervantes terms apply. |
| TORFL / ТРКИ + zlat.spb.ru + veebiarhiiv.digar.ee | Russian lexical minimum | PDF/archive terms apply; scanned source may need OCR. |
| HSK / Chinese Testing International (chinesetest.cn) | Chinese HSK 2.0 | Official XLS; runtime fetch or user-provided; do not redistribute. |
| Heartade/spanish-words-cefr | Spanish CEFR fallback pointer in grading-catalog.json | Check repository license before use/redistribution. |
| Wiktionary (it/en/de/fr/es/ru/la) | Online IPA fallback | Wikimedia/Wiktionary terms apply; no offline dump is bundled. |
| Internet Archive Wayback Machine | Historical snapshots for Profilo/PCIC | Archive/service terms apply. |

## External engines / tools (not bundled)

| Tool | Used for | License / note |
|---|---|---|
| LibreOffice | DOCX → PDF headless | MPL-2.0; external application, install separately. |
| Tesseract OCR | Russian scanned PDF OCR | Apache-2.0; external CLI. rus.traineddata language data must be supplied by the user. |
| eSpeak NG | IPA for it/en/de/fr/es/ru/la | GPLv3; external CLI. |
| spaCy | Lemmatization | MIT; language models have their own model cards/terms. |
| spaCy models | it/en/de/fr/es | it_core_news_sm, en_core_web_sm, de_core_news_sm, fr_core_news_sm, es_core_news_sm; installed separately. |
| pymorphy3 | Russian lemmatization | MIT; installed separately. |
| pykakasi | Japanese romaji | MIT; installed separately. |
| fugashi / UniDic-lite | Japanese tokenization/lemma | fugashi MIT; UniDic has its own terms; installed separately. |

## Python packages (not bundled)

- python-docx (MIT), lxml (BSD), openpyxl (MIT), xlrd (BSD).
- PyMuPDF (AGPL-3.0 or commercial; check its terms before redistribution; installed separately).
- jieba (MIT), pypinyin (MIT).
- spacy (MIT), pymorphy3 (MIT), pykakasi (MIT), fugashi (MIT), unidic-lite (UniDic terms).
- requirements.txt is an install pointer only; no wheels or model files are shipped.

## Client compatibility

These are clients/interfaces that can consume the package, not dependencies:

- WorkBuddy: upload the bilingual-literature folder as a Skill zip.
- Claude Code / Claude.ai Skills: use SKILL.md + optional reference files; shell clients can run scripts/run.py.
- Cursor / Codex / DSH (DeepSeek Harness) / other shell-capable agents: read SKILL.md and run Python CLI.
- Gemini Apps Skills: text-only upload; scripts cannot make external requests; use content/reference mode.
- Doubao Work desktop: requires lowercase skill.md in the root; this PC package uses SKILL.md, so it is not directly loadable without a lowercase wrapper. Mobile Doubao is not supported for custom skills.
- Chat-only clients: read SKILL.md as instructions; no DOCX/PDF/vocabulary automation.

This list is not exhaustive: any agent that supports Agent Skills / SKILL.md, or can read files and execute Python, can use the package with the capabilities it provides.

