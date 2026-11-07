# Bilingual Literature Skill

A portable skill for turning 9 source languages (zh/it/en/de/fr/es/ru/ja/la) into Chinese or Italian sentence-pair bilingual editions, preserving images, footnotes, hyperlinks and heading structure, with optional graded or full-vocabulary export.

## Compatibility

- WorkBuddy: upload the bilingual-literature folder as a Skill zip.
- Claude Code / Cursor / Codex and other agents with file + shell access: run scripts/run.py or the individual scripts.
- Chat-only agents can read SKILL.md as instructions, but cannot run the DOCX/PDF/vocabulary pipeline.

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

## License

Code: GNU GPL v3.0 or later (see LICENSE). Derivative works must remain open under the same license. Third-party data sources: see THIRD_PARTY.md; datasets are fetched at runtime and are not redistributed with this repository.
