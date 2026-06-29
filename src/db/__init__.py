from .database import Database
from .seed_taxonomy import seed_taxonomy
from .migrate import ensure_web_columns, ensure_indexes


def init_db(path: str = "data/marketnews.db") -> Database:
    db = Database(path)
    db.init_schema()
    seed_taxonomy(db)
    ensure_indexes(db)
    ensure_web_columns(db)
    return db


__all__ = ["Database", "init_db"]
