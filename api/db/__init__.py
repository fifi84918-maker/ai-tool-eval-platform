"""api/db package — SQLite persistence helpers."""

from api.db.database import get_conn, close_conn, init_db
from api.db.aux_store import (
    put_profile, get_profile, list_profiles, clear_profiles,
    append_recommend_history, list_recommend_history, clear_recommend_history,
    save_ingest_run, list_ingest_runs, clear_ingest_runs,
    clear_all_aux,
)
from api.db.search_cache_store import (
    make_cache_key,
    get_cached,
    set_cached,
    clear_search_cache,
)
from api.db.score_store import upsert_score, get_score, list_scores
from api.db.compat_store import upsert_compat, get_compat

__all__ = [
    "get_conn", "close_conn", "init_db",
    "put_profile", "get_profile", "list_profiles", "clear_profiles",
    "append_recommend_history", "list_recommend_history", "clear_recommend_history",
    "save_ingest_run", "list_ingest_runs", "clear_ingest_runs",
    "clear_all_aux",
    "make_cache_key", "get_cached", "set_cached", "clear_search_cache",
    "upsert_score", "get_score", "list_scores",
    "upsert_compat", "get_compat",
]

