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
