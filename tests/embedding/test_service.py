"""Task 1: EmbeddingService 测试（首次运行会下载 paraphrase-multilingual-MiniLM-L12-v2 模型）。"""
import math
from src.embedding.service import EmbeddingService


def test_embed_dim_and_normalized():
    svc = EmbeddingService()
    vecs = svc.embed(["Acme acquires Beta", "美联储维持利率不变"])
    assert len(vecs) == 2 and len(vecs[0]) == 384
    norm = math.sqrt(sum(x * x for x in vecs[0]))
    assert abs(norm - 1.0) < 1e-3   # 已归一化


def test_similar_texts_closer():
    svc = EmbeddingService()
    a, b, c = svc.embed([
        "Acme acquires Beta Corp in $2bn deal",
        "Acme to buy Beta Corporation for 2 billion",
        "Fed holds interest rates steady",
    ])

    def cos(x, y):
        return sum(i * j for i, j in zip(x, y))

    assert cos(a, b) > cos(a, c)
