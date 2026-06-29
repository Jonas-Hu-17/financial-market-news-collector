"""一键静态导出：data.json（全部历史） + 零服务器客户端看板 index.html。

用法:  python -m src.web.static_export [--out site]
"""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path

from ..db.database import Database
from .queries import WebQuery

_TEMPLATE = (Path(__file__).parent / "templates" / "static_index.html").read_text(
    encoding="utf-8")


def export(out_dir: str = "site") -> tuple[Path, Path]:
    """导出 data.json + index.html 到 out_dir，返回生成的路径。"""
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)

    db = Database("data/marketnews.db")
    wq = WebQuery(db)
    data = wq.export_all()

    data_path = dest / "data.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    html_path = dest / "index.html"
    html_path.write_text(_TEMPLATE, encoding="utf-8")

    return data_path, html_path


def main() -> None:
    p = argparse.ArgumentParser(description="Static export for Financial Market News")
    p.add_argument("--out", default="site", help="output directory (default: site)")
    args = p.parse_args()
    dp, hp = export(args.out)
    print(f"  data.json  -> {dp}")
    print(f"  index.html -> {hp}")
    print(f"Done. Open {hp} in your browser.")


if __name__ == "__main__":
    main()
