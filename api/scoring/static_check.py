"""Static Detection Gate — V1E.

Performs deterministic, regex + YAML based checks on skill artifacts
BEFORE any dynamic execution.  Defaults ON (no env-var gate needed).

Architecture
------------
StaticChecker.check(skill) → StaticResult

skill dict keys
  skill_id     str           required
  skill_md     str           SKILL.md full text (may be empty / absent)
  artifacts    list[dict]    each: {kind, content}  (content = text body)
  repo_metadata dict         GitHub / platform metadata

StaticResult
  skill_id    str
  checks      list[CheckDetail]   each: {name, passed, severity, detail}
  verdict     'REVIEWED' | 'QUARANTINE' | 'METADATA_ONLY'
  status      SkillStatus string matching verdict
  risk_flags  list[dict]   [{rule, severity, detail}] — block+warn items
  duration_ms float

Verdict logic (§4.2)
  - any severity='block' check fails  → QUARANTINE  / QUARANTINED
  - no block, structure checks pass   → REVIEWED    / STATIC_REVIEWED
  - no SKILL.md and no script arts    → METADATA_ONLY / METADATA_ONLY
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

Severity = Literal["block", "warn", "info"]
Verdict  = Literal["REVIEWED", "QUARANTINE", "METADATA_ONLY"]

STATUS_MAP: dict[Verdict, str] = {
    "REVIEWED":      "STATIC_REVIEWED",
    "QUARANTINE":    "QUARANTINED",
    "METADATA_ONLY": "METADATA_ONLY",
}


@dataclass
class CheckDetail:
    name:     str
    passed:   bool
    severity: Severity
    detail:   str = ""

    def to_dict(self) -> dict:
        return {
            "name":     self.name,
            "passed":   self.passed,
            "severity": self.severity,
            "detail":   self.detail,
        }


@dataclass
class StaticResult:
    skill_id:    str
    checks:      list[CheckDetail] = field(default_factory=list)
    verdict:     Verdict = "REVIEWED"
    status:      str = "STATIC_REVIEWED"
    risk_flags:  list[dict] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "skill_id":    self.skill_id,
            "checks":      [c.to_dict() for c in self.checks],
            "verdict":     self.verdict,
            "status":      self.status,
            "risk_flags":  self.risk_flags,
            "duration_ms": round(self.duration_ms, 1),
        }


# ---------------------------------------------------------------------------
# Security patterns
# ---------------------------------------------------------------------------

# Block-level dangerous command patterns (exact match via re.search on each
# line of script content, case-insensitive where noted).
_HIGH_RISK_PATTERNS: list[tuple[str, str]] = [
    # rm -rf dangerous targets
    (r"\brm\s+-[^\s]*rf?\s+/",          "rm -rf /"),
    (r"\brm\s+-[^\s]*rf?\s+\*",          "rm -rf *"),
    # fork bomb
    (r":\(\)\s*\{",                       "fork bomb :(){ ... }"),
    # curl|bash / wget|bash pipe execution
    (r"(curl|wget)\s+.+\|\s*(bash|sh)",   "curl/wget pipe to shell"),
    # eval of shell input / variable expansion tricks
    (r"\beval\s*\(",                       "eval("),
    (r"\beval\s+[\"'`\$]",                "eval shell expansion"),
    # sudo in scripts
    (r"\bsudo\b",                          "sudo in script"),
    # world-writable chmod
    (r"\bchmod\s+(a\+w|777|0777)\b",       "chmod 777/a+w"),
    # dd targeting block device / disk wipe
    (r"\bdd\s+.*\bif=",                    "dd if= (disk-level I/O)"),
    # Python exec of downloaded code
    (r"exec\s*\(\s*(urllib|requests|http)", "exec of network fetch"),
]

# Credential leak patterns (warn severity — false-positive prone but important)
# Only fires on patterns that look like real secrets (≥8 non-space chars after =/:)
_CREDENTIAL_PATTERNS: list[tuple[str, str]] = [
    # Generic key/secret/token/password assignments in code
    (
        r'(?i)(api[_\-]?key|secret[_\-]?key|access[_\-]?token|auth[_\-]?token'
        r'|password|passwd|credentials?)\s*[:=]\s*["\']([^"\']{8,})["\']',
        "generic credential assignment",
    ),
    # OpenAI-style keys: sk- prefix
    (r'["\']sk-[A-Za-z0-9]{20,}["\']',   "OpenAI/Anthropic-style API key"),
    # Slack bot tokens
    (r'["\']xoxb-[A-Za-z0-9\-]{20,}["\']', "Slack bot token"),
    # GitHub PAT classic
    (r'["\']ghp_[A-Za-z0-9]{36}["\']',    "GitHub PAT (classic)"),
    # AWS access key id  (starts AKIA)
    (r'\bAKIA[A-Z0-9]{16}\b',              "AWS Access Key ID"),
    # Generic hex/base64 that looks like a secret (≥32 chars, no whitespace)
    (
        r'(?i)(token|secret|key|pass)\s*=\s*["\'][A-Za-z0-9+/=_\-]{32,}["\']',
        "long hex/base64 secret literal",
    ),
]

# Hidden network access patterns (warn only — many legit tools need network)
_NETWORK_PATTERNS: list[tuple[str, str]] = [
    (r"\bimport\s+requests\b",            "import requests"),
    (r"\bimport\s+urllib\b",              "import urllib"),
    (r"\burllib\.request",                "urllib.request"),
    (r"\bhttpx\b",                        "import httpx"),
    (r"http[s]?://(?!localhost|127\.0\.0\.1|example\.com)", "non-local HTTP URL"),
]


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def _check_frontmatter(skill_md: str) -> CheckDetail:
    """a) YAML frontmatter valid + contains name + description."""
    try:
        import yaml
    except ImportError:
        return CheckDetail("structure.frontmatter_valid", True, "warn",
                           "PyYAML not available, check skipped")

    if not skill_md or not skill_md.strip().startswith("---"):
        return CheckDetail("structure.frontmatter_valid", False, "warn",
                           "No YAML frontmatter found")

    lines = skill_md.split("\n")
    fm_lines: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    else:
        return CheckDetail("structure.frontmatter_valid", False, "warn",
                           "Frontmatter block not closed")

    fm_text = "\n".join(fm_lines)
    try:
        parsed = yaml.safe_load(fm_text)
    except Exception as exc:
        return CheckDetail("structure.frontmatter_valid", False, "warn",
                           f"YAML parse error: {exc}")

    if not isinstance(parsed, dict):
        return CheckDetail("structure.frontmatter_valid", False, "warn",
                           "Frontmatter parsed but is not a mapping")

    missing = [k for k in ("name", "description") if k not in parsed]
    if missing:
        return CheckDetail("structure.frontmatter_valid", False, "warn",
                           f"Missing required keys: {missing}")

    return CheckDetail("structure.frontmatter_valid", True, "info",
                       "Frontmatter valid with name+description")


def _check_required_files(skill_md: str) -> CheckDetail:
    """b) SKILL.md presence."""
    if skill_md and skill_md.strip():
        return CheckDetail("structure.required_files", True, "info",
                           "SKILL.md present")
    return CheckDetail("structure.required_files", False, "warn",
                       "SKILL.md missing or empty")


def _check_license(repo_metadata: dict) -> CheckDetail:
    """c) License identification — info-only, UNKNOWN is not a failure."""
    lic = (
        repo_metadata.get("license")
        or repo_metadata.get("license_spdx")
        or "UNKNOWN"
    )
    if isinstance(lic, dict):
        lic = lic.get("spdx_id", "UNKNOWN") or "UNKNOWN"
    lic = str(lic).strip() or "UNKNOWN"
    passed = lic.upper() not in ("UNKNOWN", "NOASSERTION", "NONE", "")
    return CheckDetail(
        "license.identified",
        passed,
        "info",
        f"License: {lic}",
    )


def _check_high_risk_commands(scripts: list[str]) -> CheckDetail:
    """d) Dangerous commands in scripts — severity block."""
    hits: list[str] = []
    for script in scripts:
        for pattern, label in _HIGH_RISK_PATTERNS:
            if re.search(pattern, script, re.IGNORECASE):
                hits.append(label)

    if hits:
        uniq = list(dict.fromkeys(hits))  # deduplicate, preserve order
        return CheckDetail(
            "security.high_risk_command",
            False,
            "block",
            f"Dangerous pattern(s) detected: {'; '.join(uniq)}",
        )
    return CheckDetail("security.high_risk_command", True, "info",
                       "No high-risk commands detected")


def _check_credential_leak(scripts: list[str], skill_md: str) -> CheckDetail:
    """e) Hardcoded credentials in scripts or SKILL.md."""
    all_text = "\n".join(scripts) + "\n" + (skill_md or "")
    hits: list[str] = []
    for pattern, label in _CREDENTIAL_PATTERNS:
        if re.search(pattern, all_text):
            hits.append(label)

    if hits:
        uniq = list(dict.fromkeys(hits))
        return CheckDetail(
            "security.credential_leak",
            False,
            "block",
            f"Potential hardcoded credential(s): {'; '.join(uniq)}",
        )
    return CheckDetail("security.credential_leak", True, "info",
                       "No credential patterns detected")


def _check_hidden_network(scripts: list[str]) -> CheckDetail:
    """f) Network usage in scripts — warn only."""
    hits: list[str] = []
    for script in scripts:
        for pattern, label in _NETWORK_PATTERNS:
            if re.search(pattern, script):
                hits.append(label)

    if hits:
        uniq = list(dict.fromkeys(hits))
        return CheckDetail(
            "security.hidden_network",
            False,
            "warn",
            f"Network usage detected: {'; '.join(uniq)}",
        )
    return CheckDetail("security.hidden_network", True, "info",
                       "No unexpected network access detected")


def _check_doc_completeness(skill_md: str) -> CheckDetail:
    """g) Documentation quality — warn if thin."""
    if not skill_md:
        return CheckDetail("quality.doc_completeness", False, "warn",
                           "No SKILL.md content")

    # Extract description from frontmatter
    desc_len = 0
    try:
        import yaml
        lines = skill_md.split("\n")
        if lines[0].strip() == "---":
            fm_lines = []
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                fm_lines.append(line)
            parsed = yaml.safe_load("\n".join(fm_lines)) or {}
            desc = parsed.get("description", "") or ""
            desc_len = len(desc.strip())
    except Exception:
        pass

    has_usage   = bool(re.search(r"#+\s*(usage|how.to.use|getting.started)",
                                 skill_md, re.IGNORECASE))
    has_example = bool(re.search(r"#+\s*(example|sample|demo)",
                                 skill_md, re.IGNORECASE))
    # Also count ```-fenced example blocks as evidence
    has_code_block = "```" in skill_md

    issues: list[str] = []
    if desc_len < 20:
        issues.append(f"description too short ({desc_len} chars, need ≥20)")
    if not (has_usage or has_example or has_code_block):
        issues.append("no usage/example section or code block")

    if issues:
        return CheckDetail("quality.doc_completeness", False, "warn",
                           "; ".join(issues))
    return CheckDetail("quality.doc_completeness", True, "info",
                       "Documentation complete")


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class StaticChecker:
    """Runs all static checks synchronously and returns a StaticResult.

    Defaults ON — no env-var gate needed (checks are fast + deterministic).
    """

    def check(self, skill: dict) -> StaticResult:
        """Run all checks and return a consolidated StaticResult.

        Parameters
        ----------
        skill : dict
            skill_id     str  (required)
            skill_md     str  (SKILL.md full text, may be absent)
            artifacts    list[dict]  each has 'kind' and 'content' (text)
            repo_metadata dict
        """
        skill_id     = skill.get("skill_id", "unknown")
        skill_md     = skill.get("skill_md", "") or ""
        artifacts    = skill.get("artifacts", []) or []
        repo_metadata = skill.get("repo_metadata", {}) or {}

        result = StaticResult(skill_id=skill_id)
        t0 = time.monotonic()

        # Collect text content from artifacts that are scripts
        script_kinds = {"script", "python", "js", "ts", "bash", "shell",
                        "code", "skill_md"}
        scripts: list[str] = []
        has_artifact = False
        for a in artifacts:
            content = a.get("content", "") or ""
            kind = (a.get("kind", "") or "").lower()
            if content:
                has_artifact = True
                if kind in script_kinds or kind.startswith("script"):
                    scripts.append(content)

        # Normalise skill_md: treat whitespace-only as empty
        skill_md_stripped = skill_md.strip()

        # Also extract code blocks from SKILL.md as scripts to scan
        if skill_md_stripped:
            has_artifact = True  # SKILL.md itself is an artifact
            code_blocks = re.findall(r"```(?:\w*)\n(.*?)```", skill_md, re.DOTALL)
            scripts.extend(code_blocks)

        # --- Run checks ---------------------------------------------------
        result.checks.append(_check_required_files(skill_md_stripped))
        result.checks.append(_check_frontmatter(skill_md_stripped))
        result.checks.append(_check_license(repo_metadata))

        if scripts:
            result.checks.append(_check_high_risk_commands(scripts))
            result.checks.append(_check_credential_leak(scripts, skill_md_stripped))
            result.checks.append(_check_hidden_network(scripts))
        else:
            # No runnable scripts — security checks vacuously pass (info)
            result.checks.append(CheckDetail(
                "security.high_risk_command", True, "info",
                "No script artifacts to scan"))
            result.checks.append(CheckDetail(
                "security.credential_leak", True, "info",
                "No script artifacts to scan"))
            result.checks.append(CheckDetail(
                "security.hidden_network", True, "info",
                "No script artifacts to scan"))

        result.checks.append(_check_doc_completeness(skill_md_stripped))

        result.duration_ms = (time.monotonic() - t0) * 1000

        # --- Determine verdict -------------------------------------------
        result.verdict, result.status, result.risk_flags = \
            self._compute_verdict(result.checks, has_artifact, skill_md_stripped)

        logger.info(
            "static_check skill=%s verdict=%s duration=%.1fms flags=%d",
            skill_id[:12], result.verdict,
            result.duration_ms, len(result.risk_flags),
        )
        return result

    # ------------------------------------------------------------------

    @staticmethod
    def _compute_verdict(
        checks: list[CheckDetail],
        has_artifact: bool,
        skill_md: str,
    ) -> tuple[Verdict, str, list[dict]]:
        """Derive verdict, status, and risk_flags from check results."""
        risk_flags: list[dict] = []

        has_block = False
        for c in checks:
            if not c.passed and c.severity in ("block", "warn"):
                risk_flags.append({
                    "rule":     c.name,
                    "severity": c.severity,
                    "detail":   c.detail,
                })
            if not c.passed and c.severity == "block":
                has_block = True

        # METADATA_ONLY: no SKILL.md and no script artifacts
        if not skill_md.strip() and not has_artifact:
            return "METADATA_ONLY", STATUS_MAP["METADATA_ONLY"], risk_flags

        if has_block:
            return "QUARANTINE", STATUS_MAP["QUARANTINE"], risk_flags

        return "REVIEWED", STATUS_MAP["REVIEWED"], risk_flags
