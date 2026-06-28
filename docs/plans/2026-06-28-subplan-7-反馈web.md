# 子计划 7：Financial Market News Collector 反馈 Web（Phase 1.5）

> **致执行者：** 逐任务 TDD。前置：Phase 1（子计划 1–6）已完成。读 `docs/specs/2026-06-28-phase1.5-反馈web-设计文档.md`。

**目标：** 在现有仓库新增一个 FastAPI 反馈 Web：浏览器看每日 brief（Cartesian/Playfair 视觉、每条三层结构）、匿名收集行为埋点与 👍/👎/评论，部署到 Render 让第一批用户访问。

**架构：** FastAPI + Jinja2 服务端渲染，读写同一个 `data/marketnews.db`。复用 Phase 1 的 `Database`/Repos，新增 `EventRepo`/`FeedbackRepo`/`WebQuery`。前端少量 JS 管 `anon_id`、反馈、埋点、筛选。

**技术栈：** `fastapi`、`uvicorn`、`jinja2`、`httpx`（FastAPI TestClient 依赖）、Phase 1 的 db 层。

## Global Constraints
- Python 3.11+，沿用 `uv`。新增 Web 代码放 `src/web/`，不破坏 Phase 1。
- 一切匿名，无登录。`anon_id` 仅用于去重计数。
- 视觉严格按 spec 第 2 节（Playfair + 暖中性近单色，页头仅刊名+日期）。
- 🔒 合规不变：view 与概括均中性，无投资建议。
- 不破坏 Phase 1 的 322 个测试。

## 文件结构
- 修改 `src/db/schema.sql` + 新增 `src/db/migrate.py`（给 event/feedback 加 `anon_id`，幂等）
- 修改 `src/db/repositories/__init__` 区域：新增 `src/db/repositories/feedback_repo.py`（`EventRepo`、`FeedbackRepo`）
- 新增 `src/web/__init__.py`、`src/web/queries.py`（`WebQuery`）、`src/web/app.py`（FastAPI）、`src/web/templates/brief.html`、`src/web/static/app.js`
- 修改 `src/view/view_templates.py` + `src/view/generator.py` + `src/view/brief_assembler.py`：view 调用同时产出 `summary`
- 测试 `tests/web/`

---

## Task 1: anon_id 迁移 + EventRepo + FeedbackRepo

**Files:**
- Create: `src/db/migrate.py`
- Create: `src/db/repositories/feedback_repo.py`
- Test: `tests/web/test_feedback_repo.py`

**Interfaces:**
- `ensure_web_columns(db: Database) -> None`：对 `event`、`feedback` 执行 `ALTER TABLE ADD COLUMN anon_id TEXT`，已存在则跳过（幂等）。
- `EventRepo(db)`：`add(brief_item_id:int, type:str, anon_id:str, ts:str|None=None) -> int`
- `FeedbackRepo(db)`：
  - `add(brief_item_id:int, rating:str, anon_id:str, comment:str|None=None, ts:str|None=None) -> int`（rating ∈ {up,down}）
  - `counts(brief_item_id:int) -> dict`（返回 `{"up":n,"down":m}`）
  - `upsert_rating(...)`：同一 anon_id 对同一条只算最新一票（先删该 anon 对该条的旧 rating 再插）

- [ ] **Step 1: 写测试 `tests/web/test_feedback_repo.py`**

```python
from src.db import init_db
from src.db.migrate import ensure_web_columns
from src.db.repositories.feedback_repo import EventRepo, FeedbackRepo

def _db(tmp_path):
    db = init_db(str(tmp_path/"t.db")); ensure_web_columns(db); return db

def test_migration_idempotent(tmp_path):
    db = init_db(str(tmp_path/"t.db"))
    ensure_web_columns(db); ensure_web_columns(db)  # 跑两次不报错
    conn = db.connect()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(feedback)")}
    assert "anon_id" in cols

def test_event_add(tmp_path):
    db = _db(tmp_path)
    eid = EventRepo(db).add(brief_item_id=1, type="click", anon_id="a1")
    assert eid > 0

def test_feedback_counts_and_one_vote(tmp_path):
    db = _db(tmp_path)
    fr = FeedbackRepo(db)
    fr.upsert_rating(brief_item_id=1, rating="up", anon_id="a1")
    fr.upsert_rating(brief_item_id=1, rating="up", anon_id="a2")
    fr.upsert_rating(brief_item_id=1, rating="down", anon_id="a1")  # a1 改投
    c = fr.counts(1)
    assert c == {"up": 1, "down": 1}
```

- [ ] **Step 2: 跑测试确认失败** — `uv run pytest tests/web/test_feedback_repo.py -v`
- [ ] **Step 3: 实现 `src/db/migrate.py`**

```python
"""为 Web 反馈/埋点补列（幂等迁移）。"""
from __future__ import annotations
from .database import Database


def ensure_web_columns(db: Database) -> None:
    with db.transaction() as conn:
        for table in ("event", "feedback"):
            cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            if "anon_id" not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN anon_id TEXT")
```

- [ ] **Step 4: 实现 `src/db/repositories/feedback_repo.py`**

```python
"""event / feedback 仓储（匿名 anon_id）。"""
from __future__ import annotations
from datetime import datetime, timezone
from ..database import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventRepo:
    def __init__(self, db: Database):
        self.db = db

    def add(self, brief_item_id: int, type: str, anon_id: str, ts: str | None = None) -> int:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO event (brief_item_id, type, anon_id, ts) VALUES (?,?,?,?)",
                (brief_item_id, type, anon_id, ts or _now()),
            )
            return cur.lastrowid


class FeedbackRepo:
    def __init__(self, db: Database):
        self.db = db

    def add(self, brief_item_id: int, rating: str, anon_id: str,
            comment: str | None = None, ts: str | None = None) -> int:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO feedback (brief_item_id, rating, comment, anon_id, ts) "
                "VALUES (?,?,?,?,?)",
                (brief_item_id, _rating_to_int(rating), comment, anon_id, ts or _now()),
            )
            return cur.lastrowid

    def upsert_rating(self, brief_item_id: int, rating: str, anon_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "DELETE FROM feedback WHERE brief_item_id=? AND anon_id=? AND comment IS NULL",
                (brief_item_id, anon_id),
            )
            conn.execute(
                "INSERT INTO feedback (brief_item_id, rating, anon_id, ts) VALUES (?,?,?,?)",
                (brief_item_id, _rating_to_int(rating), anon_id, _now()),
            )

    def counts(self, brief_item_id: int) -> dict:
        conn = self.db.connect()
        try:
            up = conn.execute(
                "SELECT COUNT(*) FROM feedback WHERE brief_item_id=? AND rating=1",
                (brief_item_id,)).fetchone()[0]
            down = conn.execute(
                "SELECT COUNT(*) FROM feedback WHERE brief_item_id=? AND rating=-1",
                (brief_item_id,)).fetchone()[0]
            return {"up": up, "down": down}
        finally:
            conn.close()


def _rating_to_int(rating: str) -> int:
    return 1 if rating == "up" else -1
```

- [ ] **Step 5: 跑测试确认通过 → 提交** — `git commit -m "feat(web): anon_id migration + EventRepo/FeedbackRepo"`

---

## Task 2: view 调用同时产出"内容概括"

**Files:**
- Modify: `src/view/view_templates.py`（让 NEUTRAL 模板返回 JSON: `{summary, view}`）
- Modify: `src/view/generator.py`（解析并返回 `(summary, view)`，合规仍只对 view 强制；summary 也过一遍 is_clean）
- Modify: `src/view/brief_assembler.py`（写入 `brief_item.summary` = 模型概括）
- Test: `tests/web/test_view_summary.py`

**Interfaces:**
- `ViewGenerator.generate_item(story_id:int, title:str, raw_summary:str, context:str="") -> tuple[str,str]` 返回 `(summary, view_text)`；保留旧 `generate_item_view` 作为 `generate_item(...)[1]` 的兼容包装。
- `BriefAssembler.build(...)`：调 `generate_item`，把 `summary` 写进 `BriefItemRow.summary`，`view` 写进 `view_text`。

- [ ] **Step 1: 写测试 `tests/web/test_view_summary.py`**

```python
import asyncio, json
from src.db import init_db
from src.db.repositories.story_repo import StoryRepo
from src.db.repositories.analysis_repo import StoryTagRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.rows import StoryRow
from src.view.router import ViewRouter
from src.view.compliance import ComplianceChecker
from src.view.generator import ViewGenerator
from datetime import datetime, timezone

class FakeAI:
    async def complete(self, system, user):
        return json.dumps({"summary":"某公司宣布收购同业，待监管审批。",
                           "view":"该交易可能影响行业竞争格局与相关方估值要素。"})

def test_generate_item_returns_summary_and_view(tmp_path):
    db = init_db(str(tmp_path/"t.db")); now=datetime.now(timezone.utc).isoformat()
    sid = StoryRepo(db).create(StoryRow(canonical_title="x", first_seen_at=now, last_seen_at=now))
    gen = ViewGenerator(FakeAI(), ViewRouter(StoryTagRepo(db), TaxonomyRepo(db)), ComplianceChecker())
    summary, view = asyncio.run(gen.generate_item(sid, "Acme buys Beta", "raw", ""))
    assert "收购" in summary
    assert "竞争格局" in view
```

- [ ] **Step 2-4:** 跑测试确认失败 → 修改 `view_templates.py`（每个类型模板末尾改为要求返回 `{"summary": "...", "view": "..."}` JSON；`NEUTRAL_SYSTEM` 增加"先给一句客观 summary，再给中性 view，均不含投资建议，返回 JSON"）；`generator.py` 增加 `generate_item` 解析 JSON、分别合规处理；`brief_assembler.py` 改用 `generate_item` 并写 summary。跑测试通过。
- [ ] **Step 5: 提交** — `git commit -m "feat(view): produce neutral summary alongside view in one call"`

> 实现要点（generator.generate_item）：
> ```python
> async def generate_item(self, story_id, title, raw_summary, context=""):
>     key = self.router.route(story_id)
>     user = TEMPLATES[key].format(title=title, summary=raw_summary or "(none)", context=context or "(none)")
>     raw = await self.ai.complete(NEUTRAL_SYSTEM, user)
>     try:
>         data = json.loads(_strip_fences(raw)); summary = data.get("summary",""); view = data.get("view","")
>     except Exception:
>         summary, view = "", raw
>     if not self.compliance.is_clean(view):
>         view2 = await self.ai.complete(NEUTRAL_SYSTEM, user + _REWRITE_HINT)
>         view = view2 if self.compliance.is_clean(view2) else _strip_violating_sentences(view2, self.compliance)
>     if not self.compliance.is_clean(summary):
>         summary = _strip_violating_sentences(summary, self.compliance)
>     return summary.strip(), view.strip()
> ```

---

## Task 3: WebQuery（取某期 brief 的结构化渲染数据）

**Files:**
- Create: `src/web/__init__.py`、`src/web/queries.py`
- Test: `tests/web/test_web_query.py`

**Interfaces:**
- `WebQuery(db)`：
  - `latest_date() -> str|None`
  - `list_dates(limit=30) -> list[str]`
  - `brief_for_web(date:str) -> dict|None`：返回
    ```
    {"date":..., "market_view":..., "items":[
        {"id":bi.id,"rank":..,"headline":..,"summary":..,"view":..,"url":..,
         "tags":[{"dim":..,"code":..,"label":..}], "up":n,"down":m}]}
    ```
    （url 取 story 主 raw_item；tags 来自 story_tag→taxonomy；计数来自 FeedbackRepo）

- [ ] **Step 1: 写测试**（建一期 brief + 1 条 item + tag + raw_item url + 几条 feedback，断言 `brief_for_web` 返回结构正确、含 url/tags/up/down）。
- [ ] **Step 2-4:** 失败 → 实现（SQL join brief_item/story_member/raw_item/story_tag/taxonomy + 调 FeedbackRepo.counts）→ 通过。
- [ ] **Step 5: 提交** — `git commit -m "feat(web): WebQuery for structured brief rendering"`

---

## Task 4: FastAPI 应用 + 页面与接口

**Files:**
- Create: `src/web/app.py`
- Test: `tests/web/test_app.py`

**Interfaces（FastAPI app `create_app(db_path)` 返回 app）：**
- `GET /` → 重定向/渲染最新一期
- `GET /brief/{date}` → 渲染该期（HTML）
- `GET /api/dates` → `{"dates":[...]}`
- `POST /api/feedback` body `{brief_item_id, rating, anon_id, comment?}` → `{"up":n,"down":m}`
- `POST /api/event` body `{brief_item_id, type, anon_id}` → `{"ok":true}`

- [ ] **Step 1: 写测试 `tests/web/test_app.py`（用 `fastapi.testclient.TestClient`）**

```python
from fastapi.testclient import TestClient
from src.db import init_db
from src.db.migrate import ensure_web_columns
from src.web.app import create_app
# ... 准备一期 brief（可调用 WebQuery 测试里的建数据 helper）...

def test_feedback_endpoint(tmp_path):
    db_path = str(tmp_path/"t.db"); db = init_db(db_path); ensure_web_columns(db)
    # 建一条 brief_item id=1（略，用 BriefRepo/BriefItemRepo）
    app = create_app(db_path); client = TestClient(app)
    r = client.post("/api/feedback", json={"brief_item_id":1,"rating":"up","anon_id":"a1"})
    assert r.status_code == 200 and r.json()["up"] == 1

def test_event_endpoint(tmp_path):
    db_path = str(tmp_path/"t.db"); db = init_db(db_path); ensure_web_columns(db)
    app = create_app(db_path); client = TestClient(app)
    r = client.post("/api/event", json={"brief_item_id":1,"type":"click","anon_id":"a1"})
    assert r.status_code == 200 and r.json()["ok"] is True

def test_index_renders(tmp_path):
    db_path = str(tmp_path/"t.db"); db = init_db(db_path); ensure_web_columns(db)
    # 建一期 brief...
    app = create_app(db_path); client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert "Financial Market News Collector" in r.text
```

- [ ] **Step 2-4:** 失败 → 先 `uv add fastapi uvicorn jinja2` → 实现 `create_app`（挂载 templates/static、注入 `WebQuery`/`EventRepo`/`FeedbackRepo`）→ 通过。
- [ ] **Step 5: 提交** — `git commit -m "feat(web): FastAPI app with brief pages + feedback/event APIs"`

> `create_app` 骨架：
> ```python
> from fastapi import FastAPI, Request
> from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
> from fastapi.staticfiles import StaticFiles
> from fastapi.templating import Jinja2Templates
> from pathlib import Path
> from ..db.database import Database
> from ..db.repositories.feedback_repo import EventRepo, FeedbackRepo
> from .queries import WebQuery
> def create_app(db_path: str) -> FastAPI:
>     app = FastAPI(); base = Path(__file__).parent
>     tpl = Jinja2Templates(directory=str(base/"templates"))
>     app.mount("/static", StaticFiles(directory=str(base/"static")), name="static")
>     db = Database(db_path)
>     @app.get("/", response_class=HTMLResponse)
>     def index(request: Request):
>         d = WebQuery(db).latest_date()
>         return RedirectResponse(f"/brief/{d}") if d else tpl.TemplateResponse("brief.html", {"request":request,"brief":None,"dates":[]})
>     @app.get("/brief/{date}", response_class=HTMLResponse)
>     def brief(request: Request, date: str):
>         q = WebQuery(db)
>         return tpl.TemplateResponse("brief.html", {"request":request,"brief":q.brief_for_web(date),"dates":q.list_dates()})
>     @app.post("/api/feedback")
>     async def feedback(request: Request):
>         b = await request.json(); fr = FeedbackRepo(db)
>         fr.upsert_rating(b["brief_item_id"], b["rating"], b["anon_id"])
>         if b.get("comment"): fr.add(b["brief_item_id"], b["rating"], b["anon_id"], comment=b["comment"])
>         return JSONResponse(fr.counts(b["brief_item_id"]))
>     @app.post("/api/event")
>     async def event(request: Request):
>         b = await request.json(); EventRepo(db).add(b["brief_item_id"], b["type"], b["anon_id"])
>         return JSONResponse({"ok": True})
>     return app
> ```

---

## Task 5: Jinja2 模板（Cartesian 视觉）+ 前端 JS

**Files:**
- Create: `src/web/templates/brief.html`
- Create: `src/web/static/app.js`
- Test: `tests/web/test_template_render.py`（断言渲染出标题/概括/view/原文链接/免责声明/筛选 chips）

**实现 `brief.html`（完整，按 spec 视觉规范；缺数据时显示空态）：**

```html
<!doctype html><html lang="zh"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Financial Market News Collector</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&family=Work+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#f3f1ea;--card:#faf8f2;--ink:#1a1a1a;--muted:#6b665d;--faint:#8a8275;--hair:#d9d4c8;--chip:#e9e5da}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:'Work Sans',sans-serif;line-height:1.6}
.wrap{max-width:720px;margin:0 auto;padding:34px 22px 60px}
.mast{font-family:'Playfair Display',serif;font-weight:600;font-size:30px;line-height:1.1}
.date{font-size:13px;color:var(--faint);margin-top:8px}
.rule{height:1px;background:var(--ink);margin:12px 0 0}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0 4px}
.chip{font-size:13px;padding:5px 13px;border-radius:20px;border:0.5px solid var(--hair);color:var(--muted);background:var(--card);cursor:pointer}
.chip.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.h{font-family:'Playfair Display',serif;font-size:17px;font-weight:600;margin:26px 0 8px;display:flex;align-items:center;gap:8px}
.h::before{content:'';width:5px;height:5px;border-radius:50%;background:var(--ink)}
.lead{font-family:'Playfair Display',serif;font-size:18px;font-style:italic;line-height:1.55;color:#2a2620}
.item{padding:18px 0;border-bottom:0.5px solid var(--hair)}
.itop{display:flex;justify-content:space-between;gap:12px;align-items:baseline}
.title{font-family:'Playfair Display',serif;font-size:19px;font-weight:500;line-height:1.3}
.rank{color:var(--faint)}
.src{font-size:13px;color:var(--ink);border-bottom:1px solid var(--ink);white-space:nowrap;text-decoration:none}
.sum{font-size:14.5px;color:var(--muted);margin:7px 0 2px}
.tags{margin:9px 0}
.tag{font-size:12px;color:var(--muted);background:var(--chip);border-radius:4px;padding:2px 9px;margin-right:6px}
.view{font-size:15px;line-height:1.65;background:var(--card);border:0.5px solid var(--hair);border-radius:8px;padding:11px 14px;margin:10px 0}
.view b{font-family:'Playfair Display',serif;font-style:italic;font-weight:500}
.fb{display:flex;gap:18px;font-size:14px;color:var(--faint);align-items:center}
.fb button{background:none;border:none;color:inherit;font:inherit;cursor:pointer;display:inline-flex;gap:5px;align-items:center;padding:0}
.fb button.act{color:var(--ink)}
.cbox{display:none;margin-top:8px}
.cbox textarea{width:100%;font:inherit;border:0.5px solid var(--hair);border-radius:8px;padding:8px;background:var(--card);resize:vertical}
.foot{font-size:13px;color:var(--faint);font-style:italic;border-top:0.5px solid var(--hair);margin-top:16px;padding-top:14px}
.nav{margin-top:18px;font-size:13px}.nav a{color:var(--ink);margin-right:12px}
</style></head><body>
<div class="wrap">
{% if not brief %}
  <div class="mast">Financial Market News Collector</div><div class="rule"></div>
  <p class="sum" style="margin-top:18px">暂无 brief。等首期生成后这里会显示。</p>
{% else %}
  <div class="mast">Financial Market News Collector</div>
  <div class="date">{{ brief.date }}</div>
  <div class="rule"></div>
  <div class="chips" id="chips">
    <span class="chip on" data-f="all">全部</span>
    {% for f in brief.filters %}<span class="chip" data-f="{{ f.code }}">{{ f.label }}</span>{% endfor %}
  </div>
  {% if brief.market_view %}<div class="h">综合市场观点</div><div class="lead">{{ brief.market_view }}</div>{% endif %}
  <div class="h">今日要闻</div>
  {% for it in brief.items %}
  <div class="item" data-tags="{{ it.tagcodes }}" data-id="{{ it.id }}">
    <div class="itop">
      <div class="title"><span class="rank">{{ '%02d'|format(it.rank) }} — </span>{{ it.headline }}</div>
      {% if it.url %}<a class="src" href="{{ it.url }}" target="_blank" rel="noopener" data-click="{{ it.id }}">原文 ↗</a>{% endif %}
    </div>
    {% if it.summary %}<div class="sum">{{ it.summary }}</div>{% endif %}
    <div class="tags">{% for t in it.tags %}<span class="tag">{{ t.label }}</span>{% endfor %}</div>
    <div class="view"><b>影响（中性）：</b>{{ it.view }}</div>
    <div class="fb">
      <button data-vote="up" data-id="{{ it.id }}"><i class="ti ti-thumb-up"></i> <span>{{ it.up }}</span></button>
      <button data-vote="down" data-id="{{ it.id }}"><i class="ti ti-thumb-down"></i> <span>{{ it.down }}</span></button>
      <button data-comment="{{ it.id }}"><i class="ti ti-message-circle"></i> 评论</button>
    </div>
    <div class="cbox" id="cbox-{{ it.id }}"><textarea rows="2" placeholder="写下你的看法…"></textarea>
      <button data-send="{{ it.id }}" style="margin-top:6px;font:inherit;cursor:pointer">提交</button></div>
  </div>
  {% endfor %}
  <div class="foot">免责声明：本内容为公开信息汇总与中性影响陈述，不构成任何投资建议、买卖推荐或目标价。</div>
  <div class="nav">历史：{% for d in dates %}<a href="/brief/{{ d }}">{{ d }}</a>{% endfor %}</div>
{% endif %}
</div>
<link href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2/tabler-icons.min.css" rel="stylesheet">
<script src="/static/app.js"></script>
</body></html>
```

**实现 `static/app.js`（anon_id + 投票 + 评论 + 点击/浏览埋点 + 筛选）：**

```javascript
function anonId(){let id=localStorage.getItem('fmnc_anon');if(!id){id='a-'+Math.random().toString(36).slice(2)+Date.now().toString(36);localStorage.setItem('fmnc_anon',id);}return id;}
const ANON=anonId();
async function post(url,body){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.ok?r.json():null;}
document.querySelectorAll('[data-vote]').forEach(b=>b.addEventListener('click',async()=>{
  const id=+b.dataset.id,rating=b.dataset.vote;const res=await post('/api/feedback',{brief_item_id:id,rating,anon_id:ANON});
  if(res){const item=b.closest('.item');item.querySelector('[data-vote=up] span').textContent=res.up;item.querySelector('[data-vote=down] span').textContent=res.down;
    item.querySelectorAll('[data-vote]').forEach(x=>x.classList.remove('act'));b.classList.add('act');}}));
document.querySelectorAll('[data-comment]').forEach(b=>b.addEventListener('click',()=>{const box=document.getElementById('cbox-'+b.dataset.comment);box.style.display=box.style.display==='block'?'none':'block';}));
document.querySelectorAll('[data-send]').forEach(b=>b.addEventListener('click',async()=>{const id=+b.dataset.send;const ta=b.parentElement.querySelector('textarea');if(!ta.value.trim())return;await post('/api/feedback',{brief_item_id:id,rating:'up',anon_id:ANON,comment:ta.value.trim()});ta.value='';b.parentElement.style.display='none';}));
document.querySelectorAll('[data-click]').forEach(a=>a.addEventListener('click',()=>post('/api/event',{brief_item_id:+a.dataset.click,type:'click',anon_id:ANON})));
const seen=new Set();const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){const id=+e.target.dataset.id;if(!seen.has(id)){seen.add(id);post('/api/event',{brief_item_id:id,type:'view',anon_id:ANON});}}}),{threshold:0.5});
document.querySelectorAll('.item').forEach(el=>io.observe(el));
const chips=document.getElementById('chips');if(chips)chips.addEventListener('click',e=>{if(!e.target.dataset.f)return;chips.querySelectorAll('.chip').forEach(c=>c.classList.remove('on'));e.target.classList.add('on');const f=e.target.dataset.f;
  document.querySelectorAll('.item').forEach(it=>{it.style.display=(f==='all'||(it.dataset.tags||'').split(',').includes(f))?'':'none';});});
```

- [ ] **Step 1-5:** 写模板渲染测试（`test_index_renders` 已覆盖大部分，再加断言含"影响（中性）"、"原文"、"免责声明"）→ 实现模板与 app.js → 跑通 → 提交 `git commit -m "feat(web): Cartesian-styled brief template + feedback/event frontend"`。

---

## Task 6: 运行与部署（Render）

**Files:**
- Create: `render.yaml`
- Create: `src/web/run.py`（`uvicorn` 本地启动入口）
- Modify: `README` 增加 Web 运行/部署说明

- [ ] **Step 1: 本地启动入口 `src/web/run.py`**

```python
import uvicorn
from .app import create_app
app = create_app("data/marketnews.db")
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
本地自测：`uv run python -m src.web.run` → 浏览器开 `http://localhost:8000`。

- [ ] **Step 2: `render.yaml`（Web Service + 持久化磁盘 + 每日 Cron）**

```yaml
services:
  - type: web
    name: fmnc-web
    env: python
    buildCommand: "pip install uv && uv sync"
    startCommand: "uv run uvicorn src.web.app:create_app --factory --host 0.0.0.0 --port $PORT"
    disk:
      name: fmnc-data
      mountPath: /opt/render/project/src/data
      sizeGB: 1
    envVars:
      - key: DEEPSEEK_API_KEY
        sync: false
  - type: cron
    name: fmnc-daily
    env: python
    schedule: "0 0 * * *"
    buildCommand: "pip install uv && uv sync"
    startCommand: "uv run horizon --marketnews --hours 24"
    disk:
      name: fmnc-data
      mountPath: /opt/render/project/src/data
      sizeGB: 1
```

> 注意：Web Service 与 Cron 共享同一持久化磁盘上的 `data/marketnews.db`。`create_app` 的 db 路径在 Render 上指向挂载盘。`DEEPSEEK_API_KEY` 在 Render 后台填，不进 git。

- [ ] **Step 3: 提交** — `git commit -m "feat(web): local run entry + Render deploy config"`

---

## 自检
- 覆盖 spec：三层内容结构、Cartesian 视觉、匿名埋点+反馈、筛选、历史、免责声明、部署。✔
- 合规不变：view 与 summary 均过 ComplianceChecker。✔
- 不破坏 Phase 1：新增代码在 `src/web/`、新增列用幂等迁移、不改 Phase 1 表语义。✔
- 接口 `EventRepo`/`FeedbackRepo`/`WebQuery`/`create_app` 命名一致。✔

## 上线后下一步（运营）
- 看 `feedback`/`event` 数据：哪些 view 被踩多/评论多 → 回头让我帮你调 view 提示词。
- 第一批用户反馈攒够了，再决定要不要进 Phase 2（账户/个性化/商业化）。
