"""Task 2: VectorStore 测试 — sqlite-vec 向量表写入与 KNN 查询。"""
from src.db import init_db
from src.embedding.vector_store import VectorStore


def _v(*xs):
    """构建 384 维向量，前 len(xs) 分量为传入值，其余为 0。"""
    return list(xs) + [0.0] * (384 - len(xs))


def test_add_and_knn(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    vs = VectorStore(db)
    vs.add(1, _v(1, 0, 0))
    vs.add(2, _v(0, 1, 0))
    vs.add(3, _v(0.9, 0.1, 0))
    res = vs.knn(_v(1, 0, 0), k=2)
    ids = [r[0] for r in res]
    assert ids[0] == 1 and 3 in ids


def test_knn_respects_allowed_ids(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    vs = VectorStore(db)
    vs.add(1, _v(1, 0, 0))
    vs.add(2, _v(0.95, 0.05, 0))
    res = vs.knn(_v(1, 0, 0), k=5, allowed_ids={2})
    assert [r[0] for r in res] == [2]
