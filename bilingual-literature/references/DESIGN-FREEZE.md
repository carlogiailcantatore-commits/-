# 设计冻结 v1（Phase 0）

本文件只记录已冻结的架构决策，不代表代码已实现。

## 语言矩阵

- 目标语言：zh、it
- 源语言：zh、it、en、de、fr、es、ru、ja、la
- 有效方向：9 × 2 − 2 = 16 对
- 主对：it→zh、zh→it
- 二等：其余 12 对为 secondary_a；ja→zh/it、la→zh/it 为 secondary_b（best-effort）

## 词表

- 词表跟源语言走。
- 中文源：HSK 2.0（1–6），带声调拼音；不使用 IPA。
- 日语源：分词 + 词形 + Hepburn 罗马字；不使用 IPA。
- 意/英/德/法/西/俄/拉丁源：IPA；拉丁语跳过分级，提取全部词；不做等级过滤。
- 任意语言可用 `vocab.py extract --all` 进入全翻模式，跳过分级过滤；默认仍按所选等级。
- 中文词表用于 zh→it。
- 缺 tokenizer / lemmatizer / phonetic / 分级数据 → **不进入词表**，只给“补依赖 / 跳过 / 终止”。
- 不生成缺列、缺音标、缺分级的半成品词表。

## 字号与标题

- 字号来自源文档，不写死绝对 pt。
- 中文译文正文：max(8, src_pt − 2)。
- 意大利语译文正文：src_pt（同字号）。
- 标题译文：src_pt；源标题字号非单调时回退 22/18/16/14/13。
- 译文颜色：中文、意大利语均为 #1F4E79；无斜体。
- BLM 用不可见标记携带 pid/kind/src_pt；无标记时 fallback。

## 交互语言

- 母版中文；中文、意大利语原生模板。
- 其他语言：中文母版 → 翻译；失败回退中文。
- 只翻译交互层，不翻译交付文档。
- 不支持的语言不静默开始，先问是否启用。

## 消息

- messages/zh.json、messages/it.json。
- 扁平点分 key；占位符 {name}；中意 key 与占位符必须一致。
- 其他语言运行时翻译，不落盘。

## 验收与降级

- 状态：PASS / PASS_DEGRADED / FAIL。
- 仅图片缺失、脚注缺失、句对跨页允许用户确认后降级。
- 字体/字号 fallback、Notion 限制、二等质量只记 warning。
- 失败必须阻断交付；同一失败最多重试 2 次。
- 输出文件已存在：自动重命名 _v2、_v3。

## 依赖指路

- 发行版不内置任何引擎、词典、模型、HSK/CEFR 数据。
- language-packs.json 提供 provider、安装命令、语言覆盖和必需性。
- 缺依赖时明确报状态码，不猜。

## 后续阶段

1. Phase 1：字号传递 + target profile
2. Phase 2：词表预检 + HSK
3. Phase 3：phonetic provider
4. Phase 4：16 对开放（含拉丁语二级）
5. Phase 5：verify 降级与打包

