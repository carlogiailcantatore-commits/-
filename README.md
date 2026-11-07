# Bilingual Literature Skill

A portable skill for turning 9 source languages (zh/it/en/de/fr/es/ru/ja/la) into Chinese or Italian sentence-pair bilingual editions, preserving images, footnotes, hyperlinks and heading structure, with optional graded or full-vocabulary export.

## Compatibility

- **WorkBuddy**: upload the `bilingual-literature` folder as a Skill zip.
- **Claude Code / Claude.ai Skills**: use `SKILL.md` + optional reference files; shell clients can run `scripts/run.py`.
- **Cursor / Codex / DSH (DeepSeek Harness) / other shell-capable agents**: read `SKILL.md` and run the Python CLI.
- **Gemini Apps Skills**: text-only upload; scripts cannot make external requests; use content/reference mode.
- **Doubao Work desktop**: requires lowercase `skill.md` in the root; this PC package uses `SKILL.md`, so it needs a lowercase wrapper. Mobile Doubao is not supported for custom skills.
- **Chat-only agents**: read `SKILL.md` as instructions, but cannot run the DOCX/PDF/vocabulary pipeline.

This list is not exhaustive: any client that supports Agent Skills / `SKILL.md`, or can read files and run Python, can use the package within its capabilities.

## Quick start

```bash
python -m pip install -r bilingual-literature/references/requirements.txt

python bilingual-literature/scripts/run.py extract source.docx out/source.json
python bilingual-literature/scripts/run.py split-units out/source.json out/units.json
python bilingual-literature/scripts/run.py outline out/units.json out/outline.md
python bilingual-literature/scripts/run.py worklist out/units.json out/work.json
python bilingual-literature/scripts/run.py build-docx bilingual.md out/final.docx
```

## Layout

```text
bilingual-literature/
  SKILL.md
  references/
  scripts/
  templates/
LICENSE
THIRD_PARTY.md
```

## Third-party data and links / 第三方数据与链接

This repository does not bundle third-party datasets, models, fonts, engines, or services. URLs and install commands are provided only as pointers for users to obtain those resources under their own terms. The GPL license applies only to this repository's code and documentation; it does not grant any rights to third-party data, services, or content. Links are not endorsements or authorization to redistribute, and users are responsible for complying with the applicable source terms and local law.

本仓库不打包第三方数据集、模型、字体、引擎或服务；URL 与安装命令仅作获取入口，第三方资源仍受其自身条款约束。GPL 许可仅覆盖本仓库的代码与文档，不授予任何第三方数据、服务或内容的权利。链接不构成授权、背书或再分发许可；使用者应自行遵守来源条款与当地法律。

## License

The author's bilingual use statement is in [DECLARATION.md](DECLARATION.md).

Code: GNU GPL v3.0 or later (see LICENSE). Derivative works must remain open under the same license. Third-party data sources: see THIRD_PARTY.md; datasets are fetched at runtime and are not redistributed with this repository.
