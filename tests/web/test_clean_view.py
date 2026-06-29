"""测试 _clean_view 对各种 JSON 残渣的清洗能力。"""
from src.web.queries import _clean_view


class TestCleanView:
    def test_normal_chinese_passthrough(self):
        """正常中文 view 原样返回，不误伤。"""
        assert _clean_view("该并购将整合市场资源，提升行业集中度。") == \
               "该并购将整合市场资源，提升行业集中度。"
        assert _clean_view("中性影响：对行业格局无明显改变。") == \
               "中性影响：对行业格局无明显改变。"

    def test_normal_english_passthrough(self):
        """正常英文 view 原样返回。"""
        assert _clean_view("The acquisition may reshape the competitive landscape.") == \
               "The acquisition may reshape the competitive landscape."

    def test_empty_and_whitespace(self):
        """空/空白字符串原样返回。"""
        assert _clean_view("") == ""
        assert _clean_view("   ") == ""

    def test_trailing_view_json_fragment(self):
        """", "view": "正文"}}  → 得"正文"。"""
        assert _clean_view('", "view": "该并购将整合市场资源"}}') == \
               "该并购将整合市场资源"

    def test_full_json_object_with_view(self):
        """{"summary": "...", "view": "..."} → 提取 view 值。"""
        result = _clean_view(
            '{"summary": "据媒体报道，Acme宣布收购Beta。", '
            '"view": "该并购将整合市场资源。"}')
        assert result == "该并购将整合市场资源。"

    def test_summary_prefix_leak(self):
        """summary": "正文 → 得"正文"。"""
        assert _clean_view('summary": "据媒体报道，Acme宣布收购Beta。') == \
               "据媒体报道，Acme宣布收购Beta。"

    def test_summary_colon_space_prefix(self):
        """summary": 无前导引号的正文 → 去掉前缀。"""
        result = _clean_view('summary": 据媒体报道，Acme宣布收购Beta。')
        assert "据媒体报道" in result
        assert 'summary"' not in result

    def test_quoted_summary_prefix(self):
        """"summary": "正文" → 得"正文"。"""
        assert _clean_view('"summary": "据媒体报道，Acme宣布收购Beta。"') == \
               "据媒体报道，Acme宣布收购Beta。"

    def test_full_json_summary_view_both(self):
        """{"summary": "S", "view": "V"} → 优先提取 view。"""
        result = _clean_view(
            '{"summary": "摘要内容", "view": "中性影响陈述"}')
        assert result == "中性影响陈述"

    def test_json_with_newlines(self):
        """多行 JSON 残渣也能清洗。"""
        result = _clean_view(
            '{\n"summary": "摘要内容",\n"view": "中性影响陈述"\n}')
        assert result == "中性影响陈述"

    def test_bare_braces_and_quotes_stripped(self):
        """开头有 {、"、, 等字符，无明确字段名时兜底 strip。"""
        # 这种垃圾文本只 strip 前导/后缀 JSON 符号
        assert _clean_view('{"该并购利好市场"}') == "该并购利好市场"
        # 但要注意不能误伤正常文本的引号

    def test_mixed_chinese_with_json_noise(self):
        """中文正文后面跟了 JSON 残渣。"""
        # 实际场景：正文在前，后面跟了 JSON 碎片
        result = _clean_view(
            '中性影响陈述", "view": "该并购将整合资源"}}')
        assert result == "该并购将整合资源"
