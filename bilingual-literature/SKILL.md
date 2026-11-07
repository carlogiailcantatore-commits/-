---
name: bilingual-literature
display_name: 外文文献双语整理
display_name_en: Bilingual Literature
description: 把 9 种源语言（zh/it/en/de/fr/es/ru/ja/la）的外文文献整理成中文或意大利语句对句双语稿（DOCX/PDF/TXT/Notion Markdown），保留图片、脚注、链接、标题层级，并可导出分级词汇表。触发词：句对句翻译、句对句译、双语整理、对照翻译，以及意大利语对应说法。
description_zh: 把 9 种源语言的外文文献整理成中文或意大利语句对句双语稿，保留原格式，并可导出分级词汇表。
description_en: Turn 9 source languages into Chinese or Italian sentence-pair bilingual editions, preserving layout, images, links and headings, with optional graded vocabulary.
version: 0.1.17
author: Bilingual Literature Contributors
license: GPL-3.0-or-later
examples_zh:
  - 把这份意大利语文献句对句翻译成中文，保留图片和脚注
  - 把这篇 PDF 做成中外对照稿，并导出 B1 以上词汇表
examples_en:
  - Translate this Italian document sentence by sentence into Chinese, keeping images and footnotes.
  - Make a bilingual edition of this PDF and export a B1+ vocabulary list.
---


# 外文文献双语整理（目标：中文 / 意大利语）

## 0.1 语言矩阵

- 源语言：zh、it、en、de、fr、es、ru、ja、la
- 目标语言：zh、it
- 有效方向：9 × 2 − 2 = 16 对；同语对拒绝
- 主对：it→zh、zh→it；其余 14 对为二等 best-effort；la→zh、la→it 为 secondary_b
- 词表永远跟源语言；中文用拼音+HSK，日语用罗马字+JLPT，其余 IPA；拉丁语跳过分级，提取全部词；词表不做等级过滤


## 执行模式

- **A. 脚本模式**（推荐）：智能体有文件读写 + Bash/Python 执行能力时，用 `scripts/run.py` 和 `scripts/*.py` 完成抽取、排版、词汇表、PDF。
- **B. 纯文本模式**：只有聊天/写作能力时，按本文件规则人工产出双语 Markdown；无法自动生成 DOCX/PDF/词汇表，需向用户说明限制。


## 0. 触发与开工前确认

- 触发词：`句对句翻译`、`句对句译`、`双语整理`、`对照翻译`。出现任一，**先询问用户是否启用本技能**，不得静默触发。
- 开工前确认（缺一不可）：源文件路径；源语言（可自动判断，但要说明）；目标语言（默认中文）；**输出格式（多选，每项独立）**；领域（默认按内容判断）。
- 输出格式必须用**多选/复选**（平台提问工具支持时用 multi_select=true）问，不要用“单选+组合项”：选项固定为 `DOCX`、`PDF`、`TXT`、`Notion Markdown` 四项，各管各的；默认只勾与输入相同的格式（输入 TXT 才默认勾 TXT），用户可同时勾多个；PDF 需 LibreOffice，Notion Markdown 单独交付。
- 禁止把“示例说明/模板文字”混进文稿正文。

## 1. 固定格式规则（默认，不逐条问）

### 1.1 句对句
- 原文一句一段，译文一段紧跟其后，成对出现。
- 译文样式（Word）：中文目标=源字号−2；意大利语目标=源字号；字体按 target profile（中文楷体，意大利语 Times）；深蓝色（#1F4E79）；**不用斜体**。字号由源文档驱动，不写死。
- 译文**禁止**在术语后括号附原文；术语靠句对句和术语表对应。
- 对不上就继续在**可断标点**（。？！；：，. ? ! ; : ,）处切短；**不得按字数硬切**，没有标点不切。
- 原文段 + 译文段必须同页：原文段设 keepNext，两者设 keepLines。

### 1.2 标题层级（Word 五级 + 文档标题）
- L0 文档标题 22pt；L1 部分 18pt；L2 章节 16pt；L3 子章节 14pt；L4 示例 13pt；正文 12pt。严格单调，同级统一。
- **短标题**：合并成 `ITALIANO/中文` 单行后，在该级字号下能单行放下（按页面可用宽度实测）。
- **长标题**：放不下的不算短标题；同一标题内排两行（原文行 + 中文行），级别不变。
- 编号补全：Caccini 1–5、Tosi 1–7 之类按原文补；示例保留 `Esempio N`。
- 第一部分若原文无标题，从内容总结加一个 L1 标题（需在结构分析里给用户看）。

### 1.3 示例
- 示例是独立单元，禁止并进正文句。
- 结构：L4 示例标题（`Esempio N/例N`）→ 数据行（原样、不译、代码块）→ 标签（短标题格式，如 `Solfeggio/视唱`）→ 说明正文（句对）。
- `Ut–Re–Mi–Fa`、`ut–re–mi–fa`、四音列串联等纯数据**绝不翻译**，也不进标题中文。
- 示例说明里的短标签用短标题格式；不新开标题级。

### 1.4 版式清理
- 只清**正文**里的空段和段首缩进；标题间距保留。
- 不额外用段间距模拟空行。

### 1.5 文献与链接
- 参考文献条目三行：原文 / 中文 / 链接。链接必须实际打开验证（200）才写；找不到就只写原文 + 中文；失效链接只放链接并标注“链接已失效”。
- 文末 Link utili 同样三行格式；失效只放链接 + 标注。

## 2. 中间格式：双语 Markdown（BLM）

所有输入先转成 `bilingual.md`（中间文件，**作为最终交付物保留**，但关卡里不展示内容）：

- YAML front matter：source / source_lang / target_lang / domain / output_format / title_original / title_zh。
- 标题：`#`=L0 标题，`##`=L1 部分，`###`=L2 章节，`####`=L3 子章节，`#####`=L4 示例。
- 原文段落：普通段落。译文段落：`> ` 引用块。
- 示例数据：围栏代码块；示例标签：`**Solfeggio/视唱**`。
- 图片：`![说明](assets/xxx.png)`。
- 脚注：文末 `## 注释`，每条 `**N.** 原文` + `> 中文`。
- 参考文献 / 链接：按「原文 / 中文 / 链接」三行写；只收验证过的链接，失效只放 URL + 「链接已失效」。

## 3. 关卡（只保留两个）

### 关卡 1：书目录 + 正文一句话概述
1. 先给 `[前言概述]`：**200–300 字**总体概述。
2. 再按**实际阅读顺序**输出 L1–L4 标题目录，缩进表示层级；每个标题给原文/中文、短/长、段号。
3. **只对正文写 `[内容概述]`**：标题本身不写；每个标题下直接属于它的正文合并成**一句话**（极致缩写，代替正文），放在该节正文位置，供用户快速审阅；正文全文不展示。
4. 没有正文的标题不写概述。
5. 数量统计只能附在最后，不能代替目录。
6. 先跑 `scripts/extract.py` → `scripts/split_units.py` → `scripts/outline.py` 生成骨架；文言文/古文用 `split_units.py ... --classical`，按 `，；：` 切到短句；现代文用默认。确认结构后写 `structure.json`（kinds/synth 覆盖），再跑 `scripts/worklist.py units.json work.json --structure structure.json` 生成带 `zh` 槽的工作单。**不要另写项目专用 build_units/切句器**。

### 关卡 2：双语章节核对
- 按结构展示**全部章节**：每章给**双语标题** + **正文中文摘要（每章 20–100 字）**。
- 用户确认后才继续。

### 输出前询问：参考文献
- 生成最终交付文件前**必须问用户：要不要联网找参考文献 / 补链接？**
- 要：复用既有文献流程——从正文抽出被引文献（作者/书名/篇名），联网找可验证版本；每条按「原文 / 中文 / 链接」三行写；链接必须实际打开验证（200），只收验证过的；找不到可靠链接就只列原文+中文、省略链接；失效链接只放 URL 并标「链接已失效」；**不编造条目、不把搜索结果当正文**；文献节放在 BLM 末尾（`## Riferimenti bibliografici / 参考文献`）。
- 不要：不新增文献节，保留原文已有引用。

## 4. 输出

- 按用户**多选**的格式交付，可同时出多份；默认只勾与输入相同的格式（输入 TXT 才默认勾 TXT）；TXT 不默认勾；Notion Markdown 单独勾选。
- 翻译后装配链：`translate.py export` → 填 `tr_cN.json` → `translate.py merge`（缺失必须报）→ `build_blm.py` → `verify_md.py` → `build_docx.py` / `build_txt.py`；Notion 直接交 `--notion` 产物。
- PDF **不得用 Word 导出**：用 LibreOffice headless（方案 A）；缺工具时先取得用户授权再联网下载/安装。
- 输出后：
  1. 询问是否导出词汇表（Excel 或 Word）；
  2. 询问是否删除中间 Markdown。

## 5. 词汇表（外置 SQLite）

- 三层都外置：
  1. **分级词库**：`vocab/vocab.db`（SQLite：datasets / words / meta）
  2. **文档词表**：`vocab/docs\<文档名>.vocab.json`（复用资产，导出后保留）
  3. **术语表**：`vocab/glossary.<lang>.json`（按语言分文件，自动补、可手改）
- **路径**：默认 `./vocab/vocab.db`；首次 `init` 时必须问用户确认默认路径或指定另一个路径；确认后写工作区根 `.bilingual-vocab.json` 记住路径。
- **初始化**：用户明确要词表、且该语言/体系未初始化 → 自动初始化；一次只初始化选中的“语言+体系”，**抓全等级入库**，不批量抓所有语言。
- **体系提醒**：每次 `extract` 必须显示：

```text
使用体系：it / CEFR (Profilo)    门槛：B1及以上
按当前体系过滤；要换体系请指定体系名称或询问我可用体系
```

- 用户要别的体系：重新找源/补解析器 + 单独 `init --lang <lang> --system <id>`；**不许复用旧体系**。
- 过滤：B1 以上 = 用全等级库反向排除低等级；不设默认等级，每次导出让用户选门槛。
- 收录范围：专名、功能词、短语，只要在所选等级范围内都收。
- **词表前置检查**：先跑 `vocab.py precheck --lang <lang> [--system <system>]`；tokenizer / lemmatizer / phonetic / 分级数据任一缺失 → **不进入词表**，只给“补依赖 / 跳过 / 终止”。
- 中文：HSK 2.0 官方词表（`https://www.chinesetest.cn/userfiles/file/HSK/HSK-2012.xls`），解析器 `hsk_xls`，pinyin 由 `pypinyin` 生成；中文不生成 IPA。
- Excel：按源语言动态列；中文为 `原文 / 拼音 / HSK / 意大利语释义`，其他语言为 `原文 / IPA 或罗马字 / 变位说明 / 原型 / 译文`。
- Word：按实际字段自适应，不补空段；示例：

```
中文：原文/拼音
意大利语/英语/德语/法语/西班牙语/俄语：原文/IPA/（变位说明）/原型
日语：原文/罗马字/（词形）/原型
```

- 没有变位/原型与原文相同则省略；不出现 `//`、空括号。
- IPA/罗马字：优先本地引擎；缺引擎走指路；都不通过预检则不出词表，不猜。
- 变位：词形变化、性数、时态、分词等；**歌词省音/缩合（l’amore、dell’aria）算一种变位**，归到原型并标注。
- 俄语：解析器是 OCR 型；需 Tesseract + `rus.traineddata`（放工作区 `tessdata/` 或设置 `TESSDATA_PREFIX`）。无 OCR 时提示缺前置并问是否补；补则授权联网装，不补则跳过词表。

## 6. PDF / OCR

- PDF 输入：先检测文字层；有文字层直接抽；扫描件用 OCR（Tesseract）。
- 没有 OCR：停止输出，告知用户“无 OCR”，询问是联网找工具还是换文件格式。
- PDF 输出：DOCX → LibreOffice headless 转 PDF；缺 LibreOffice 先问授权再下载安装。

## 7. 验收（必须跑）

- 原文零丢失：逐段/逐句比对源与输出。
- 图片、脚注、超链接数量与源一致（DOCX 输入）。
- 句对同页：导出 PDF 后逐对检查，0 对跨页。
- 无正文空段、无段首缩进。
- 标题层级单调，短标题单行、长标题两行。
- 链接均验证过；失效有标注。
- Markdown 输出跑 `verify_md.py --work ... --md ...`；DOCX 输出跑 `verify.py source.json out.docx`。
- 两者都支持 `--degradations` + `--report`；状态为 PASS / PASS_DEGRADED / FAIL；FAIL 阻断交付。
- 只有图片缺失、脚注缺失、句对跨页允许用户确认后降级；其余 FAIL。

## 8. 工具与命令

> 在工作区目录（可写）里跑；venv 默认 `.bilingual-venv`（可用 `BILINGUAL_VENV` 覆盖）。
> 词库默认 `./vocab/vocab.db`，首次 init 需确认路径。

- `scripts/setup.ps1` / `setup.sh` / `scripts/bootstrap.py`：建 venv、装 python-docx/lxml/PyMuPDF/openpyxl。
- `scripts/run.py <command>`：单入口（extract / build-docx / build-txt / to-pdf / verify / vocab / check-tools）。
- `scripts/check_tools.py`：报告 LibreOffice / Tesseract / winget 是否可用。
- `scripts/install_tools.ps1 -Tool libreoffice|tesseract -Authorized`：**用户授权后**才联网安装。
- `scripts/ocr_pdf.py <pdf> <out.txt> [--lang ita+eng]`：扫描 PDF → OCR 文本；缺 Tesseract 返回 `OCR_MISSING`。
- `scripts/extract.py <file> <out.json>`：DOCX/PDF/TXT → 结构 JSON；DOCX 为 span 级（有序 text/link/fn/img，保留 run 级粗体/字号）。
- `scripts/split_units.py <source.json> <units.json> [--body-size N]`：句级切分 + 结构提示（L0–L4/body/list/image）。
- `scripts/outline.py <units.json> <outline.md>`：生成“书目录 + 正文一句话概述”骨架（标题、段号、每节概述占位）。
- `scripts/worklist.py <units.json> <work.json> [--structure structure.json]`：生成翻译工作单；每句带 `zh` 空槽与链接/脚注/图片 token，不硬编码段落号。
- `scripts/translate.py export <work.json> <dir> [--chunk-chars N]`：生成分批翻译件 `tr_cN.json` / `tr_input.txt`。
- `scripts/translate.py merge <work.json> <dir> --out translations.json`：合并译文、检查缺失/多余/重复；缺失时非零退出。
- `scripts/build_blm.py --work work.json --translations translations.json --out bilingual.md [--notion notion.md] [--sizes sizes.json] [--source-lang it] [--target-lang zh|it]`：生成 BLM/Notion Markdown；带字号标记与 sizes 旁路；图片说明、脚注译文用 JSON 传入。
- `scripts/verify_md.py --work work.json --md bilingual.md`：检查原文片段、链接、图片、脚注、译文孤儿、空段。
- `scripts/widths.py --work work.json --translations translations.json --out widths.tsv`：标题单行宽度实测。
- `scripts/phonetic.py <word> --lang it|en|de|fr|es|ru|ja|zh`：多语言发音（IPA / 罗马字 / 拼音）；`ipa.py` 保留为意大利语兼容别名。
- `scripts/lemmatize.py <word> --lang <lang> [--context "..."]`：语言相关词形还原（spaCy / pymorphy3 / UniDic）。
- `scripts/build_docx.py <bilingual.md> <out.docx>`：BLM → DOCX；读取字号标记和目标 profile；旧 BLM 无标记时回退固定层级。
- `scripts/build_txt.py <bilingual.md> <out.txt>`：BLM → TXT。
- `scripts/to_pdf.py <docx> <out.pdf>`：LibreOffice 转换（缺工具先问授权）。
- `scripts/verify.py <source.json> <out.docx>`：零丢失/图片/链接检查。
- `scripts/parsers.py`：内置解析器（goethe_pdf / profilo_html / pcic_html / torfl_pdf）。
- 词汇表命令：
  - `vocab.py catalog`：列出语言/体系/当前体系/等级/是否已初始化/DB 路径。
  - `vocab.py init --lang it [--system CEFR] --db <path>`：初始化该体系全部等级；首次先问路径。
  - `vocab.py status`：已初始化数据集、词数、来源、时间。
  - `vocab.py extract --md <bilingual.md> --lang it --min B1 --out <doc.vocab.json>`：只读 SQLite；文档词表单独落盘。
  - 拉丁语：`vocab.py extract --md <bilingual.md> --lang la --target zh|it --out <doc.vocab.json>`，不传 `--min`，输出全部词；翻译用 `fill` 接用户词典。
  - 全翻模式：任意语言加 `--all`（如 `--lang it --all`），跳过分级过滤，输出全部词；拉丁语默认就是全翻。
  - `vocab.py precheck --lang <lang> [--system <system>] [--db <path>]`：检查 tokenizer/lemmatizer/phonetic/分级数据；不通过只给补/跳过。
  - `vocab.py fill --words <doc.vocab.json> --translations <map.json> --out <doc.zh.json>`：把中文释义写回词表（key 用 lemma/original）。
  - `vocab.py build --words <doc.zh.json> --format excel|word --out <file>`：输出词汇表（Word 四段式含 IPA）。
  - `vocab.py glossary add --lang it --term ... --translation ...`：术语表写 `vocab/glossary.it.json`。

## 9. 已知坑（来自实战）

- Notion Markdown 只有三级标题、无颜色/脚注：导出 Notion 版时 L4 用加粗，译文用引用块。
- Python 写桌面可能被系统保护/权限限制：先写工作区，再复制到目标目录。
- 改 MCP/技能配置后需要重载或重启对应客户端才生效。
- 扫描 PDF 无文字层时 OCR 必须先确认。
- Word 打开中的文件会被占用：另存新名或先让用户关闭。