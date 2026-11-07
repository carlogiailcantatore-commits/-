# Bilingual Literature Skill (portable)

把外文文献做成「原文句 / 中文译文句」的双语稿；支持 DOCX / 文本 PDF / TXT 输入，输出 DOCX / PDF / TXT，并可导出分级词汇表。

## 适用智能体

- **WorkBuddy**：上传 `bilingual-literature` 文件夹为 Skill zip。
- **Claude Code / Claude.ai Skills**：使用 `SKILL.md` 和可选参考文件；有 shell 的客户端可跑 `scripts/run.py`。
- **Cursor / Codex / DSH（DeepSeek Harness）等有 shell 的智能体**：读 `SKILL.md`，直接跑 Python CLI。
- **Gemini Apps Skills**：只支持文本上传，脚本不能访问外部网站；用内容/参考模式。
- **豆包工作桌面端**：要求根目录小写 `skill.md`；本 PC 包是大写 `SKILL.md`，需要 lowercase wrapper。豆包移动端不支持自定义技能。
- **只有聊天/写作能力的智能体**：把 `SKILL.md` 当提示词，按规则人工执行；无法自动跑 DOCX/词库/PDF。
- 本包不依赖任何专有框架；`SKILL.md` 是流程说明，`scripts/` 是普通 Python CLI。

## 安装

需要 Python 3.10+。

```bash
# Windows
powershell -ExecutionPolicy Bypass -File .\skills\setup.ps1

# macOS / Linux
bash setup.sh

# 或手动
python -m pip install -r references/requirements.txt
```

可选：LibreOffice（DOCX→PDF，禁止用 Word 导出）；Tesseract（扫描 PDF OCR）；eSpeak NG（离线 IPA，缺省可用意大利语 Wiktionary 回退）。

## 快速开始

```bash
# 1) 从源文件抽取结构
python scripts/run.py extract "source.docx" "out/source.json"
python scripts/run.py split-units "out/source.json" "out/units.json"

# 2) 工作单 → 分批翻译 → 合并 → 生成 BLM / Notion
python scripts/run.py worklist "out/units.json" "out/work.json"
python scripts/run.py translate export "out/work.json" "out/tr"
# 填写 out/tr/tr_cN.json 的 translations 后：
python scripts/run.py translate merge "out/work.json" "out/tr" --out "out/translations.json"
python scripts/run.py build-blm --work "out/work.json" --translations "out/translations.json" --out "out/bilingual.md" --notion "out/notion.md"
python scripts/run.py verify-md --work "out/work.json" --md "out/bilingual.md"

# 3) 生成 DOCX
python scripts/run.py build-docx "out/bilingual.md" "out/final.docx"

# 4) 可选：PDF（LibreOffice）
python scripts/run.py to-pdf "out/final.docx" "out/final.pdf"

# 5) 可选：词汇表
python scripts/run.py vocab catalog
python scripts/run.py vocab init --lang it --db vocab/vocab.db
python scripts/run.py vocab extract --md "bilingual.md" --lang it --min B1
python scripts/run.py vocab build --words "vocab/docs/bilingual.vocab.json" --format excel --out "out/vocab.xlsx"
# Word 词表格式：原文/IPA音标/（变位说明）/原型 + 译文行；无 IPA 时显示 —
```

## 目录

```
run.py                  # 单入口
SKILL.md                # 流程/规则（给智能体读）
scripts/                # extract / build_docx / build_txt / vocab / parsers ...
references/grading-catalog.json  # 分级词库目录（不含数据本身）
templates/              # 双语 Markdown 示例
references/requirements.txt
setup.ps1 / setup.sh
```

## 词库与外部数据

- 分级词库**不在本包内**；`vocab init` 时按 `data/grading-catalog.json` 的源抓取/解析，写入外置 SQLite（默认 `vocab/vocab.db`）。
- 文档词表写 `vocab/docs/<doc>.vocab.json`；术语表写 `vocab/glossary.<lang>.json`。
- 首次 init 会询问数据库路径；确认后记在工作区 `.bilingual-vocab.json`。

## 限制

- PDF 输出必须用 LibreOffice（或等价工具），不要用 Word 导出。
- 扫描版 PDF 需要 Tesseract；没有就停并询问。
- Notion Markdown 只有三级标题、无颜色/脚注；本包导出的 Markdown 按此映射。
- 字体（Times New Roman / 楷体）在非 Windows 环境由 Word/LibreOffice 回退。

## 数据来源与许可

- 英语 CEFR-J：CC BY-SA 4.0（引用 Tono Laboratory）。
- 日语 JLPT：OpenJLPT 社区整理；韩语：combined_korean_vocabulary_list；法语：bienvenue-au-croissant。
- 德语：Goethe 官方 A1–B1 Wortliste PDF；意大利语：Profilo della lingua italiana（Wayback 快照）；西班牙语：PCIC inventories（Wayback 快照）。
- 俄语：ТРКИ B1 PDF 为扫描件，需 OCR。
- 运行期抓取，不随包分发受限数据；使用时请遵守各来源许可。
