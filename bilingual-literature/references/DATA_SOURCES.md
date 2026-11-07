# 词汇表结构（外置）

默认目录（相对当前工作区）：

```
vocab/
  vocab.db                 # SQLite：datasets / words / meta
  docs/<文档名>.vocab.json  # 文档词表（复用资产，导出后保留）
  glossary.<lang>.json     # 术语表（按语言分文件）
```

首次初始化时确认 DB 路径，并把路径记录在工作区根 `.bilingual-vocab.json`。

## SQLite 表

- `datasets`：lang / system / name / levels / sources / note / fetched_at / word_count
- `words`：dataset_id / word / lemma / level / pos / notes / phonetic
- `meta`：schema 版本等

## 初始化规则

- 用户明确要词表、且该语言/体系未初始化 → 自动初始化；
- 一次只初始化选中的“语言+体系”，**抓全等级入库**，不批量抓所有语言；
- 导出时按门槛过滤（如 B1 以上 = 用全等级库反向排除低等级）；
- 源更新用 `init --refresh`（重跑 init 即覆盖）；
- 体系必须显式显示；用户换体系 → 重新找源/补解析器 + 单独 init，不复用旧体系。

## 当前源与解析器

| 语言 | 体系 | 状态 | 源/解析器 |
|---|---|---|---|
| en | CEFR-J | 已可用 | olp-en-cefrj CSV |
| ja | JLPT | 已可用 | OpenJLPT 分文件 CSV |
| ko | TOPIK | 已可用 | combined_korean_vocabulary_list TSV |
| fr | CEFR | 已可用 | bienvenue-au-croissant A1–C2 JSON |
| de | Goethe | 已可用 | Goethe A1–B1 PDF + goethe_pdf |
| it | CEFR (Profilo) | 已可用 | Profilo A1–B2 Wayback + profilo_html |
| es | PCIC | 已可用 | PCIC inventories Wayback + pcic_html |
| ru | TORFL | 需 OCR | ТРКИ B1 扫描 PDF + torfl_pdf；无 Tesseract 报 OCR_REQUIRED |
| zh | HSK 2.0 (1–6) | 已可用 | 官方 HSK-2012.xls + hsk_xls；pinyin 由 pypinyin 生成；不内置数据 |

## HSK 2.0

- 官方源：https://www.chinesetest.cn/userfiles/file/HSK/HSK-2012.xls
- 词数：5000（HSK1 150 / HSK2 150 / HSK3 300 / HSK4 600 / HSK5 1300 / HSK6 2500）
- 解析器：`hsk_xls`；需要 `xlrd`
- 拼音：`pypinyin`，带声调；不内置拼音表
- 发行版只给 URL 和解析器，不随包带 HSK 数据
- 全局版可把官方 XLS 转成 `data/hsk2.tsv` 缓存，但该文件不进入发行包
