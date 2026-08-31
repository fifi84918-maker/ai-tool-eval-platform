"""Tests for compat-weighted ranking + conflict detection (PRD §7).

Cases:
  a) mixed pool (COMPATIBLE/BLOCKED/PENDING) → BLOCKED excluded, ordered by rank_score
  b) composite=None + evidence_level='C' → evidence_fallback=40, rank_score computed
  c) same canonical_name → version conflict detected
  d) target_domains Jaccard ≥ 0.7 → overlap conflict detected
  e) target_domains Jaccard < 0.7 → no overlap conflict
  f) compat_weight mapping: all 7 states correct
  g) include_blocked=true → BLOCKED appears with excluded=True
  h) empty pool → {items: [], conflicts: []}
  i) GET /api/v1/recommend/skills contract fields
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "rec_test.db")
    monkeypatch.setenv("APP_DB_PATH", db_file)
    from api.db.database import close_conn, get_conn
    close_conn()
    get_conn()
    yield db_file
    close_conn()


@pytest.fixture
def client(tmp_db):
    from api.main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Skill-dict helpers
# ---------------------------------------------------------------------------

def _skill(
    skill_id: str,
    name: str = "Skill",
    composite: float | None = 75.0,
    evidence_level: str = "C",
    compat_status: str = "COMPATIBLE",
    target_domains: list[str] | None = None,
    canonical_name: str | None = None,
) -> dict:
    return {
        "skill_id":       skill_id,
        "name":           name,
        "canonical_name": canonical_name or name,
        "description":    f"{name} description",
        "platform":       "github",
        "composite":      composite,
        "evidence_level": evidence_level,
        "compat_status":  compat_status,
        "target_domains": target_domains or [],
        "status":         "STATIC_REVIEWED",
    }


# ---------------------------------------------------------------------------
# a) Mixed pool → BLOCKED excluded, rank_score descending
# ---------------------------------------------------------------------------

class TestRankOrdering:
    def test_blocked_marked_excluded(self):
        from api.recommend.ranker import RecommendRanker
        pool = [
            _skill("aa" * 32, "TopSkill",   composite=90.0, compat_status="COMPATIBLE"),
            _skill("bb" * 32, "BlockedOne", composite=95.0, compat_status="BLOCKED"),
            _skill("cc" * 32, "PendingOne", composite=80.0, compat_status="PENDING_VERIFICATION"),
        ]
        ranked = RecommendRanker().rank(pool)
        blocked = next(s for s in ranked if s["skill_id"] == "bb" * 32)
        assert blocked["excluded"] is True

    def test_ranked_by_score_descending(self):
        from api.recommend.ranker import RecommendRanker
        pool = [
            _skill("aa" * 32, "Mid",   composite=60.0, compat_status="COMPATIBLE"),
            _skill("bb" * 32, "High",  composite=90.0, compat_status="COMPATIBLE"),
            _skill("cc" * 32, "Low",   composite=30.0, compat_status="COMPATIBLE"),
        ]
        ranked = RecommendRanker().rank(pool)
        scores = [s["rank_score"] for s in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_compatible_outranks_pending_same_composite(self):
        from api.recommend.ranker import RecommendRanker
        pool = [
            _skill("aa" * 32, "Pending",    composite=80.0, compat_status="PENDING_VERIFICATION"),
            _skill("bb" * 32, "Compatible", composite=80.0, compat_status="COMPATIBLE"),
        ]
        ranked = RecommendRanker().rank(pool)
        # COMPATIBLE has weight 1.0 vs PENDING weight 0.5
        assert ranked[0]["skill_id"] == "bb" * 32

    def test_incompatible_weight_zero(self):
        from api.recommend.ranker import RecommendRanker
        pool = [_skill("dd" * 32, composite=99.0, compat_status="INCOMPATIBLE")]
        ranked = RecommendRanker().rank(pool)
        assert ranked[0]["rank_score"] == 0.0
        assert ranked[0]["excluded"] is True


# ---------------------------------------------------------------------------
# b) composite=None + evidence_level='C' → evidence_fallback 40 × compat_weight
# ---------------------------------------------------------------------------

class TestEvidenceFallback:
    def test_none_composite_uses_fallback(self):
        from api.recommend.ranker import RecommendRanker
        pool = [_skill("ee" * 32, composite=None, evidence_level="C",
                        compat_status="COMPATIBLE")]
        ranked = RecommendRanker().rank(pool)
        item = ranked[0]
        assert item["score_source"] == "evidence_fallback"
        # C fallback = 40.0, COMPATIBLE weight = 1.0 → rank_score = 40.0
        assert item["rank_score"] == pytest.approx(40.0)

    def test_evidence_D_fallback(self):
        from api.recommend.ranker import RecommendRanker
        pool = [_skill("ff" * 32, composite=None, evidence_level="D",
                        compat_status="COMPATIBLE")]
        ranked = RecommendRanker().rank(pool)
        assert ranked[0]["rank_score"] == pytest.approx(20.0)

    def test_evidence_B_fallback(self):
        from api.recommend.ranker import RecommendRanker
        pool = [_skill("gg" * 32, composite=None, evidence_level="B",
                        compat_status="COMPATIBLE")]
        ranked = RecommendRanker().rank(pool)
        assert ranked[0]["rank_score"] == pytest.approx(60.0)

    def test_evidence_U_fallback_zero(self):
        from api.recommend.ranker import RecommendRanker
        pool = [_skill("hh" * 32, composite=None, evidence_level="U",
                        compat_status="COMPATIBLE")]
        ranked = RecommendRanker().rank(pool)
        assert ranked[0]["rank_score"] == 0.0


# ---------------------------------------------------------------------------
# c) Same canonical_name → version conflict
# ---------------------------------------------------------------------------

class TestVersionConflict:
    def test_same_name_two_entries_detected(self):
        from api.recommend.conflict import ConflictDetector
        skills = [
            _skill("aa" * 32, canonical_name="pdf-tool", compat_status="COMPATIBLE"),
            _skill("bb" * 32, canonical_name="pdf-tool", compat_status="COMPATIBLE"),
        ]
        conflicts = ConflictDetector().detect(skills)
        version_c = [c for c in conflicts if c.type == "version"]
        assert len(version_c) >= 1
        assert set(version_c[0].items) == {"aa" * 32, "bb" * 32}

    def test_different_names_no_version_conflict(self):
        from api.recommend.conflict import ConflictDetector
        skills = [
            _skill("cc" * 32, canonical_name="tool-a"),
            _skill("dd" * 32, canonical_name="tool-b"),
        ]
        conflicts = ConflictDetector().detect(skills)
        assert not any(c.type == "version" for c in conflicts)

    def test_three_versions_all_in_conflict_items(self):
        from api.recommend.conflict import ConflictDetector
        skills = [
            _skill("aa" * 32, canonical_name="shared-tool"),
            _skill("bb" * 32, canonical_name="shared-tool"),
            _skill("cc" * 32, canonical_name="shared-tool"),
        ]
        conflicts = ConflictDetector().detect(skills)
        vc = next(c for c in conflicts if c.type == "version")
        assert len(vc.items) == 3


# ---------------------------------------------------------------------------
# d) Jaccard ≥ 0.7 → overlap conflict
# ---------------------------------------------------------------------------

class TestOverlapConflict:
    def test_high_overlap_detected(self):
        from api.recommend.conflict import ConflictDetector
        # {a,b,c,d} ∩ {a,b,c,e} = {a,b,c}; union={a,b,c,d,e}; J=3/5=0.6 < 0.7
        # Use identical sets: J=1.0
        skills = [
            _skill("aa" * 32, target_domains=["data", "ml", "nlp"]),
            _skill("bb" * 32, target_domains=["data", "ml", "nlp"]),
        ]
        conflicts = ConflictDetector().detect(skills)
        overlap_c = [c for c in conflicts if c.type == "overlap"]
        assert len(overlap_c) >= 1

    def test_overlap_reason_contains_jaccard(self):
        from api.recommend.conflict import ConflictDetector
        skills = [
            _skill("aa" * 32, target_domains=["data", "ml", "nlp"]),
            _skill("bb" * 32, target_domains=["data", "ml", "nlp"]),
        ]
        conflicts = ConflictDetector().detect(skills)
        oc = next(c for c in conflicts if c.type == "overlap")
        assert "jaccard" in oc.reason.lower() or "Jaccard" in oc.reason

    def test_partial_overlap_above_threshold(self):
        from api.recommend.conflict import ConflictDetector
        # {a,b,c,d,e,f,f,h,g,j} ∩ same 8 of 10 → J >= 0.7
        domains_a = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        domains_b = ["a", "b", "c", "d", "e", "f", "g", "h"]    # 8/10 = 0.8
        skills = [
            _skill("cc" * 32, target_domains=domains_a),
            _skill("dd" * 32, target_domains=domains_b),
        ]
        conflicts = ConflictDetector().detect(skills)
        overlap_c = [c for c in conflicts if c.type == "overlap"]
        assert len(overlap_c) == 1


# ---------------------------------------------------------------------------
# e) Jaccard < 0.7 → no overlap conflict
# ---------------------------------------------------------------------------

class TestNoOverlap:
    def test_low_overlap_not_flagged(self):
        from api.recommend.conflict import ConflictDetector
        # J = 1/5 = 0.2
        skills = [
            _skill("ee" * 32, target_domains=["data", "web"]),
            _skill("ff" * 32, target_domains=["data", "devops", "ml", "nlp"]),
        ]
        conflicts = ConflictDetector().detect(skills)
        overlap_c = [c for c in conflicts if c.type == "overlap"]
        # J({data,web} | {data,devops,ml,nlp}) = 1/5 = 0.2 → below threshold
        assert len(overlap_c) == 0

    def test_empty_domains_no_overlap(self):
        from api.recommend.conflict import ConflictDetector
        skills = [
            _skill("gg" * 32, target_domains=[]),
            _skill("hh" * 32, target_domains=[]),
        ]
        conflicts = ConflictDetector().detect(skills)
        assert not any(c.type == "overlap" for c in conflicts)


# ---------------------------------------------------------------------------
# f) compat_weight mapping — all 7 states
# ---------------------------------------------------------------------------

class TestCompatWeightMapping:
    def test_all_seven_states(self):
        from api.recommend.ranker import COMPAT_WEIGHTS
        expected = {
            "COMPATIBLE":              1.00,
            "COMPATIBLE_WITH_ADAPTER": 0.85,
            "PARTIAL":                 0.60,
            "PENDING_VERIFICATION":    0.50,
            "UNKNOWN":                 0.30,
            "INCOMPATIBLE":            0.00,
            "BLOCKED":                 0.00,
        }
        for status, weight in expected.items():
            assert COMPAT_WEIGHTS[status] == pytest.approx(weight), (
                f"Wrong weight for {status}: got {COMPAT_WEIGHTS[status]}"
            )

    def test_rank_score_formula(self):
        from api.recommend.ranker import RecommendRanker
        # rank_score = composite × compat_weight × (1 + 0)
        pool = [_skill("aa" * 32, composite=80.0, compat_status="COMPATIBLE_WITH_ADAPTER")]
        ranked = RecommendRanker().rank(pool)
        # 80 × 0.85 = 68.0
        assert ranked[0]["rank_score"] == pytest.approx(68.0)

    def test_unknown_status_uses_030_weight(self):
        from api.recommend.ranker import RecommendRanker
        pool = [_skill("bb" * 32, composite=100.0, compat_status="UNKNOWN")]
        ranked = RecommendRanker().rank(pool)
        assert ranked[0]["rank_score"] == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# g) include_blocked=true → BLOCKED appears with excluded=True
# ---------------------------------------------------------------------------

class TestIncludeBlocked:
    @pytest.fixture
    def seeded_pool(self, tmp_db):
        """Seed skills + scores + compat into DB."""
        from api.store.skill_store import put_skill
        from api.models.skill_schema import CanonicalSkill
        from api.db.score_store import upsert_score
        from api.db.compat_store import upsert_compat
        from api.scoring.scorer import ScoreResult
        from api.scoring.compat import CompatAnalyzer
        from datetime import datetime, timezone

        def _put(sid, name, composite, compat_status_str):
            sk = CanonicalSkill(
                skill_id=sid, name=name,
                description=f"{name} desc", platform="github",
                state="STATIC_REVIEWED", status="STATIC_REVIEWED",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            put_skill(sk)
            upsert_score(ScoreResult(skill_id=sid, composite=composite, evidence_level="C"))
            # Fake compat result via direct upsert
            from api.scoring.compat import CompatResult, PortableCoreProfile, HostOverlayReport, CompatEvidence
            cr = CompatResult(skill_id=sid, compat_status=compat_status_str)
            from api.db.compat_store import upsert_compat
            upsert_compat(cr)

        _put("c0" * 32, "Clean",   80.0, "COMPATIBLE")
        _put("b0" * 32, "Blocked", 90.0, "BLOCKED")
        _put("p0" * 32, "Pending", 70.0, "PENDING_VERIFICATION")

    def test_blocked_hidden_by_default(self, client, seeded_pool):
        r = client.get("/api/v1/recommend/skills")
        assert r.status_code == 200
        ids = [s["skill_id"] for s in r.json()["items"]]
        assert "b0" * 32 not in ids

    def test_blocked_visible_with_flag(self, client, seeded_pool):
        r = client.get("/api/v1/recommend/skills?include_blocked=true")
        assert r.status_code == 200
        data = r.json()
        blocked = [s for s in data["items"] if s["skill_id"] == "b0" * 32]
        assert len(blocked) == 1
        assert blocked[0]["excluded"] is True

    def test_conflicts_in_response(self, client, seeded_pool):
        r = client.get("/api/v1/recommend/skills")
        assert "conflicts" in r.json()


# ---------------------------------------------------------------------------
# h) Empty pool → {items: [], conflicts: []}
# ---------------------------------------------------------------------------

class TestEmptyPool:
    def test_empty_list_ranked(self):
        from api.recommend.ranker import RecommendRanker
        assert RecommendRanker().rank([]) == []

    def test_empty_list_no_conflicts(self):
        from api.recommend.conflict import ConflictDetector
        assert ConflictDetector().detect([]) == []

    def test_endpoint_empty_db(self, client, tmp_db):
        r = client.get("/api/v1/recommend/skills")
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["conflicts"] == []
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# i) GET /api/v1/recommend/skills contract fields
# ---------------------------------------------------------------------------

class TestEndpointContract:
    @pytest.fixture
    def seeded(self, tmp_db):
        from api.store.skill_store import put_skill
        from api.models.skill_schema import CanonicalSkill
        from api.db.score_store import upsert_score
        from api.scoring.scorer import ScoreResult
        from api.scoring.compat import CompatResult
        from api.db.compat_store import upsert_compat
        from datetime import datetime, timezone

        sid = "f1" * 32
        sk = CanonicalSkill(
            skill_id=sid, name="Contract Skill",
            description="test", platform="github",
            state="STATIC_REVIEWED", status="STATIC_REVIEWED",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        put_skill(sk)
        upsert_score(ScoreResult(skill_id=sid, composite=72.0, evidence_level="C"))
        upsert_compat(CompatResult(skill_id=sid, compat_status="COMPATIBLE"))
        return sid

    def test_200(self, client, seeded):
        assert client.get("/api/v1/recommend/skills").status_code == 200

    def test_top_level_keys(self, client, seeded):
        data = client.get("/api/v1/recommend/skills").json()
        for key in ("total", "items", "conflicts"):
            assert key in data

    def test_item_fields(self, client, seeded):
        data = client.get("/api/v1/recommend/skills").json()
        assert data["total"] >= 1
        item = data["items"][0]
        for key in ("skill_id", "name", "compat_status", "composite",
                    "rank_score", "compat_weight", "excluded", "score_source"):
            assert key in item, f"Missing field: {key}"

    def test_compat_filter(self, client, seeded):
        r = client.get("/api/v1/recommend/skills?compat_status=COMPATIBLE")
        data = r.json()
        for item in data["items"]:
            assert item["compat_status"] == "COMPATIBLE"
