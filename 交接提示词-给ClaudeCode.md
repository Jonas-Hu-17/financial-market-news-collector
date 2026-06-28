# 给 Claude Code（接 DeepSeek）的交接启动提示词

> 用法：先按下面「准备步骤」把仓库和文档放好，再把「===启动提示词===」之间的整段，粘贴进 Claude Code 作为第一条消息。

## 准备步骤（你先手动做）

```bash
# 1. fork 并克隆 Horizon（或直接克隆后改 remote）
git clone https://github.com/Thysrael/Horizon.git marketnews
cd marketnews
git checkout -b marketnews-phase1

# 2. 把设计文档与实施计划拷进仓库，供 Claude Code 阅读
mkdir -p docs/specs docs/plans
cp "/Users/huyihan/Desktop/MarketNews收集工具/docs/specs/"*.md docs/specs/
cp "/Users/huyihan/Desktop/MarketNews收集工具/docs/plans/"*.md docs/plans/

# 3. 配置 DeepSeek 与依赖
uv sync
cp .env.example .env            # 在 .env 填入 DEEPSEEK_API_KEY
cp data/config.example.json data/config.json
git add -A && git commit -m "chore: import design spec and implementation plans"
```

---

## ===启动提示词（粘贴给 Claude Code）===

我们要在当前这个 fork 自 Horizon 的仓库里，构建一个**金融市场每日 Brief 个人工具（Phase 1）**。完整设计与逐任务实施计划已经放在仓库里，**请严格按计划执行，不要自由发挥架构**。

**第一步——先读，再动手（务必按序）：**
1. `docs/specs/2026-06-28-金融市场brief-设计文档.md`（整体设计、数据模型、合规原则）
2. `docs/plans/2026-06-28-phase1-计划索引.md`（路线图：7 个子计划 + Horizon「复用 vs 新建」对照 + 接口契约）
3. 然后从子计划 0 开始，逐个执行：
   - `subplan-1-持久化数据层` → `subplan-2-摄取层与去重与金融源` → `subplan-3-embedding与跨天聚类` → `subplan-4-金融打分与分类与实体` → `subplan-5-中性view生成与brief组装` → `subplan-6-展示回顾与投递`

**执行方式（每个子计划内部）：**
- 严格 TDD：先写失败测试 → 跑测试确认失败 → 写最小实现 → 跑测试确认通过 → 提交。计划文件里每个任务都给了**完整的测试代码、实现代码、确切文件路径、运行命令**，照着做即可。
- 每完成一个任务就 `git commit`（用计划里给的 commit message）。
- 一个子计划全部任务跑通后，**停下来汇报**：列出新增/修改的文件、测试结果，等我确认后再进入下一个子计划。

**必须遵守的全局约束：**
- 技术栈：Python 3.11+、沿用现有 `uv`/`pyproject.toml`；数据库 **SQLite + sqlite-vec**；embedding 用**本地 `sentence-transformers`**（384 维，零成本）；LLM 用 **DeepSeek**（`provider=deepseek`，`DEEPSEEK_API_KEY`）。
- **最大化复用 Horizon**：scrapers 框架（`src/scrapers/base.py`）、AI 客户端（`src/ai/client.py`）、投递（`src/services/`、`docs/` Pages）都复用，不要重写。Horizon 是无状态文件式的，我们新增的**持久化层（`src/db/`）是核心新增模块**。
- 🔒 **合规第一原则（不可违背）**：生成的 view 只做**中性影响陈述**，绝不含投资建议——不出现 buy/sell/看多/看空/目标价/建议买入卖出/增持减持等。每期 brief 必带免责声明。子计划 5 的 `ComplianceChecker` 必须实现并接入。
- **省 token 机制要落实**：精确去重（dedup_key）和跨天聚类都发生在打分/view 之前；只有「新建 story」才进入昂贵的分析与 view 生成；打分只读标题+摘要。
- 工程原则：异步并发 I/O、DB 索引 + 向量索引、新源失败只跳过不中断、Pydantic 校验。**不要**做 dynamic typing / JIT kernel / 底层重写这类过早优化。

**遇到以下情况，停下来问我，不要擅自改设计：**
- 计划里的接口签名与 Horizon 实际代码冲突（例如 `ai/client.py` 的方法名与计划假设不一致）——先报告实际情况再调整，保持对外接口不变。
- 需要新增计划中未列出的依赖或数据表。
- 任何会削弱合规约束或改变数据模型的改动。

现在开始：先读完上述 1、2 两份文档，给我一个简短的「我理解的执行计划 + 我看到的 Horizon 实际结构与计划的差异（如有）」，等我确认后再开始子计划 0。

## ===启动提示词结束===

---

## 给你（用户）的小贴士
- 每个子计划做完，把 Claude Code 的产出（改了哪些文件、测试结果）发回给我（Cowork/Opus），我帮你做代码审查再放行下一步。
- 子计划 5 的 view 提示词是系统的「灵魂」，跑通后建议用几条真实新闻试生成，看 view 的中性与专业度是否满意，再让我帮你调提示词。
- `data/config.json` 里的数据源清单和打分阈值（`min_score`）可以边用边调。
