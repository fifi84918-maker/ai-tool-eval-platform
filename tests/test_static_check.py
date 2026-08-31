"""Tests for V1E static detection pipeline.

Test cases:
  1) Valid SKILL.md + valid Python block → REVIEWED, risk_flags=[]
  2) rm -rf / in script → QUARANTINE, security.high_risk_command in flags
  3) Hardcoded api_key="sk-..." → credential_leak block
  4) Missing frontmatter → frontmatter warn, verdict still REVIEWED
  5) Metadata-only (no skill_md, no artifacts) → METADATA_ONLY
  6) _ensure_columns idempotency: double call → no error, columns present
  7) Old-record compat: new skill without V1E fields → sensible defaults
"""

import json
import textwrap
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Isolated SQLite file for each test."""
    db_file = str(tmp_path / "static_test.db")
    monkeypatch.setenv("APP_DB_PATH", db_file)
    from api.db.database import close_conn, get_conn
    close_conn()
    get_conn()  # trigger lazy init
    yield db_file
    close_conn()


# ---------------------------------------------------------------------------
# Skill-dict helpers
# ---------------------------------------------------------------------------

VALID_SKILL_MD = textwrap.dedent("""\
    ---
    name: PDF Processor
    description: Converts PDF files to text with layout preservation
    version: "1.0"
    license: MIT
    ---

    # PDF Processor

    Converts PDF files to text.

    ## Usage

    ```python
    from pathlib import Path
    p = Path("doc.pdf")
    print(p.suffix)
    ```

    ## Example

    Pass a file path and get back plain text.
""")

DANGEROUS_SCRIPT = "rm -rf /tmp/something && rm -rf / --no-preserve-root"

CREDENTIAL_SCRIPT = textwrap.dedent("""\
    import openai
    api_key = "sk-1234567890abcdef1234567890abcdef12345678"
    client = openai.OpenAI(api_key=api_key)
""")

NO_FRONTMATTER_MD = textwrap.dedent("""\
    # My Skill

    This skill does something useful.

    ## Usage

    ```python
    print("hello")
    ```
""")


def _make_skill(skill_md="", artifacts=None, repo_metadata=None):
    return {
        "skill_id": "a" * 64,
        "skill_md": skill_md,
        "artifacts": artifacts or [],
        "repo_metadata": repo_metadata or {},
    }


# ---------------------------------------------------------------------------
# 1) Valid SKILL.md → REVIEWED, empty risk_flags
# ---------------------------------------------------------------------------

class TestValidSkill:
    def test_reviewed_verdict(self):
        from api.scoring.static_check import StaticChecker
        result = StaticChecker().check(_make_skill(skill_md=VALID_SKILL_MD))
        assert result.verdict == "REVIEWED"
        assert result.status == "STATIC_REVIEWED"

    def test_no_block_risk_flags(self):
        from api.scoring.static_check import StaticChecker
        result = StaticChecker().check(_make_skill(skill_md=VALID_SKILL_MD))
        block_flags = [f for f in result.risk_flags if f["severity"] == "block"]
        assert block_flags == [], f"Unexpected block flags: {block_flags}"

    def test_frontmatter_passes(self):
        from api.scoring.static_check import StaticChecker
        result = StaticChecker().check(_make_skill(skill_md=VALID_SKILL_MD))
        fm = next((c for c in result.checks if c.name == "structure.frontmatter_valid"), None)
        assert fm is not None
        assert fm.passed is True

    def test_all_block_checks_pass(self):
        from api.scoring.static_check import StaticChecker
        result = StaticChecker().check(_make_skill(skill_md=VALID_SKILL_MD))
        block_checks = [
            c for c in result.checks
            if c.severity == "block" and not c.passed
        ]
        assert block_checks == []

    def test_duration_recorded(self):
        from api.scoring.static_check import StaticChecker
        result = StaticChecker().check(_make_skill(skill_md=VALID_SKILL_MD))
        assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# 2) rm -rf / → QUARANTINE, security.high_risk_command in flags
# ---------------------------------------------------------------------------

class TestDangerousCommand:
    def test_quarantine_verdict(self):
        from api.scoring.static_check import StaticChecker
        skill = _make_skill(
            skill_md=VALID_SKILL_MD,
            artifacts=[{"kind": "script", "content": DANGEROUS_SCRIPT}],
        )
        result = StaticChecker().check(skill)
        assert result.verdict == "QUARANTINE"
        assert result.status == "QUARANTINED"

    def test_high_risk_flag_present(self):
        from api.scoring.static_check import StaticChecker
        skill = _make_skill(
            skill_md=VALID_SKILL_MD,
            artifacts=[{"kind": "script", "content": DANGEROUS_SCRIPT}],
        )
        result = StaticChecker().check(skill)
        rules = [f["rule"] for f in result.risk_flags]
        assert "security.high_risk_command" in rules

    def test_flag_severity_is_block(self):
        from api.scoring.static_check import StaticChecker
        skill = _make_skill(
            skill_md=VALID_SKILL_MD,
            artifacts=[{"kind": "script", "content": DANGEROUS_SCRIPT}],
        )
        result = StaticChecker().check(skill)
        hrc = next(
            (f for f in result.risk_flags if f["rule"] == "security.high_risk_command"),
            None,
        )
        assert hrc is not None
        assert hrc["severity"] == "block"

    def test_dangerous_in_code_block_quarantined(self):
        """rm -rf inside a SKILL.md code block also triggers."""
        from api.scoring.static_check import StaticChecker
        md = VALID_SKILL_MD + "\n```bash\nrm -rf /home/user\n```\n"
        result = StaticChecker().check(_make_skill(skill_md=md))
        assert result.verdict == "QUARANTINE"


# ---------------------------------------------------------------------------
# 3) Hardcoded credential → credential_leak block
# ---------------------------------------------------------------------------

class TestCredentialLeak:
    def test_sk_prefix_triggers_block(self):
        from api.scoring.static_check import StaticChecker
        skill = _make_skill(
            skill_md=VALID_SKILL_MD,
            artifacts=[{"kind": "python", "content": CREDENTIAL_SCRIPT}],
        )
        result = StaticChecker().check(skill)
        cred_flags = [f for f in result.risk_flags
                      if f["rule"] == "security.credential_leak"]
        assert len(cred_flags) >= 1, "credential_leak not detected"
        assert cred_flags[0]["severity"] == "block"

    def test_verdict_quarantine_on_credential(self):
        from api.scoring.static_check import StaticChecker
        skill = _make_skill(
            skill_md=VALID_SKILL_MD,
            artifacts=[{"kind": "python", "content": CREDENTIAL_SCRIPT}],
        )
        result = StaticChecker().check(skill)
        assert result.verdict == "QUARANTINE"

    def test_generic_api_key_assignment(self):
        """generic api_key = "..." pattern also fires."""
        from api.scoring.static_check import StaticChecker
        script = 'api_key = "secretpassword123456"\n'
        skill = _make_skill(
            skill_md=VALID_SKILL_MD,
            artifacts=[{"kind": "python", "content": script}],
        )
        result = StaticChecker().check(skill)
        cred_flags = [f for f in result.risk_flags
                      if f["rule"] == "security.credential_leak"]
        assert len(cred_flags) >= 1

    def test_no_false_positive_short_string(self):
        """Short strings (< 8 chars) should NOT fire credential_leak."""
        from api.scoring.static_check import StaticChecker
        script = 'name = "bob"\n'
        skill = _make_skill(
            skill_md=VALID_SKILL_MD,
            artifacts=[{"kind": "python", "content": script}],
        )
        result = StaticChecker().check(skill)
        cred_flags = [f for f in result.risk_flags
                      if f["rule"] == "security.credential_leak"]
        assert cred_flags == [], f"False positive: {cred_flags}"


# ---------------------------------------------------------------------------
# 4) Missing frontmatter → warn, verdict still REVIEWED (no block)
# ---------------------------------------------------------------------------

class TestMissingFrontmatter:
    def test_frontmatter_check_fails(self):
        from api.scoring.static_check import StaticChecker
        result = StaticChecker().check(_make_skill(skill_md=NO_FRONTMATTER_MD))
        fm = next(
            (c for c in result.checks if c.name == "structure.frontmatter_valid"),
            None,
        )
        assert fm is not None
        assert fm.passed is False

    def test_severity_is_warn_not_block(self):
        from api.scoring.static_check import StaticChecker
        result = StaticChecker().check(_make_skill(skill_md=NO_FRONTMATTER_MD))
        fm = next(c for c in result.checks if c.name == "structure.frontmatter_valid")
        assert fm.severity == "warn"

    def test_verdict_still_reviewed(self):
        """No block check → verdict is REVIEWED even with warn."""
        from api.scoring.static_check import StaticChecker
        result = StaticChecker().check(_make_skill(skill_md=NO_FRONTMATTER_MD))
        assert result.verdict == "REVIEWED"
        assert result.status == "STATIC_REVIEWED"

    def test_frontmatter_warn_in_risk_flags(self):
        """Warn items appear in risk_flags."""
        from api.scoring.static_check import StaticChecker
        result = StaticChecker().check(_make_skill(skill_md=NO_FRONTMATTER_MD))
        warn_flags = [f for f in result.risk_flags if f["severity"] == "warn"]
        rules = [f["rule"] for f in warn_flags]
        assert "structure.frontmatter_valid" in rules


# ---------------------------------------------------------------------------
# 5) Metadata only (no skill_md, no artifacts) → METADATA_ONLY
# ---------------------------------------------------------------------------

class TestMetadataOnly:
    def test_metadata_only_verdict(self):
        from api.scoring.static_check import StaticChecker
        result = StaticChecker().check(_make_skill(skill_md="", artifacts=[]))
        assert result.verdict == "METADATA_ONLY"
        assert result.status == "METADATA_ONLY"

    def test_score_none_for_metadata_only(self):
        """METADATA_ONLY skills have no actionable score."""
        from api.scoring.static_check import StaticChecker
        result = StaticChecker().check(_make_skill())
        assert result.verdict == "METADATA_ONLY"

    def test_empty_skill_md_string(self):
        """Whitespace-only skill_md counts as empty."""
        from api.scoring.static_check import StaticChecker
        result = StaticChecker().check(_make_skill(skill_md="   \n  "))
        assert result.verdict == "METADATA_ONLY"


# ---------------------------------------------------------------------------
# 6) _ensure_columns idempotency
# ---------------------------------------------------------------------------

class TestEnsureColumnsIdempotency:
    def test_double_call_no_error(self, tmp_db):
        from api.db.database import get_conn, _ensure_columns
        conn = get_conn()
        # Should not raise on second call
        _ensure_columns(conn)
        _ensure_columns(conn)

    def test_v1e_columns_present_after_init(self, tmp_db):
        from api.db.database import get_conn
        conn = get_conn()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(skills)").fetchall()}
        for expected in ("status", "entity_type", "risk_flags",
                         "status_changed_at", "canonical_name", "dynamic_score"):
            assert expected in cols, f"Column '{expected}' missing from skills table"

    def test_columns_not_duplicated(self, tmp_db):
        """Running _ensure_columns 5× doesn't create duplicate columns."""
        from api.db.database import get_conn, _ensure_columns
        conn = get_conn()
        for _ in range(5):
            _ensure_columns(conn)
        col_names = [row[1] for row in conn.execute("PRAGMA table_info(skills)").fetchall()]
        assert len(col_names) == len(set(col_names)), "Duplicate columns detected"


# ---------------------------------------------------------------------------
# 7) Old-record compatibility: CanonicalSkill without V1E fields
# ---------------------------------------------------------------------------

class TestOldRecordCompat:
    def test_new_skill_has_default_status(self, tmp_db):
        """A freshly created skill gets status='DISCOVERED' by default."""
        from api.store.skill_store import put_skill, get_skill
        from api.models.skill_schema import CanonicalSkill
        from datetime import datetime, timezone

        skill = CanonicalSkill(
            skill_id="b" * 64,
            name="Legacy Skill",
            description="An old-style skill",
            platform="github",
            state="ACQUIRED",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        put_skill(skill)
        fetched = get_skill("b" * 64)
        assert fetched is not None
        assert fetched.status == "DISCOVERED"
        assert fetched.entity_type == "SKILL"
        assert fetched.risk_flags == []

    def test_raw_db_row_missing_columns_handled(self, tmp_db):
        """Row read by _row_to_skill with missing V1E columns → safe defaults."""
        from api.db.database import get_conn
        from api.store.skill_store import _row_to_skill
        from datetime import datetime, timezone

        # Insert minimal row without V1E columns (simulate old DB)
        conn = get_conn()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO skills
               (skill_id, name, description, platform, state, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("c" * 64, "Old Skill", "desc", "github", "ACQUIRED", now, now),
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM skills WHERE skill_id = ?", ("c" * 64,)
        ).fetchone()
        skill = _row_to_skill(row)
        assert skill.status == "DISCOVERED"    # NOT NULL DEFAULT in DDL
        assert skill.entity_type == "SKILL"
        assert skill.risk_flags == []
        assert skill.canonical_name is None

    def test_risk_flags_roundtrip(self, tmp_db):
        """risk_flags stored as JSON, read back as list[dict]."""
        from api.store.skill_store import put_skill, get_skill
        from api.models.skill_schema import CanonicalSkill
        from datetime import datetime, timezone

        flags = [
            {"rule": "security.credential_leak", "severity": "block", "detail": "test"},
        ]
        skill = CanonicalSkill(
            skill_id="d" * 64,
            name="Flagged",
            description="Has flags",
            platform="github",
            state="QUARANTINED",
            status="QUARANTINED",
            risk_flags=flags,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        put_skill(skill)
        fetched = get_skill("d" * 64)
        assert fetched.risk_flags == flags


# ---------------------------------------------------------------------------
# StaticResult.to_dict() structure test
# ---------------------------------------------------------------------------

class TestStaticResultStructure:
    def test_to_dict_keys(self):
        from api.scoring.static_check import StaticResult, CheckDetail
        r = StaticResult(
            skill_id="e" * 64,
            checks=[CheckDetail("structure.frontmatter_valid", True, "info", "ok")],
            verdict="REVIEWED",
            status="STATIC_REVIEWED",
            risk_flags=[],
        )
        d = r.to_dict()
        assert set(d.keys()) >= {"skill_id", "checks", "verdict", "status",
                                  "risk_flags", "duration_ms"}
        assert d["checks"][0]["name"] == "structure.frontmatter_valid"
        assert d["verdict"] == "REVIEWED"
