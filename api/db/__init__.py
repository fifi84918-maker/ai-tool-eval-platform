"""api/db package — SQLite persistence helpers."""

from api.db.database import get_conn, close_conn, init_db
from api.db.aux_store import (
    put_profile, get_profile, list_profiles, clear_profiles,
    append_recommend_history, list_recommend_history, clear_recommend_history,
    save_ingest_run, list_ingest_runs, clear_ingest_runs,
    clear_all_aux,
)

__all__ = [
    "get_conn", "close_conn", "init_db",
    "put_profile", "get_profile", "list_profiles", "clear_profiles",
    "append_recommend_history", "list_recommend_history", "clear_recommend_history",
    "save_ingest_run", "list_ingest_runs", "clear_ingest_runs",
    "clear_all_aux",
]
