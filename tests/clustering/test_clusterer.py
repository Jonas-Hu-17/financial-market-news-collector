"""Task 3: StoryClusterer 跨天聚类 + 状态机测试（用假 embedding 注入，不下模型）。"""
from datetime import datetime, timezone, timedelta
from src.db import init_db
from src.db.repositories.raw_item_repo import RawItemRepo
from src.db.repositories.story_repo import StoryRepo, StoryMemberRepo
from src.db.rows import RawItemRow
from src.embedding.vector_store import VectorStore
from src.clustering.clusterer import StoryClusterer


class FakeEmb:
    def __init__(self, mapping):
        self.mapping = mapping

    def embed_one(self, text):
        v = self.mapping[text.strip()]
        return list(v) + [0.0] * (384 - len(v))


def _item(repo, title, key):
    r = RawItemRow(
        title=title, summary="",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        dedup_key=key,
    )
    rid, _ = repo.upsert(r)
    r.id = rid
    return r


def test_similar_item_joins_existing_story(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    ri = RawItemRepo(db)
    emb = FakeEmb({"Acme buys Beta": (1, 0, 0), "Acme to acquire Beta": (0.98, 0.02, 0)})
    cl = StoryClusterer(
        emb, VectorStore(db), StoryRepo(db), StoryMemberRepo(db),
        similarity_threshold=0.8, lookback_days=7,
    )
    sid1, new1 = cl.assign(_item(ri, "Acme buys Beta", "k1"))
    sid2, new2 = cl.assign(_item(ri, "Acme to acquire Beta", "k2"))
    assert new1 is True and new2 is False and sid1 == sid2


def test_unrelated_item_makes_new_story(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    ri = RawItemRepo(db)
    emb = FakeEmb({"Acme buys Beta": (1, 0, 0), "Fed holds rates": (0, 1, 0)})
    cl = StoryClusterer(
        emb, VectorStore(db), StoryRepo(db), StoryMemberRepo(db),
        similarity_threshold=0.8, lookback_days=7,
    )
    sid1, _ = cl.assign(_item(ri, "Acme buys Beta", "k1"))
    sid2, new2 = cl.assign(_item(ri, "Fed holds rates", "k2"))
    assert new2 is True and sid1 != sid2


def test_assign_with_vec_uses_precomputed_vector(tmp_path):
    """assign(row, vec=...) should use passed vector, not call embed_one."""
    db = init_db(str(tmp_path / "t.db"))
    ri = RawItemRepo(db)

    # 用 FakeEmb 但记录 embed_one 调用次数来确认未调用
    class CountingFakeEmb:
        def __init__(self, mapping):
            self.mapping = mapping
            self.embed_one_calls = 0

        def embed_one(self, text):
            self.embed_one_calls += 1
            v = self.mapping[text.strip()]
            return list(v) + [0.0] * (384 - len(v))

    emb = CountingFakeEmb({"Acme buys Beta": (1, 0, 0)})
    cl = StoryClusterer(
        emb, VectorStore(db), StoryRepo(db), StoryMemberRepo(db),
        similarity_threshold=0.8, lookback_days=7,
    )

    precomputed = [0.5] * 384
    item = _item(ri, "Acme buys Beta", "k_test")
    sid, is_new = cl.assign(item, vec=precomputed)

    # 核心断言：传入 vec 后不应调用 embed_one
    assert emb.embed_one_calls == 0, (
        f"Expected embed_one to NOT be called when vec is provided, "
        f"but got {emb.embed_one_calls} calls"
    )
    assert is_new is True
    assert sid > 0

    # 第二个相似 item 用 precomputed vec 也应归入同一 story
    precomputed_similar = [0.48] * 384  # close enough to [0.5]
    item2 = _item(ri, "Another title", "k_test2")
    sid2, is_new2 = cl.assign(item2, vec=precomputed_similar)
    # With cosine threshold of 0.8, same-direction vectors should match
    assert emb.embed_one_calls == 0  # still not called
    assert is_new2 is False
    assert sid2 == sid
