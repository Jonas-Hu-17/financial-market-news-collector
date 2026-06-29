# 调优任务 5：修复「同日重复条目」+「JSON 残渣」

> 致执行者：发现两个 bug。逐项 TDD、只跑相关分目录测试(勿全量)、单独 commit。

## Bug 1：同一天重复生成 brief 时，brief_item 累加而非替换（根因）

**现象**：最新 brief 有 48 条 = 12 个唯一 story × 4（今天管线被跑了约 4 次）。`brief.create` 用了 `ON CONFLICT DO UPDATE` 复用同一 `brief_id`，但 `BriefAssembler.build` 每次又插入一遍 brief_item，旧的没清，导致每条重复 N 次、rank 重复。**不是去重失败**（同一 story_id）。

**改法**：重新生成某期 brief 时，**先清空该 brief 的旧 brief_item 再插入**（替换语义）。
- 在 `BriefAssembler.build` 拿到 `brief_id` 后、写入新 item 前，调用 `BriefItemRepo.delete_for_brief(brief_id)`。
- `BriefItemRepo` 新增 `delete_for_brief(brief_id: int) -> None`：`DELETE FROM brief_item WHERE brief_id=?`。
- 同时清掉旧的 market_view（`build` 末尾本就会 set 新的，无需额外处理）。
- 测试 `tests/web` 或 `tests/db`：对同一 (period_type, period_date, language) 连续 `build` 两次，断言最终 brief_item 数量 = 单次的数量（不翻倍）、无重复 story_id。
- commit: `fix(brief): replace brief_items on regenerate (no duplicate accumulation)`

## Bug 2：`_clean_view` 未覆盖 `summary": "...` 等 JSON 残渣形态

**现象**：某条 view 显示 `summary": "据媒体报道…`，是模型返回整段 JSON、解析回退后残留了字段名前缀。现有 `_clean_view` 只处理 `"view":` 形态。

**改法**：加固 `src/web/queries.py` 的 `_clean_view`（静态导出也复用它），覆盖更多形态：
- 若文本含 `"view"`：优先提取 `"view"` 字段值（已有逻辑保留）。
- 否则若文本以 `summary"` / `summary":` / `"summary"` 开头，或含 `summary": "`：提取其后的实际内容（取 `summary": "` 到结尾的下一个 `"` 之前，或回退到去掉该前缀）。
- 统一兜底：strip 掉开头的 `{`, `"`, `,`, 字段名残片（`summary":`、`view":`），strip 掉结尾的 `"`, `}`。
- **仅在检测到 JSON 残渣特征时清洗**，正常中文 view 原样返回（不误伤）。
- 测试 `tests/web/test_clean_view.py`：覆盖三种输入 —
  - 正常中文 view → 原样
  - `", "view": "正文"}` → 得"正文"
  - `summary": "正文` / `"summary": "正文", "view": "..."` → 得正确正文
- commit: `fix(web): harden _clean_view against summary/view JSON-fragment leaks`

> 更彻底的根治在 `src/view/generator.py` 的 JSON 解析兜底（让它稳定解析、失败时只取纯文本）；若顺手可一并加固，但 `_clean_view` 作为渲染层兜底必须覆盖以上形态。

## 收尾：清理现存重复数据 + 重新导出

1. 删掉当前重复的 brief_item（保留每个 (brief_id, story_id) 一条），或直接删 brief 后重跑：
   ```bash
   uv run python -c "import sqlite3; d=sqlite3.connect('data/marketnews.db'); d.execute('DELETE FROM brief_item WHERE id NOT IN (SELECT MIN(id) FROM brief_item GROUP BY brief_id, story_id)'); d.commit(); print('deduped', d.total_changes)"
   ```
2. 重新导出：`uv run python -m src.web.static_export --out site`
3. 本地 `cd site && python3 -m http.server 8080` → http://localhost:8080 复查：SpaceX 等只出现一次、无 JSON 残渣。
- commit（数据/导出产物如需）：`chore: dedupe brief_items and re-export`

## 自检
- 同日重复 build 不再翻倍。✔
- `_clean_view` 覆盖 summary/view 两类残渣、不误伤正常中文。✔
- 现存重复已清、site 复查干净。✔
