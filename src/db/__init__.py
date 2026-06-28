from .database import Database
from .seed_taxonomy import seed_taxonomy


def init_db(path: str = "data/marketnews.db") -> Database:
    db = Database(path)
    db.init_schema()
    seed_taxonomy(db)
    return db


__all__ = ["Database", "init_db"]
