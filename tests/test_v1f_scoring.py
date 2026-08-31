"""Tests for 8-dimension scoring scaffold (V1F — PRD §6.1/§6.2).

Cases:
  a) clean static skill → composite has value, evidence_level='C'
  b) QUARANTINED (block risk_flags) → permission_privacy low, composite limited
  c) METADATA_ONLY → evidence_level='D', dynamic dims null
  d) dynamic enabled + score=100 → evidence_level='B', task_effect mapped
  e) DIMENSIONS weight sum = 1.0
  f) GET /api/v1/skills/{id}/scores contract fields present
  g) old DB without V1F columns → idempotent _ensure_columns, scoring works
"""

import json
import textwrap
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "v1f_test.db")
    monkeypatch.setenv("APP_DB_PATH", db_file)
    from api.db.database import close_conn, get_conn
    close_conn()
    get_conn()
    yield db_file
    close_conn()


VALID_SKILL_MD = textwrap.dedent("""\
    ---
    name: PDF Processor
    description: Converts PDF files to text, preserving paragraph layout.
    version: "1.0"
    license: MIT
    ---

    # PDF Processor

    ## Usage

    Pass a PDF file path and receive plain text output.

    ## Example

    ```python
    from pathlib import Path
    text = process_pdf(Path("report.pdf"))
    print(text[:200])
    ```
""")


def _make_static_result(verdict="REVIEWED", risk_flags=None):
    from api.scoring.static_check import StaticResult, CheckDetail
    status_map = {
        "REVIEWED":      "STATIC_REVIEWED",
        "QUARANTINE":    "QUARANTINED",
        "METADATA_ONLY": "METADATA_ONLY",
    }
    checks = [
        CheckDetail("structure.frontmatter_valid", True,  "info", "ok"),
        CheckDetail("structure.required_files",    True,  "info", "ok"),
        CheckDetail("security.high_risk_command",  True,  "info", "no risk"),
        CheckDetail("security.credential_leak",    True,  "info", "no creds"),
        CheckDetail("quality.doc_completeness",    True,  "info", "ok"),
    ]
    return StaticResult(
        skill_id="x" * 64,
        checks=checks,
        verdict=verdict,
        status=status_map.get(verdict, verdict),
        risk_flags=risk_flags or [],
    )


def _make_dynamic_result(score: float | None = None):
    from api.scoring.dynamic import DynamicResult
    return DynamicResult(skill_id="x" * 64, score=score, duration_ms=10.0)


# ---------------------------------------------------------------------------
# a) clean skill → composite non-None, evidence='C'
# ---------------------------------------------------------------------------

class TestCleanSkill:
    def test_composite_has_value(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "a" * 64, "skill_md": VALID_SKILL_MD},
            static_result=_make_static_result(),
        )
        assert result.composite is not None
        assert result.composite > 0

    def test_evidence_level_C(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "a" * 64, "skill_md": VALID_SKILL_MD},
            static_result=_make_static_result(),
        )
        assert result.evidence_level == "C"

    def test_permission_privacy_high_on_clean(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "a" * 64, "skill_md": VALID_SKILL_MD},
            static_result=_make_static_result(risk_flags=[]),
        )
        pp = result.dimensions.get("permission_privacy")
        assert pp is not None and pp >= 80

    def test_sample_size_is_zero(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "a" * 64},
            static_result=_make_static_result(),
        )
        assert result.sample_size == 0

    def test_uplift_is_none(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "a" * 64},
            static_result=_make_static_result(),
        )
        assert result.uplift is None


# ---------------------------------------------------------------------------
# b) QUARANTINED → permission_privacy low, composite still computed
# ---------------------------------------------------------------------------

class TestQuarantinedSkill:
    def test_permission_privacy_low_on_two_block_flags(self):
        from api.scoring.scorer import SkillScorer
        flags = [
            {"rule": "security.high_risk_command", "severity": "block", "detail": "rm -rf /"},
            {"rule": "security.credential_leak",   "severity": "block", "detail": "key found"},
        ]
        result = SkillScorer().score(
            {"skill_id": "b" * 64, "skill_md": VALID_SKILL_MD},
            static_result=_make_static_result(verdict="QUARANTINE", risk_flags=flags),
        )
        pp = result.dimensions.get("permission_privacy")
        assert pp is not None and pp <= 55

    def test_evidence_still_C_on_quarantine(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "b" * 64},
            static_result=_make_static_result(
                verdict="QUARANTINE",
                risk_flags=[{"rule": "x", "severity": "block", "detail": ""}],
            ),
        )
        assert result.evidence_level == "C"

    def test_composite_non_none_on_quarantine(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "b" * 64},
            static_result=_make_static_result(
                verdict="QUARANTINE",
                risk_flags=[{"rule": "x", "severity": "block", "detail": ""}],
            ),
        )
        assert result.composite is not None


# ---------------------------------------------------------------------------
# c) METADATA_ONLY → evidence='D', dynamic dims null
# ---------------------------------------------------------------------------

class TestMetadataOnly:
    def test_evidence_level_D(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "c" * 64, "skill_md": ""},
            static_result=_make_static_result(verdict="METADATA_ONLY"),
        )
        assert result.evidence_level == "D"

    def test_dynamic_dims_null(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "c" * 64, "skill_md": ""},
            static_result=_make_static_result(verdict="METADATA_ONLY"),
        )
        for dim in ("task_effect", "stability", "trigger_quality"):
            assert result.dimensions.get(dim) is None, (
                f"{dim} should be None for D-level, got {result.dimensions[dim]}"
            )

    def test_no_crash_on_metadata_only(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "c" * 64},
            static_result=_make_static_result(verdict="METADATA_ONLY"),
        )
        assert result.evidence_level == "D"


# ---------------------------------------------------------------------------
# d) dynamic score=100 → evidence='B', task_effect=100
# ---------------------------------------------------------------------------

class TestDynamicEnabled:
    def test_evidence_B_with_dynamic_score(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "d" * 64, "skill_md": VALID_SKILL_MD},
            static_result=_make_static_result(),
            dynamic_result=_make_dynamic_result(score=100.0),
        )
        assert result.evidence_level == "B"

    def test_task_effect_equals_dynamic_score(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "d" * 64, "skill_md": VALID_SKILL_MD},
            static_result=_make_static_result(),
            dynamic_result=_make_dynamic_result(score=100.0),
        )
        assert result.dimensions["task_effect"] == 100.0

    def test_composite_at_least_equal_with_dynamic_100(self):
        from api.scoring.scorer import SkillScorer
        base  = SkillScorer().score(
            {"skill_id": "d" * 64, "skill_md": VALID_SKILL_MD},
            static_result=_make_static_result(),
        )
        with_dyn = SkillScorer().score(
            {"skill_id": "d" * 64, "skill_md": VALID_SKILL_MD},
            static_result=_make_static_result(),
            dynamic_result=_make_dynamic_result(score=100.0),
        )
        assert (with_dyn.composite or 0) >= (base.composite or 0)

    def test_evidence_C_without_dynamic(self):
        from api.scoring.scorer import SkillScorer
        result = SkillScorer().score(
            {"skill_id": "d" * 64},
            static_result=_make_static_result(),
        )
        assert result.evidence_level == "C"


# ---------------------------------------------------------------------------
# e) Weight sum = 1.0
# ---------------------------------------------------------------------------

class TestDimensionWeights:
    def test_weights_sum_to_one(self):
        from api.scoring.dimensions import DIMENSIONS
        assert abs(sum(DIMENSIONS.values()) - 1.0) < 1e-9

    def test_all_eight_dims_present(self):
        from api.scoring.dimensions import DIMENSIONS
        expected = {
            "task_effect", "stability", "trigger_quality", "permission_privacy",
            "cost_efficiency", "platform_compat", "maintainability", "doc_explainability",
        }
        assert set(DIMENSIONS.keys()) == expected

    def test_no_negative_weights(self):
        from api.scoring.dimensions import DIMENSIONS
        for k, v in DIMENSIONS.items():
            assert v > 0, f"negative weight: {k}={v}"

    def test_score_result_has_all_dims(self):
        from api.scoring.scorer import SkillScorer
        from api.scoring.dimensions import DIMENSIONS
        result = SkillScorer().score({"skill_id": "e" * 64})
        assert set(result.dimensions.keys()) == set(DIMENSIONS.keys())


# ---------------------------------------------------------------------------
# f) GET /api/v1/skills/{id}/scores contract
# ---------------------------------------------------------------------------

class TestScoresEndpoint:
    @pytest.fixture
    def client(self, tmp_db):
        from api.main import app
        return TestClient(app)

    @pytest.fixture
    def skill_and_score(self, tmp_db):
        from api.store.skill_store import put_skill
        from api.models.skill_schema import CanonicalSkill
        from api.db.score_store import upsert_score
        from api.scoring.scorer import ScoreResult
        from datetime import datetime, timezone

        skill_id = "f" * 64
        skill = CanonicalSkill(
            skill_id=skill_id, name="Test Skill",
            description="endpoint test",
            platform="github", state="STATIC_REVIEWED", status="STATIC_REVIEWED",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        put_skill(skill)

        upsert_score(ScoreResult(
            skill_id=skill_id,
            dimensions={
                "task_effect": 72.0, "stability": None,
                "trigger_quality": 80.0, "permission_privacy": 100.0,
                "cost_efficiency": None, "platform_compat": None,
                "maintainability": 70.0, "doc_explainability": 65.0,
            },
            composite=77.5, evidence_level="C", sample_size=0,
        ))
        return skill_id

    def test_200_response(self, client, skill_and_score):
        r = client.get(f"/api/v1/skills/{skill_and_score}/scores")
        assert r.status_code == 200

    def test_contract_fields_present(self, client, skill_and_score):
        data = client.get(f"/api/v1/skills/{skill_and_score}/scores").json()
        for key in ("skill_id", "dimensions", "composite", "evidence_level",
                    "sample_size", "uplift", "env", "status", "valid_until"):
            assert key in data, f"Missing field: {key}"

    def test_evidence_level_value(self, client, skill_and_score):
        data = client.get(f"/api/v1/skills/{skill_and_score}/scores").json()
        assert data["evidence_level"] == "C"

    def test_sample_size_zero(self, client, skill_and_score):
        data = client.get(f"/api/v1/skills/{skill_and_score}/scores").json()
        assert data["sample_size"] == 0

    def test_env_subfields(self, client, skill_and_score):
        data = client.get(f"/api/v1/skills/{skill_and_score}/scores").json()
        for k in ("host", "model", "client_version", "test_date"):
            assert k in data["env"], f"env.{k} missing"

    def test_404_unknown_skill(self, client, tmp_db):
        r = client.get("/api/v1/skills/" + "z" * 64 + "/scores")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# g) V1F column idempotency + score_store auto-creates table
# ---------------------------------------------------------------------------

class TestV1fPersistence:
    def test_ensure_columns_twice_no_error(self, tmp_db):
        from api.db.database import get_conn, _ensure_columns
        conn = get_conn()
        _ensure_columns(conn)
        _ensure_columns(conn)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(skills)").fetchall()}
        for c in ("dimensions_json", "evidence_level", "sample_size"):
            assert c in cols

    def test_upsert_creates_score(self, tmp_db):
        from api.db.score_store import upsert_score, get_score
        from api.scoring.scorer import ScoreResult
        upsert_score(ScoreResult(
            skill_id="g" * 64, composite=60.0, evidence_level="C"
        ))
        stored = get_score("g" * 64)
        assert stored is not None
        assert stored["composite"] == 60.0

    def test_upsert_idempotent_keeps_latest(self, tmp_db):
        from api.db.score_store import upsert_score, get_score
        from api.db.database import get_conn
        from api.scoring.scorer import ScoreResult
        upsert_score(ScoreResult(skill_id="h" * 64, composite=50.0, evidence_level="C"))
        upsert_score(ScoreResult(skill_id="h" * 64, composite=80.0, evidence_level="B"))
        stored = get_score("h" * 64)
        assert stored["composite"] == 80.0
        assert stored["evidence_level"] == "B"
        count = get_conn().execute(
            "SELECT COUNT(*) FROM skill_scores WHERE skill_id=?", ("h" * 64,)
        ).fetchone()[0]
        assert count == 1
