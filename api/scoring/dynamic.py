"""Lightweight dynamic skill checker (V1D).

Performs subprocess-level syntax / validity checks on skill artifacts:
  a) SKILL.md frontmatter YAML validity
  b) Embedded Python code block syntax (py_compile)
  c) Embedded JS/TS syntax via `node --check`
  d) Code block extraction from SKILL.md and batch syntax check

Opt-in via environment variable:
    DYNAMIC_SCORING=enabled   # must be set explicitly
    DYNAMIC_SCORING=disabled  # (default) → all checks skipped, score=None

Security constraints:
    - No eval/exec of remote code strings
    - All execution via subprocess with hard timeout
    - No network access
    - tempdir cleaned in try/finally
    - Default disabled
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature gate
# ---------------------------------------------------------------------------

def _dynamic_enabled() -> bool:
    return os.environ.get("DYNAMIC_SCORING", "disabled").strip().lower() == "enabled"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class DynamicResult:
    skill_id: str
    checks: list[CheckResult] = field(default_factory=list)
    score: Optional[float] = None   # None = "could not evaluate"
    duration_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "checks": [{"name": c.name, "passed": c.passed, "detail": c.detail}
                       for c in self.checks],
            "score": self.score,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Weights (sum = 100 if all checks apply)
# ---------------------------------------------------------------------------

WEIGHTS: dict[str, float] = {
    "frontmatter_valid":      20.0,
    "python_syntax_ok":       25.0,
    "js_syntax_ok":           15.0,
    "code_blocks_all_valid":  25.0,
    "example_command_runnable": 15.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node_available() -> bool:
    """Return True if `node` executable is on PATH."""
    return shutil.which("node") is not None


def _extract_frontmatter(skill_md: str) -> Optional[str]:
    """Extract YAML frontmatter between leading --- delimiters."""
    if not skill_md.startswith("---"):
        return None
    lines = skill_md.split("\n")
    fm_lines: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return "\n".join(fm_lines)
        fm_lines.append(line)
    return None  # unclosed frontmatter


def _extract_code_blocks(skill_md: str) -> list[tuple[str, str]]:
    """Return list of (lang, code) tuples for fenced code blocks in skill_md."""
    pattern = re.compile(
        r"```(\w*)\n(.*?)```",
        re.DOTALL,
    )
    blocks = []
    for m in pattern.finditer(skill_md):
        lang = m.group(1).strip().lower()
        code = m.group(2)
        blocks.append((lang, code))
    return blocks


def _run_subprocess(cmd: list[str], cwd: str, timeout: int = 30) -> tuple[int, str, str]:
    """Run a subprocess, kill the whole process tree on timeout (Windows-safe).

    Returns (returncode, stdout, stderr).
    Raises nothing — callers should handle all outcomes.
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            # Windows: CREATE_NEW_PROCESS_GROUP so we can kill the tree
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        # Kill the hung process tree
        if exc.process is not None:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(exc.process.pid)],
                        capture_output=True,
                    )
                else:
                    import signal, os as _os
                    _os.killpg(_os.getpgid(exc.process.pid), signal.SIGKILL)
            except Exception:
                pass
        raise


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_frontmatter(skill_md: str) -> CheckResult:
    """Check YAML frontmatter validity."""
    try:
        import yaml
    except ImportError:
        return CheckResult("frontmatter_valid", True, "yaml not available, skipped")

    fm = _extract_frontmatter(skill_md)
    if fm is None:
        return CheckResult("frontmatter_valid", True, "no frontmatter, skipped")

    try:
        yaml.safe_load(fm)
        return CheckResult("frontmatter_valid", True, "YAML valid")
    except Exception as exc:
        return CheckResult("frontmatter_valid", False, f"YAML error: {exc}")


def _check_python_syntax(code: str, tmpdir: str) -> CheckResult:
    """Check Python syntax via py_compile in a subprocess."""
    src = os.path.join(tmpdir, "_check_py.py")
    try:
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
    except OSError as e:
        return CheckResult("python_syntax_ok", False, f"write error: {e}")

    try:
        rc, out, err = _run_subprocess(
            [sys.executable, "-m", "py_compile", src],
            cwd=tmpdir,
        )
        if rc == 0:
            return CheckResult("python_syntax_ok", True, "syntax ok")
        return CheckResult("python_syntax_ok", False, err.strip() or out.strip())
    except subprocess.TimeoutExpired:
        return CheckResult("python_syntax_ok", False, "timeout")
    except Exception as e:
        return CheckResult("python_syntax_ok", False, str(e))


def _check_js_syntax(code: str, tmpdir: str) -> Optional[CheckResult]:
    """Check JS/TS syntax via `node --check`. Returns None if node unavailable."""
    if not _node_available():
        return None

    src = os.path.join(tmpdir, "_check_js.js")
    try:
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
    except OSError as e:
        return CheckResult("js_syntax_ok", False, f"write error: {e}")

    try:
        rc, out, err = _run_subprocess(
            ["node", "--check", src],
            cwd=tmpdir,
        )
        if rc == 0:
            return CheckResult("js_syntax_ok", True, "syntax ok")
        return CheckResult("js_syntax_ok", False, err.strip() or out.strip())
    except subprocess.TimeoutExpired:
        return CheckResult("js_syntax_ok", False, "timeout")
    except Exception as e:
        return CheckResult("js_syntax_ok", False, str(e))


def _check_code_blocks(skill_md: str, tmpdir: str) -> CheckResult:
    """Extract and syntax-check all code blocks in SKILL.md."""
    blocks = _extract_code_blocks(skill_md)
    py_blocks = [(lang, code) for lang, code in blocks if lang in ("python", "py", "")]
    js_blocks = [(lang, code) for lang, code in blocks if lang in ("javascript", "js", "typescript", "ts")]

    if not py_blocks and not js_blocks:
        return CheckResult("code_blocks_all_valid", True, "no code blocks, skipped")

    failures: list[str] = []
    passed_count = 0

    for i, (lang, code) in enumerate(py_blocks):
        r = _check_python_syntax(code, tmpdir)
        if r.passed:
            passed_count += 1
        else:
            failures.append(f"block[py#{i}]: {r.detail}")

    if _node_available():
        for i, (lang, code) in enumerate(js_blocks):
            r = _check_js_syntax(code, tmpdir)
            if r and r.passed:
                passed_count += 1
            elif r:
                failures.append(f"block[js#{i}]: {r.detail}")

    total = len(py_blocks) + (len(js_blocks) if _node_available() else 0)
    if failures:
        return CheckResult(
            "code_blocks_all_valid",
            False,
            f"{len(failures)}/{total} blocks failed: {'; '.join(failures[:3])}",
        )
    return CheckResult(
        "code_blocks_all_valid",
        True,
        f"all {total} block(s) ok",
    )


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

class DynamicExecutor:
    """Runs a battery of static/dynamic checks on a skill artifact bundle.

    All execution is sandboxed: subprocess with timeout, no eval/exec,
    tmpdir cleaned after each run, no network.

    Enable via DYNAMIC_SCORING=enabled (disabled by default).
    """

    def run_skill_check(self, skill: dict) -> DynamicResult:
        """Run all applicable checks for ``skill``.

        Parameters
        ----------
        skill : dict
            Must contain at least ``skill_id``.
            Optional keys:
              - ``skill_md`` (str) — SKILL.md text
              - ``artifacts`` (list[dict]) — each with ``kind`` and ``content``
              - ``python_code`` (str) — inline Python snippet to check

        Returns
        -------
        DynamicResult
            Never raises; exceptions are captured in ``DynamicResult.error``.
        """
        skill_id = skill.get("skill_id", "unknown")
        result = DynamicResult(skill_id=skill_id)

        if not _dynamic_enabled():
            result.error = "DYNAMIC_SCORING not enabled"
            return result

        t0 = time.monotonic()
        tmpdir = tempfile.mkdtemp(prefix="dyn_check_")
        try:
            self._run_checks(skill, tmpdir, result)
        except Exception as exc:
            result.error = f"unexpected error: {exc}"
            logger.exception("DynamicExecutor unexpected error for %s", skill_id)
        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass
            result.duration_ms = (time.monotonic() - t0) * 1000

        # Compute score
        result.score = self._compute_score(result.checks)
        return result

    # ------------------------------------------------------------------

    def _run_checks(self, skill: dict, tmpdir: str, result: DynamicResult) -> None:
        skill_md: str = skill.get("skill_md", "") or ""
        python_code: str = skill.get("python_code", "") or ""
        js_code: str = skill.get("js_code", "") or ""

        # a) Frontmatter
        if skill_md:
            result.checks.append(_check_frontmatter(skill_md))

        # b) Python syntax (inline)
        if python_code:
            result.checks.append(_check_python_syntax(python_code, tmpdir))

        # c) JS syntax (inline)
        if js_code:
            r = _check_js_syntax(js_code, tmpdir)
            if r is not None:
                result.checks.append(r)

        # d) Code blocks from SKILL.md
        if skill_md:
            result.checks.append(_check_code_blocks(skill_md, tmpdir))

    def _compute_score(self, checks: list[CheckResult]) -> Optional[float]:
        """Weighted sum over applicable checks.  Returns None if no checks ran."""
        if not checks:
            return None

        # Only count checks that were not "skipped"
        active = [c for c in checks if "skipped" not in c.detail.lower()]
        if not active:
            return None

        total_weight = 0.0
        earned_weight = 0.0

        # Map check names to weights
        for c in active:
            w = WEIGHTS.get(c.name, 10.0)  # default 10 for unlisted
            total_weight += w
            if c.passed:
                earned_weight += w

        if total_weight == 0:
            return None

        return round((earned_weight / total_weight) * 100, 1)
