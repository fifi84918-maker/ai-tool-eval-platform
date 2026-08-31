"""Tests for search query builder and search result cache (V1A search).

Test plan
---------
a) query construction: keywords + language + topics + min_stars → correct q string
b) default qualifiers: no language/topics → q contains "stars:>=50" and "pushed:>=2024-01-01"
c) cache TTL: write → read within TTL → hit; TTL=0 → miss
d) cache key normalisation: keywords in different order → same cache_key
"""

import json
import os
import pytest
from datetime import datetime, timezone, timedelta


# ---------------------------------------------------------------------------
# Fixture: isolated per-test DB
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Isolate each test to its own SQLite file."""
    db_file = str(tmp_path / "search_test.db")
    monkeypatch.setenv("APP_DB_PATH", db_file)

    from api.db.database import close_conn
    close_conn()
    # Trigger lazy init on the new path
    from api.db.database import get_conn
    get_conn()

    yield db_file

    close_conn()


# ---------------------------------------------------------------------------
# a) Query construction: keywords + qualifiers → correct q
# ---------------------------------------------------------------------------

class TestQueryBuilder:
    def test_full_qualifiers(self):
        """All qualifiers present → q assembled correctly."""
        from api.search.query_builder import SearchParams, build_github_query

        params = SearchParams(
            keywords=["pdf", "skill"],
            language="python",
            topics=["cli", "skill"],
            min_stars=100,
        )
        q, sort, order = build_github_query(params)

        assert "pdf" in q
        assert "skill" in q
        assert "language:python" in q
        assert "topic:cli" in q
        assert "topic:skill" in q
        assert "stars:>=100" in q
        assert "pushed:>=2024-01-01" in q
        assert sort == "stars"
        assert order == "desc"

    def test_q_format_plus_separated(self):
        """All tokens joined with '+', no spaces."""
        from api.search.query_builder import SearchParams, build_github_query

        params = SearchParams(keywords=["foo", "bar"])
        q, _, _ = build_github_query(params)

        assert " " not in q  # no spaces
        parts = q.split("+")
        assert len(parts) >= 1

    def test_multiple_topics_each_prefixed(self):
        """Each topic gets its own topic: qualifier."""
        from api.search.query_builder import SearchParams, build_github_query

        params = SearchParams(
            keywords=["x"],
            topics=["automation", "devops"],
        )
        q, _, _ = build_github_query(params)
        assert "topic:automation" in q
        assert "topic:devops" in q

    def test_sort_updated(self):
        """sort='updated' is passed through."""
        from api.search.query_builder import SearchParams, build_github_query

        params = SearchParams(keywords=["x"], sort="updated")
        _, sort, order = build_github_query(params)
        assert sort == "updated"
        assert order == "desc"

    def test_invalid_sort_falls_back_to_stars(self):
        """Unknown sort value falls back to 'stars'."""
        from api.search.query_builder import SearchParams, build_github_query

        params = SearchParams(keywords=["x"], sort="nonsense")
        _, sort, _ = build_github_query(params)
        assert sort == "stars"


# ---------------------------------------------------------------------------
# b) Default qualifiers: no language/topics → stars:>=50 and pushed:>= date
# ---------------------------------------------------------------------------

class TestDefaultQualifiers:
    def test_default_min_stars(self):
        """Without min_stars kwarg, q contains 'stars:>=50'."""
        from api.search.query_builder import SearchParams, build_github_query

        params = SearchParams(keywords=["pdf"])
        q, _, _ = build_github_query(params)

        assert "stars:>=50" in q, f"Expected 'stars:>=50' in q={q!r}"

    def test_default_pushed_since(self):
        """Without pushed_since, q contains 'pushed:>=2024-01-01'."""
        from api.search.query_builder import SearchParams, build_github_query

        params = SearchParams(keywords=["pdf"])
        q, _, _ = build_github_query(params)

        assert "pushed:>=2024-01-01" in q, f"Expected pushed qualifier in q={q!r}"

    def test_no_language_qualifier_when_not_set(self):
        """No language= argument → no 'language:' in q."""
        from api.search.query_builder import SearchParams, build_github_query

        params = SearchParams(keywords=["pdf"])
        q, _, _ = build_github_query(params)

        assert "language:" not in q

    def test_no_topic_qualifier_when_not_set(self):
        """No topics argument → no 'topic:' in q."""
        from api.search.query_builder import SearchParams, build_github_query

        params = SearchParams(keywords=["pdf"])
        q, _, _ = build_github_query(params)

        assert "topic:" not in q


# ---------------------------------------------------------------------------
# c) Cache: write → read within TTL → hit; TTL=0 → stale miss
# ---------------------------------------------------------------------------

class TestSearchCache:
    def test_cache_hit_within_ttl(self, tmp_db, monkeypatch):
        """Written entry is returned within default TTL."""
        monkeypatch.setenv("SEARCH_CACHE_TTL_HOURS", "24")
        from api.db.search_cache_store import make_cache_key, get_cached, set_cached

        key = make_cache_key("pdf", {"language": "python"})
        items = [{"repo_full_name": "test/repo", "stars": 100}]

        set_cached(key, "pdf", {"language": "python"}, items)
        result = get_cached(key)

        assert result is not None
        assert len(result) == 1
        assert result[0]["repo_full_name"] == "test/repo"

    def test_cache_miss_when_ttl_zero(self, tmp_db, monkeypatch):
        """TTL=0 → every read is a stale miss."""
        monkeypatch.setenv("SEARCH_CACHE_TTL_HOURS", "0")
        from api.db.search_cache_store import make_cache_key, get_cached, set_cached

        key = make_cache_key("stale_test", {})
        items = [{"repo_full_name": "test/stale"}]

        # Write with TTL=0 env, then immediately try to read
        set_cached(key, "stale_test", {}, items)
        result = get_cached(key)

        assert result is None, "TTL=0 should always produce a miss"

    def test_cache_miss_when_key_absent(self, tmp_db):
        """Non-existent key returns None."""
        from api.db.search_cache_store import get_cached

        result = get_cached("nonexistent_key_abc123")
        assert result is None

    def test_cache_upsert_overwrites_old_entry(self, tmp_db, monkeypatch):
        """Second set_cached with same key replaces the old entry."""
        monkeypatch.setenv("SEARCH_CACHE_TTL_HOURS", "24")
        from api.db.search_cache_store import make_cache_key, get_cached, set_cached

        key = make_cache_key("overwrite", {})
        set_cached(key, "overwrite", {}, [{"repo_full_name": "old/repo"}])
        set_cached(key, "overwrite", {}, [{"repo_full_name": "new/repo"}])

        result = get_cached(key)
        assert result is not None
        assert result[0]["repo_full_name"] == "new/repo"


# ---------------------------------------------------------------------------
# d) Cache key normalisation: different keyword order → same key
# ---------------------------------------------------------------------------

class TestCacheKeyNormalisation:
    def test_keywords_order_independent(self):
        """['pdf', 'skill'] and ['skill', 'pdf'] → same cache_key."""
        from api.db.search_cache_store import make_cache_key
        from api.search.query_builder import SearchParams, params_to_dict

        params_a = params_to_dict(SearchParams(keywords=["pdf", "skill"]))
        params_b = params_to_dict(SearchParams(keywords=["skill", "pdf"]))

        key_a = make_cache_key("pdf skill", params_a)
        key_b = make_cache_key("pdf skill", params_b)

        assert key_a == key_b, "Keywords order should not affect cache key"

    def test_topics_order_independent(self):
        """topics=['cli','devops'] and ['devops','cli'] → same key."""
        from api.db.search_cache_store import make_cache_key
        from api.search.query_builder import SearchParams, params_to_dict

        params_a = params_to_dict(SearchParams(keywords=["x"], topics=["cli", "devops"]))
        params_b = params_to_dict(SearchParams(keywords=["x"], topics=["devops", "cli"]))

        key_a = make_cache_key("x", params_a)
        key_b = make_cache_key("x", params_b)

        assert key_a == key_b

    def test_different_queries_different_keys(self):
        """Different query strings → different keys."""
        from api.db.search_cache_store import make_cache_key

        key_a = make_cache_key("pdf", {})
        key_b = make_cache_key("video", {})

        assert key_a != key_b

    def test_different_language_different_keys(self):
        """Same query, different language → different keys."""
        from api.db.search_cache_store import make_cache_key
        from api.search.query_builder import SearchParams, params_to_dict

        params_py = params_to_dict(SearchParams(keywords=["skill"], language="python"))
        params_go = params_to_dict(SearchParams(keywords=["skill"], language="go"))

        key_py = make_cache_key("skill", params_py)
        key_go = make_cache_key("skill", params_go)

        assert key_py != key_go
