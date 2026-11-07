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

## Python dependencies (installed by user, not bundled)

- `jieba` (MIT), `pypinyin` (MIT), `xlrd` (BSD) for Chinese segmentation/HSK parsing; install only when needed.
- `espeak-ng` (GPL-compatible engine, external CLI) for IPA; not bundled.

- Tesseract OCR: Apache-2.0; external CLI, not bundled. Russian TORFL requires `rus.traineddata` supplied by the user.
