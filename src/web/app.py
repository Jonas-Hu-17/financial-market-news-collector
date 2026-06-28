"""FastAPI 反馈 Web：浏览 brief + 匿名反馈/埋点 API。"""
from __future__ import annotations
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..db.database import Database
from ..db.repositories.feedback_repo import EventRepo, FeedbackRepo
from .queries import WebQuery


def create_app(db_path: str = "data/marketnews.db") -> FastAPI:
    app = FastAPI()
    base = Path(__file__).parent
    tpl = Jinja2Templates(directory=str(base / "templates"))
    static_dir = base / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)),
                  name="static")
    db = Database(db_path)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        q = WebQuery(db)
        d = q.latest_date()
        if d:
            return RedirectResponse(f"/brief/{d}")
        return tpl.TemplateResponse(
            "brief.html",
            {"request": request, "brief": None, "dates": []})

    @app.get("/brief/{date}", response_class=HTMLResponse)
    def brief(request: Request, date: str):
        q = WebQuery(db)
        return tpl.TemplateResponse(
            "brief.html",
            {"request": request, "brief": q.brief_for_web(date),
             "dates": q.list_dates()})

    @app.get("/api/dates")
    def api_dates():
        return JSONResponse({"dates": WebQuery(db).list_dates()})

    @app.post("/api/feedback")
    async def api_feedback(request: Request):
        b = await request.json()
        fr = FeedbackRepo(db)
        fr.upsert_rating(
            b["brief_item_id"], b["rating"], b["anon_id"])
        if b.get("comment"):
            fr.add(b["brief_item_id"], b["rating"], b["anon_id"],
                   comment=b["comment"])
        return JSONResponse(fr.counts(b["brief_item_id"]))

    @app.post("/api/event")
    async def api_event(request: Request):
        b = await request.json()
        EventRepo(db).add(
            b["brief_item_id"], b["type"], b["anon_id"])
        return JSONResponse({"ok": True})

    return app
