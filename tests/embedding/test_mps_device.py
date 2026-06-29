"""Task D: 测试 EmbeddingService 使用 MPS 设备（Apple Silicon GPU 加速）。"""
import torch
from src.embedding.service import EmbeddingService


def test_mps_device_is_used_when_available(monkeypatch):
    """当 torch.backends.mps.is_available() 返回 True 时，模型加载到 mps 设备。"""
    captured_kwargs = {}

    # 拦截 SentenceTransformer 构造，避免实际下载模型
    import sentence_transformers as st_mod
    original_init = st_mod.SentenceTransformer.__init__

    def fake_init(self, model_name, *args, **kwargs):
        captured_kwargs["device"] = kwargs.get("device", "cpu")
        # 不调用 original_init（会下载模型），返回 None 表示成功

    monkeypatch.setattr(st_mod.SentenceTransformer, "__init__", fake_init)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)

    svc = EmbeddingService()
    try:
        _ = svc._model
    except Exception:
        pass

    assert captured_kwargs.get("device") == "mps", (
        f"Expected device='mps' when MPS is available, "
        f"got {captured_kwargs.get('device')!r}"
    )


def test_fallback_to_cpu_when_mps_unavailable(monkeypatch):
    """当 MPS 不可用时回退到 CPU。"""
    captured_kwargs = {}

    import sentence_transformers as st_mod

    def fake_init(self, model_name, *args, **kwargs):
        captured_kwargs["device"] = kwargs.get("device", "cpu")

    monkeypatch.setattr(st_mod.SentenceTransformer, "__init__", fake_init)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)

    svc = EmbeddingService()
    try:
        _ = svc._model
    except Exception:
        pass

    assert captured_kwargs.get("device") == "cpu", (
        f"Expected fallback to 'cpu', got {captured_kwargs.get('device')!r}"
    )
