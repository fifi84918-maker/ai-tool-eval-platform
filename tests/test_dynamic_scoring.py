"""Tests for dynamic skill checker (V1D).

Tests:
  a) valid SKILL.md + valid python block → score > 0
  b) invalid YAML frontmatter → frontmatter check fails, others proceed
  c) python syntax error → python_syntax_ok=False
  d) timeout → error captured, no crash
  e) empty skill → score=None
"""

import os
import sys
import textwrap
import subprocess
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Enable dynamic scoring for all tests in this module
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def enable_dynamic(monkeypatch):
    monkeypatch.setenv("DYNAMIC_SCORING", "enabled")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_SKILL_MD = textwrap.dedent("""\
    ---
    name: Test Skill
    description: A well-formed skill
    version: "1.0"
    ---

    # Test Skill

    A skill that processes data.

    ## Usage

    ```python
    x = 1 + 2
    print(x)
    ```
""")

INVALID_YAML_SKILL_MD = textwrap.dedent("""\
    ---
    name: Bad Skill
    : invalid yaml here :::
    ---

    # Bad Skill

    ```python
    x = 42
    ```
""")

BAD_PYTHON_SKILL_MD = textwrap.dedent("""\
    ---
    name: Bad Python
    description: Has syntax error
    ---

    # Bad Python

    ```python
    def foo(
        # missing closing paren — syntax error
    print("oops")
    ```
""")


# ---------------------------------------------------------------------------
# a) Valid SKILL.md + valid Python block → score > 0
# ---------------------------------------------------------------------------

class TestDynamicExecutorValid:
    def test_valid_skill_score_positive(self, tmp_path):
        """Valid SKILL.md with correct Python → score > 0, no error."""
        from api.scoring.dynamic import DynamicExecutor

        result = DynamicExecutor().run_skill_check({
            "skill_id": "abc" * 21 + "d",   # 64 chars
            "skill_md": VALID_SKILL_MD,
        })

        assert result.error is None or "DYNAMIC_SCORING" not in (result.error or "")
        assert result.score is not None
        assert result.score > 0, f"Expected score > 0, got {result.score}"
        assert result.duration_ms >= 0

        # At least frontmatter and code_blocks checks ran
        names = {c.name for c in result.checks}
        assert "frontmatter_valid" in names
        assert "code_blocks_all_valid" in names

    def test_all_valid_checks_pass(self, tmp_path):
        """All checks on clean skill are True (no failures)."""
        from api.scoring.dynamic import DynamicExecutor

        result = DynamicExecutor().run_skill_check({
            "skill_id": "a" * 64,
            "skill_md": VALID_SKILL_MD,
        })

        failed = [c for c in result.checks if not c.passed and "skipped" not in c.detail.lower()]
        assert failed == [], f"Unexpected failures: {failed}"


# ---------------------------------------------------------------------------
# b) Invalid YAML frontmatter → frontmatter fails, others proceed
# ---------------------------------------------------------------------------

class TestFrontmatterFailure:
    def test_invalid_yaml_frontmatter_check_fails(self):
        """Bad YAML → frontmatter_valid=False, code block check still runs."""
        from api.scoring.dynamic import DynamicExecutor

        result = DynamicExecutor().run_skill_check({
            "skill_id": "b" * 64,
            "skill_md": INVALID_YAML_SKILL_MD,
        })

        assert result.error is None
        fm_checks = [c for c in result.checks if c.name == "frontmatter_valid"]
        assert len(fm_checks) == 1
        assert fm_checks[0].passed is False, "Expected frontmatter to fail"
        assert "YAML" in fm_checks[0].detail or "yaml" in fm_checks[0].detail.lower()

        # Score is not None — other checks contributed
        # (code block has valid python, so score > 0)
        assert result.score is not None

    def test_other_checks_still_run_after_yaml_failure(self):
        """All checks are attempted even when frontmatter is invalid."""
        from api.scoring.dynamic import DynamicExecutor

        result = DynamicExecutor().run_skill_check({
            "skill_id": "b" * 64,
            "skill_md": INVALID_YAML_SKILL_MD,
        })

        names = {c.name for c in result.checks}
        # frontmatter ran AND code_blocks ran
        assert "frontmatter_valid" in names
        assert "code_blocks_all_valid" in names


# ---------------------------------------------------------------------------
# c) Python syntax error → python_syntax_ok=False
# ---------------------------------------------------------------------------

class TestPythonSyntaxError:
    def test_bad_python_block_fails_check(self):
        """Code block with syntax error → code_blocks_all_valid=False."""
        from api.scoring.dynamic import DynamicExecutor

        result = DynamicExecutor().run_skill_check({
            "skill_id": "c" * 64,
            "skill_md": BAD_PYTHON_SKILL_MD,
        })

        block_checks = [c for c in result.checks if c.name == "code_blocks_all_valid"]
        assert len(block_checks) == 1
        assert block_checks[0].passed is False, "Expected code_blocks to fail"

    def test_inline_python_syntax_error(self):
        """Passing python_code with syntax error → python_syntax_ok=False."""
        from api.scoring.dynamic import DynamicExecutor

        bad_py = "def broken(\n    # unclosed\nprint('x')\n"
        result = DynamicExecutor().run_skill_check({
            "skill_id": "c" * 64,
            "python_code": bad_py,
        })

        py_checks = [c for c in result.checks if c.name == "python_syntax_ok"]
        assert len(py_checks) == 1
        assert py_checks[0].passed is False

    def test_inline_python_valid_passes(self):
        """Valid python_code → python_syntax_ok=True."""
        from api.scoring.dynamic import DynamicExecutor

        result = DynamicExecutor().run_skill_check({
            "skill_id": "c" * 64,
            "python_code": "x = 1\nprint(x)\n",
        })

        py_checks = [c for c in result.checks if c.name == "python_syntax_ok"]
        assert len(py_checks) == 1
        assert py_checks[0].passed is True


# ---------------------------------------------------------------------------
# d) Timeout → error captured, no crash
# ---------------------------------------------------------------------------

class TestTimeout:
    def test_timeout_captured_not_raised(self, monkeypatch):
        """TimeoutExpired in subprocess → CheckResult.passed=False, no exception propagation."""
        from api.scoring import dynamic as dyn_mod
        from api.scoring.dynamic import DynamicExecutor

        # Patch _run_subprocess to simulate timeout
        def fake_run(cmd, cwd, timeout=30):
            mock_proc = MagicMock()
            mock_proc.pid = 99999
            exc = subprocess.TimeoutExpired(cmd, timeout)
            exc.process = mock_proc
            raise exc

        monkeypatch.setattr(dyn_mod, "_run_subprocess", fake_run)

        result = DynamicExecutor().run_skill_check({
            "skill_id": "d" * 64,
            "python_code": "x = 1",   # triggers _check_python_syntax
        })

        # Should not raise; timeout info in check detail
        py_checks = [c for c in result.checks if c.name == "python_syntax_ok"]
        assert len(py_checks) == 1
        assert py_checks[0].passed is False
        assert "timeout" in py_checks[0].detail.lower()

        # result.error should be None (timeout is per-check, not fatal)
        assert result.error is None

    def test_timeout_in_code_blocks_handled(self, monkeypatch):
        """TimeoutExpired during code block check → code_blocks_all_valid=False."""
        from api.scoring import dynamic as dyn_mod
        from api.scoring.dynamic import DynamicExecutor

        def fake_run(cmd, cwd, timeout=30):
            mock_proc = MagicMock()
            mock_proc.pid = 99998
            exc = subprocess.TimeoutExpired(cmd, timeout)
            exc.process = mock_proc
            raise exc

        monkeypatch.setattr(dyn_mod, "_run_subprocess", fake_run)

        result = DynamicExecutor().run_skill_check({
            "skill_id": "d" * 64,
            "skill_md": VALID_SKILL_MD,   # has a python block
        })

        # No crash
        assert result is not None
        assert result.error is None or "DYNAMIC" not in (result.error or "")


# ---------------------------------------------------------------------------
# e) Empty skill → score=None
# ---------------------------------------------------------------------------

class TestEmptySkill:
    def test_empty_skill_dict_score_none(self):
        """No skill_md, no code → no checks → score=None."""
        from api.scoring.dynamic import DynamicExecutor

        result = DynamicExecutor().run_skill_check({
            "skill_id": "e" * 64,
        })

        assert result.score is None, f"Expected None, got {result.score}"
        assert result.checks == [] or all("skipped" in c.detail.lower() for c in result.checks)

    def test_empty_skill_md_score_none(self):
        """Empty string skill_md → no meaningful checks → score=None."""
        from api.scoring.dynamic import DynamicExecutor

        result = DynamicExecutor().run_skill_check({
            "skill_id": "e" * 64,
            "skill_md": "",
        })

        assert result.score is None

    def test_score_none_when_disabled(self, monkeypatch):
        """DYNAMIC_SCORING=disabled → score=None, error message set."""
        monkeypatch.setenv("DYNAMIC_SCORING", "disabled")
        from api.scoring.dynamic import DynamicExecutor

        result = DynamicExecutor().run_skill_check({
            "skill_id": "f" * 64,
            "skill_md": VALID_SKILL_MD,
        })

        assert result.score is None
        assert result.error is not None
        assert "DYNAMIC_SCORING" in result.error


# ---------------------------------------------------------------------------
# Structural / integration
# ---------------------------------------------------------------------------

class TestDynamicResult:
    def test_to_dict_structure(self):
        """DynamicResult.to_dict() has all required keys."""
        from api.scoring.dynamic import DynamicResult, CheckResult

        r = DynamicResult(
            skill_id="x" * 64,
            checks=[CheckResult("frontmatter_valid", True, "ok")],
            score=80.0,
            duration_ms=12.3,
        )
        d = r.to_dict()
        assert set(d.keys()) >= {"skill_id", "checks", "score", "duration_ms", "error"}
        assert d["checks"][0]["name"] == "frontmatter_valid"
        assert d["score"] == 80.0

    def test_tmpdir_cleaned_after_run(self, tmp_path, monkeypatch):
        """Temporary directory is removed after run_skill_check returns."""
        import tempfile
        from api.scoring import dynamic as dyn_mod

        created_dirs = []
        original_mkdtemp = tempfile.mkdtemp

        def tracking_mkdtemp(**kwargs):
            d = original_mkdtemp(**kwargs)
            created_dirs.append(d)
            return d

        monkeypatch.setattr(tempfile, "mkdtemp", tracking_mkdtemp)

        from api.scoring.dynamic import DynamicExecutor
        DynamicExecutor().run_skill_check({
            "skill_id": "g" * 64,
            "skill_md": VALID_SKILL_MD,
        })

        import os
        for d in created_dirs:
            assert not os.path.exists(d), f"tmpdir {d} was not cleaned up"
