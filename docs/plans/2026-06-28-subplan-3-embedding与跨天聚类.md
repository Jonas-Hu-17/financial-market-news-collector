# 子计划 3：本地 embedding + 跨天 story 聚类

> **致执行者：** 逐任务 TDD。前置：子计划 1、2 完成。

**目标：** 用本地免费 embedding 把 `raw_item` 向量化存入 sqlite-vec；实现跨天 story 聚类——新 item 与最近 N 天的 story 比相似度，命中则挂为该 story 的「更新」（`status=updated`），否则建新 story。这样同一事件的后续报道不会重复进入昂贵的打分/view 步骤。

**架构：** `EmbeddingService` 用 `sentence-transformers`（384 维，多语言）批量编码，懒加载模型。向量写入 `vec_raw_item`（rowid = raw_item.id）。`StoryClusterer` 对一条 raw_item：编码 → 在最近 N 天 raw_item 的向量里 KNN 检索 → 取最近邻所属 story → 若相似度≥阈值则归入该 story 并标记 updated，否则新建 story。阈值与回溯窗口可配置。

**技术栈：** `sentence-transformers`、`numpy`、sqlite-vec、子计划1 的 `StoryRepo`/`StoryMemberRepo`/`RawItemRepo`。

## Global Constraints
（同索引。）embedding 本地零成本；相似度用余弦（sqlite-vec 距离）；模型维度 384 与 `Database.EMBEDDING_DIM` 一致。

## 文件结构
- 创建 `src/embedding/__init__.py`
- 创建 `src/embedding/service.py` — `EmbeddingService`
- 创建 `src/embedding/vector_store.py` — 对 `vec_raw_item` 的写入与 KNN 查询封装
- 创建 `src/clustering/__init__.py`
- 创建 `src/clustering/clusterer.py` — `StoryClusterer`
- 测试 `tests/embedding/`、`tests/clustering/`

---

## Task 1: EmbeddingService

**Files:**
- Create: `src/embedding/service.py`
- Test: `tests/embedding/test_service.py`

**Interfaces:**
- Produces:
  - `EmbeddingService(model_name: str = "paraphrase-multilingual-MiniLM-L12-v2")`
  - `embed(texts: list[str]) -> list[list[float]]`（返回 L2 归一化向量，长度=384）
  - `embed_one(text: str) -> list[float]`

- [ ] **Step 1: 写测试 `tests/embedding/test_service.py`**

```python
import math
from src.embedding.service import EmbeddingService

def test_embed_dim_and_normalized():
    svc = EmbeddingService()
    vecs = svc.embed(["Acme acquires Beta", "美联储维持利率不变"])
    assert len(vecs) == 2 and len(vecs[0]) == 384
    norm = math.sqrt(sum(x*x for x in vecs[0]))
    assert abs(norm - 1.0) < 1e-3   # 已归一化

def test_similar_texts_closer():
    svc = EmbeddingService()
    a, b, c = svc.embed([
        "Acme acquires Beta Corp in $2bn deal",
        "Acme to buy Beta Corporation for 2 billion",
        "Fed holds interest rates steady",
    ])
    cos = lambda x, y: sum(i*j for i,j in zip(x,y))
    assert cos(a, b) > cos(a, c)
```

- [ ] **Step 2: 跑测试确认失败**（先 `uv add sentence-transformers numpy`）
- [ ] **Step 3: 实现 `src/embedding/service.py`**

```python
"""本地 embedding 服务（sentence-transformers，多语言，384 维）。"""
from __future__ import annotations
from functools import cached_property


class EmbeddingService:
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name

    @cached_property
    def _model(self):
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(self.model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        arr = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True)
        return [row.tolist() for row in arr]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
```

- [ ] **Step 4: 跑测试确认通过**（首次会下载模型）
- [ ] **Step 5: 提交** — `git commit -m "feat(embedding): local sentence-transformers service"`

---

## Task 2: VectorStore（写入 + KNN）

**Files:**
- Create: `src/embedding/vector_store.py`
- Test: `tests/embedding/test_vector_store.py`

**Interfaces:**
- Consumes: `Database`
- Produces:
  - `VectorStore(db: Database)`
  - `add(raw_item_id: int, vector: list[float]) -> None`（写入 `vec_raw_item`，rowid=raw_item_id；幂等：先 delete 同 rowid 再 insert）
  - `knn(vector: list[float], k: int, allowed_ids: set[int]|None=None) -> list[tuple[int, float]]`（返回 `(raw_item_id, distance)`，可按 allowed_ids 过滤为最近 N 天集合）

- [ ] **Step 1: 写测试 `tests/embedding/test_vector_store.py`**

```python
from src.db import init_db
from src.embedding.vector_store import VectorStore

def _v(*xs):
    return list(xs) + [0.0]*(384-len(xs))

def test_add_and_knn(tmp_path):
    db = init_db(str(tmp_path/"t.db"))
    vs = VectorStore(db)
    vs.add(1, _v(1,0,0)); vs.add(2, _v(0,1,0)); vs.add(3, _v(0.9,0.1,0))
    res = vs.knn(_v(1,0,0), k=2)
    ids = [r[0] for r in res]
    assert ids[0] == 1 and 3 in ids

def test_knn_respects_allowed_ids(tmp_path):
    db = init_db(str(tmp_path/"t.db"))
    vs = VectorStore(db)
    vs.add(1,_v(1,0,0)); vs.add(2,_v(0.95,0.05,0))
    res = vs.knn(_v(1,0,0), k=5, allowed_ids={2})
    assert [r[0] for r in res] == [2]
```

- [ ] **Step 2: 跑测试确认失败**
- [ ] **Step 3: 实现 `src/embedding/vector_store.py`**

```python
"""sqlite-vec 向量表读写封装。"""
from __future__ import annotations
import struct
from typing import Optional
from ..db.database import Database


def _pack(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


class VectorStore:
    def __init__(self, db: Database):
        self.db = db

    def add(self, raw_item_id: int, vector: list[float]) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM vec_raw_item WHERE rowid=?", (raw_item_id,))
            conn.execute(
                "INSERT INTO vec_raw_item(rowid, embedding) VALUES (?, ?)",
                (raw_item_id, _pack(vector)),
            )

    def knn(self, vector: list[float], k: int,
            allowed_ids: Optional[set[int]] = None) -> list[tuple[int, float]]:
        conn = self.db.connect()
        try:
            rows = conn.execute(
                "SELECT rowid, distance FROM vec_raw_item "
                "WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
                (_pack(vector), k if allowed_ids is None else max(k, 50)),
            ).fetchall()
            out = [(r["rowid"], r["distance"]) for r in rows]
            if allowed_ids is not None:
                out = [t for t in out if t[0] in allowed_ids]
            return out[:k]
        finally:
            conn.close()
```

- [ ] **Step 4: 跑测试确认通过**
- [ ] **Step 5: 提交** — `git commit -m "feat(embedding): sqlite-vec VectorStore add+knn"`

---

## Task 3: StoryClusterer（跨天聚类 + 状态机）

**Files:**
- Create: `src/clustering/clusterer.py`
- Test: `tests/clustering/test_clusterer.py`

**Interfaces:**
- Consumes: `EmbeddingService`、`VectorStore`、`RawItemRepo`、`StoryRepo`、`StoryMemberRepo`
- Produces:
  - `StoryClusterer(embedding, vector_store, story_repo, member_repo, *, similarity_threshold=0.82, lookback_days=7)`
  - `assign(raw_item: RawItemRow) -> tuple[int, bool]`：编码 title+summary → 写向量 → 在最近 `lookback_days` 的 raw_item 集合里 KNN → 命中(余弦≥阈值)取其 story 并 `update_status(updated)`、加 member（非 primary）、返回 `(story_id, False)`；否则新建 story（primary member）返回 `(story_id, True)`。
  - 注：sqlite-vec 距离为 L2；归一化向量下 `cos = 1 - dist^2/2`，阈值换算在实现内处理。

- [ ] **Step 1: 写测试 `tests/clustering/test_clusterer.py`**（用假的 embedding 注入，避免下载模型）

```python
from datetime import datetime, timezone, timedelta
from src.db import init_db
from src.db.repositories.raw_item_repo import RawItemRepo
from src.db.repositories.story_repo import StoryRepo, StoryMemberRepo
from src.db.rows import RawItemRow
from src.embedding.vector_store import VectorStore
from src.clustering.clusterer import StoryClusterer

class FakeEmb:
    def __init__(self, mapping): self.mapping = mapping
    def embed_one(self, text):
        v = self.mapping[text]
        return list(v) + [0.0]*(384-len(v))

def _item(repo, title, key):
    r = RawItemRow(title=title, summary="", fetched_at=datetime.now(timezone.utc).isoformat(), dedup_key=key)
    rid, _ = repo.upsert(r); r.id = rid
    return r

def test_similar_item_joins_existing_story(tmp_path):
    db = init_db(str(tmp_path/"t.db"))
    ri = RawItemRepo(db)
    emb = FakeEmb({"Acme buys Beta":(1,0,0), "Acme to acquire Beta":(0.98,0.02,0)})
    cl = StoryClusterer(emb, VectorStore(db), StoryRepo(db), StoryMemberRepo(db),
                        similarity_threshold=0.8, lookback_days=7)
    sid1, new1 = cl.assign(_item(ri,"Acme buys Beta","k1"))
    sid2, new2 = cl.assign(_item(ri,"Acme to acquire Beta","k2"))
    assert new1 is True and new2 is False and sid1 == sid2

def test_unrelated_item_makes_new_story(tmp_path):
    db = init_db(str(tmp_path/"t.db"))
    ri = RawItemRepo(db)
    emb = FakeEmb({"Acme buys Beta":(1,0,0), "Fed holds rates":(0,1,0)})
    cl = StoryClusterer(emb, VectorStore(db), StoryRepo(db), StoryMemberRepo(db),
                        similarity_threshold=0.8, lookback_days=7)
    sid1, _ = cl.assign(_item(ri,"Acme buys Beta","k1"))
    sid2, new2 = cl.assign(_item(ri,"Fed holds rates","k2"))
    assert new2 is True and sid1 != sid2
```

- [ ] **Step 2: 跑测试确认失败**
- [ ] **Step 3: 实现 `src/clustering/clusterer.py`**

```python
"""跨天 story 聚类：相似归入已有 story（标记 updated），否则新建。"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from ..db.rows import RawItemRow, StoryRow


class StoryClusterer:
    def __init__(self, embedding, vector_store, story_repo, member_repo,
                 *, similarity_threshold: float = 0.82, lookback_days: int = 7):
        self.embedding = embedding
        self.vs = vector_store
        self.stories = story_repo
        self.members = member_repo
        self.threshold = similarity_threshold
        self.lookback_days = lookback_days

    def assign(self, raw_item: RawItemRow) -> tuple[int, bool]:
        text = f"{raw_item.title}\n{raw_item.summary or ''}"
        vec = self.embedding.embed_one(text)
        self.vs.add(raw_item.id, vec)

        since = (datetime.now(timezone.utc) - timedelta(days=self.lookback_days)).isoformat()
        recent_ids = {rid for rid in self._recent_member_item_ids(since)
                      if rid != raw_item.id}
        now = datetime.now(timezone.utc).isoformat()

        if recent_ids:
            neighbors = self.vs.knn(vec, k=3, allowed_ids=recent_ids)
            for nid, dist in neighbors:
                cos = 1.0 - (dist * dist) / 2.0   # 归一化向量 L2→cos
                if cos >= self.threshold:
                    story_id = self._story_of_item(nid)
                    if story_id is not None:
                        self.members.add(story_id, raw_item.id, is_primary=False)
                        self.stories.update_status(story_id, "updated", now)
                        return story_id, False

        new_id = self.stories.create(StoryRow(
            canonical_title=raw_item.title, first_seen_at=now,
            last_seen_at=now, last_update_at=now, status="new"))
        self.members.add(new_id, raw_item.id, is_primary=True)
        return new_id, True

    def _recent_member_item_ids(self, since_iso: str) -> list[int]:
        out = []
        for s in self.stories.recent(since_iso):
            out.extend(self.members.raw_items_for_story(s.id))
        return out

    def _story_of_item(self, raw_item_id: int):
        for s in self.stories.recent("0000"):  # 全量回看映射；小数据量可接受
            if raw_item_id in self.members.raw_items_for_story(s.id):
                return s.id
        return None
```

> 性能注：`_story_of_item` 的线性回看仅适用于个人版数据量；产品化时改为 `story_member` 上加 `raw_item_id` 索引并直接反查（子计划6/Phase2 优化）。

- [ ] **Step 4: 跑测试确认通过**
- [ ] **Step 5: 提交** — `git commit -m "feat(clustering): cross-day story clusterer with status machine"`

---

## 自检
- 覆盖设计文档第 6 节第 2(B) 步（跨天语义聚类）、第 5 节 story.status、raw_item 向量化。✔
- 相似事件不重复建 story → 后续打分/view 不重复跑（省 token）。✔
- 阈值/窗口可配置；测试用假 embedding 注入，不依赖模型下载。✔
- 接口 `EmbeddingService.embed/embed_one`、`StoryClusterer.assign` 与计划索引一致。✔
