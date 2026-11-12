# SKILL 内工具调用说明

版本：0.3.0
许可：Unlicense
适用：需要把双语文献技能里的工具单独接到其它项目、流水线或智能体中的开发者。

## 一、工具位置

发行版：

C:\DSH个人助手工作区\dist\bilingual-literature-universal\bilingual-literature\scripts

全局开发副本：

C:\DSH工作区\.dsh\skills\dsh-bilingual-literature\scripts

GitHub 仓库：

https://github.com/carlogiailcantatore-commits/-

工具全部是普通 Python 命令行脚本，不依赖专有框架。run.py 只是统一入口，每个脚本都可以单独调用。

## 二、不要只复制单个脚本

脚本之间有本地模块依赖，包括 parsers.py、phonetic.py、ipa.py、lemmatize.py 等。它们还依赖 references 下的 style-profiles.json、grading-catalog.json、language-packs.json、requirements.txt。

复用时请复制整个 scripts 目录，并保留 references 目录。不要只复制 build_docx.py 或 vocab.py 单个文件。

## 三、调用方式

### 方式一：run.py 统一入口

~~~powershell
python scripts/run.py <命令> [参数...]
~~~

命令与脚本对应：

| 命令 | 脚本 |
|---|---|
| extract | scripts/extract.py |
| split-units | scripts/split_units.py |
| outline | scripts/outline.py |
| worklist | scripts/worklist.py |
| translate | scripts/translate.py |
| build-blm | scripts/build_blm.py |
| verify-md | scripts/verify_md.py |
| build-docx | scripts/build_docx.py |
| build-txt | scripts/build_txt.py |
| to-pdf | scripts/to_pdf.py |
| verify | scripts/verify.py |
| widths | scripts/widths.py |
| ipa | scripts/ipa.py |
| phonetic | scripts/phonetic.py |
| lemmatize | scripts/lemmatize.py |
| ocr-pdf | scripts/ocr_pdf.py |
| vocab | scripts/vocab.py |
| check-tools | scripts/check_tools.py |

### 方式二：其它项目用子进程调用

这是推荐的跨项目方式。路径请换成自己的发行目录。

~~~python
import os
import subprocess

SKILL = r"C:\DSH个人助手工作区\dist\bilingual-literature-universal\bilingual-literature"
PYTHON = r"C:\DSH个人助手工作区\.dsh-bilingual-venv\Scripts\python.exe"

def call_skill(script_name, *args):
    script = os.path.join(SKILL, "scripts", script_name)
    subprocess.run([PYTHON, script, *args], check=True)

call_skill("build_docx.py", "bilingual.md", "out.docx")
~~~

### 方式三：PowerShell 直接调用

~~~powershell
$py="C:\DSH个人助手工作区\.dsh-bilingual-venv\Scripts\python.exe"
$skill="C:\DSH个人助手工作区\dist\bilingual-literature-universal\bilingual-literature"
& $py (Join-Path $skill "scripts\build_docx.py") "bilingual.md" "out.docx"
~~~

## 四、主要工具和输入输出

### extract.py

~~~text
python scripts/extract.py <输入文件> <source.json>
~~~

输入 Word、PDF、TXT；输出 source.json，包含段落、文字片段、图片、脚注、链接和页面信息。

### split_units.py

~~~text
python scripts/split_units.py <source.json> <units.json> [--body-size N] [--classical]
~~~

输出 units.json，包含段落、句子、标题层级、链接、脚注和图片。--classical 只用于中文古文，按逗号、分号、冒号切短句；现代文不要用。

### outline.py

~~~text
python scripts/outline.py <units.json> <outline.md>
~~~

输出给人看的结构清单，不是最终文档。

### worklist.py

~~~text
python scripts/worklist.py <units.json> <work.json> [--structure structure.json]
~~~

输出带翻译槽位的工作单。structure.json 用于覆盖自动识别的结构。

### translate.py

~~~text
python scripts/translate.py export <work.json> <批次目录> [--chunk-chars N]
python scripts/translate.py merge <work.json> <批次目录> --out <translations.json>
~~~

export 生成批次文件；merge 把译文合并成 translations.json。

### build_blm.py

~~~text
python scripts/build_blm.py --work work.json --translations translations.json --out bilingual.md
~~~

可选参数：--notion、--source-lang、--target-lang、--assets-prefix、--sizes、--strict、--image-alts、--notes-zh。输出双语 Markdown。

### build_docx.py

~~~text
python scripts/build_docx.py <bilingual.md> <out.docx>
~~~

输入 BLM Markdown；输出双语 Word。

### build_txt.py

~~~text
python scripts/build_txt.py <bilingual.md> <out.txt>
~~~

输入 BLM Markdown；输出纯文本稿。

### to_pdf.py

~~~text
python scripts/to_pdf.py <docx> <out.pdf>
~~~

依赖 LibreOffice。脚本使用工作区临时目录和独立用户配置目录。

### verify_md.py

~~~text
python scripts/verify_md.py --work work.json --md bilingual.md [--degradations d.json] [--report r.json]
~~~

输出验收报告，状态为 PASS、PASS_DEGRADED 或 FAIL。

### verify.py

~~~text
python scripts/verify.py <source.json> <out.docx> [--degradations d.json] [--report r.json]
~~~

输出 Word 验收报告。

### vocab.py

~~~text
python scripts/vocab.py catalog
python scripts/vocab.py init --lang it --system CEFR --db vocab/vocab.db
python scripts/vocab.py status --db vocab/vocab.db
python scripts/vocab.py precheck --lang it --system CEFR --db vocab/vocab.db
python scripts/vocab.py extract --md bilingual.md --lang it --target zh --min B1 --db vocab/vocab.db --out doc.vocab.json
python scripts/vocab.py extract --md bilingual.md --lang it --target zh --all --out doc.all.json
python scripts/vocab.py fill --words doc.vocab.json --translations dictionary.json --out doc.filled.json
python scripts/vocab.py build --words doc.filled.json --format word --out doc.vocab.docx
python scripts/vocab.py build --words doc.filled.json --format excel --out doc.vocab.xlsx
~~~

拉丁语默认全量；其它语言要全量时显式传 --all。

### phonetic.py

~~~text
python scripts/phonetic.py "<单词或短语>" --lang it
~~~

输出 value、type、source、status 四个字段的 JSON。

### lemmatize.py

~~~text
python scripts/lemmatize.py "<单词>" --lang it --context "..."
~~~

输出词形还原结果。

### ocr_pdf.py

~~~text
python scripts/ocr_pdf.py <input.pdf> <out.txt> --lang rus
~~~

依赖 Tesseract 和对应语言数据。

### widths.py

~~~text
python scripts/widths.py --work work.json --translations translations.json --out sizes.json [--usable-pt N]
~~~

输出标题宽度和字号建议。

### check_tools.py

~~~text
python scripts/check_tools.py
~~~

输出 LibreOffice、Tesseract、eSpeak NG、jieba、pypinyin、xlrd、fugashi、spacy、pymorphy3、pykakasi、winget 的可用状态。

## 五、数据结构

### source.json

由 extract.py 生成，保存原始文档结构：format、file、paragraphs 或 blocks、media、footnotes、links、page。

### units.json

由 split_units.py 生成，保存 paragraphs、links、notes、body_size、heading_sizes。每个 paragraph 包含 idx、kind、size、text、sents、links、fns、images。

### work.json

由 worklist.py 生成，保存 items、sents、sid、pid、kind、text 和翻译槽位。

### translations.json

由 translate merge 生成，是 sid 到译文的映射。

### BLM Markdown

由标题、正文、引用块译文和隐藏标记组成。build_docx.py 读取标记里的字号和段落编号；没有标记时使用回退字号。

## 六、跨项目调用注意

1. 工作目录决定默认输出和默认词库路径；调用前先切换到项目目录。
2. scripts 和 references 要一起复制，不能只复制某个脚本。
3. 需要 Python 3.10 或更高版本；依赖见 references/requirements.txt。
4. PDF 需要 LibreOffice；OCR 需要 Tesseract；IPA 需要 eSpeak NG。
5. 字体和颜色由 build_docx.py 和 references/style-profiles.json 控制，不要在调用方另写一套字号。
6. 外部数据和词库不随包分发；vocab init 会从数据源运行获取，不要提交数据库或缓存。
7. 脚本默认按 UTF-8 处理文本；Word 和 Markdown 请保持 UTF-8。
8. verify-md 需要 work.json 和 bilingual.md；verify 需要 source.json 和 out.docx。
9. 输出文件已存在时会改名 _v2、_v3；调用方若要固定文件名，请自己先处理旧文件。
10. 第三方依赖和数据的许可证与项目 Unlicense 无关，使用前阅读 THIRD_PARTY.md。

## 七、打包和发布

技能包内的打包通常指生成交付文件：build_docx.py、build_txt.py、build_blm.py、to_pdf.py。

发布压缩包不是技能内脚本，用系统压缩命令或 GitHub CLI：

~~~powershell
Compress-Archive -Path bilingual-literature -DestinationPath bilingual-literature-universal.zip
Compress-Archive -Path bilingual-literature-universal\* -DestinationPath bilingual-literature-github.zip
~~~

GitHub Release 使用 gh release create 或 gh release upload。不要把它误当成 build_docx 的一部分。

## 八、路径对照

发行版脚本：C:\DSH个人助手工作区\dist\bilingual-literature-universal\bilingual-literature\scripts

全局开发脚本：C:\DSH工作区\.dsh\skills\dsh-bilingual-literature\scripts

发行版 references：C:\DSH个人助手工作区\dist\bilingual-literature-universal\bilingual-literature\references

GitHub 仓库：https://github.com/carlogiailcantatore-commits/-

## 九、许可

工具代码适用 Unlicense。第三方数据、模型、字体、引擎和服务不在本项目许可范围内，见 THIRD_PARTY.md。
