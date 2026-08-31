"""Static Scanner for L3 (V1A L3).

Scans ACQUIRED skills using pattern-based rules, produces scan_report artifacts,
and transitions to STATIC_REVIEWED or QUARANTINED based on findings.
"""

import uuid
import json
import re
from datetime import datetime, timezone
from dataclasses import dataclass
from api.store import get_skill, list_artifacts, transition_state, put_artifact, put_skill
from api.models import ArtifactRecord


# Severity levels
SEV_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class ScanFinding:
    """扫描发现问题。"""
    rule_id: str
    rule_name: str
    severity: str  # info/low/medium/high/critical
    message: str
    line_number: int | None = None


# Static scan rules (pattern-based)
STATIC_RULES = [
    {
        "rule_id": "S001",
        "rule_name": "hardcoded_secret",
        "severity": "critical",
        "pattern": r"(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][\w\-]{16,}['\"]",
        "message": "Hardcoded secret/token detected"
    },
    {
        "rule_id": "S002",
        "rule_name": "dangerous_shell",
        "severity": "high",
        "pattern": r"(curl|wget).*\|\s*(bash|sh|python)",
        "message": "Dangerous shell pipe pattern (curl|wget | bash/sh)"
    },
    {
        "rule_id": "S003",
        "rule_name": "eval_usage",
        "severity": "high",
        "pattern": r"\beval\s*\(",
        "message": "Use of eval() detected (code injection risk)"
    },
    {
        "rule_id": "S004",
        "rule_name": "sql_injection_risk",
        "severity": "medium",
        "pattern": r"(execute|query)\s*\(\s*['\"].*\+.*['\"]",
        "message": "Potential SQL injection (string concatenation in query)"
    },
    {
        "rule_id": "S005",
        "rule_name": "unsafe_deserialization",
        "severity": "high",
        "pattern": r"(pickle\.loads|yaml\.unsafe_load|eval\s*\()",
        "message": "Unsafe deserialization pattern detected"
    },
]


def run_static_rules(content: str) -> list[ScanFinding]:
    """Run pattern-based static analysis rules.
    
    Args:
        content: SKILL.md content or code
        
    Returns:
        List of findings
    """
    findings = []
    
    lines = content.split("\n")
    for rule in STATIC_RULES:
        pattern = re.compile(rule["pattern"], re.IGNORECASE)
        
        for line_num, line in enumerate(lines, 1):
            if pattern.search(line):
                findings.append(ScanFinding(
                    rule_id=rule["rule_id"],
                    rule_name=rule["rule_name"],
                    severity=rule["severity"],
                    message=rule["message"],
                    line_number=line_num
                ))
    
    return findings


def static_scan_skill(skill_id: str) -> dict:
    """Static scan a skill and transition to STATIC_REVIEWED or QUARANTINED.
    
    Args:
        skill_id: Skill ID to scan
        
    Returns:
        Scan report dict
        
    Raises:
        ValueError: If skill not found or not in ACQUIRED state
    """
    # 1. Get skill
    skill = get_skill(skill_id)
    if skill is None:
        raise ValueError(f"Skill {skill_id} not found")
    if skill.state != "ACQUIRED":
        raise ValueError(f"Skill {skill_id} state={skill.state}, expected ACQUIRED")
    
    # 2. Get skill_md artifact
    md_artifacts = [a for a in list_artifacts(skill_id) if a.kind == "skill_md"]
    if not md_artifacts:
        raise ValueError(f"Skill {skill_id} has no skill_md artifact")
    content = md_artifacts[0].path_or_text or ""
    
    # 3. Run static analysis rules
    findings = run_static_rules(content)
    
    # 4. Determine decision
    severe_findings = [f for f in findings if f.severity in ("high", "critical")]
    has_severe = bool(severe_findings) or skill.high_risk
    
    to_state = "QUARANTINED" if has_severe else "STATIC_REVIEWED"
    reason = "Static scan: severe/high findings" if has_severe else "Static scan: passed"
    
    passed = not has_severe
    
    # 5. Create scan_report artifact
    report = {
        "skill_id": skill_id,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "finding_count": len(findings),
        "severe_count": len(severe_findings),
        "decision": to_state,
        "findings": [
            {
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity,
                "message": f.message,
                "line_number": f.line_number
            }
            for f in findings
        ],
    }
    
    artifact = ArtifactRecord(
        artifact_id=str(uuid.uuid4()),
        skill_id=skill_id,
        kind="scan_report",
        path_or_text=json.dumps(report, ensure_ascii=False, indent=2),
        created_at=datetime.now(timezone.utc),
    )
    put_artifact(artifact)
    
    # 6. Transition state
    transition_state(skill_id, to_state, reason=reason)
    
    # 7. Update artifact_refs
    refreshed = get_skill(skill_id)
    refreshed.artifact_refs.append(artifact.artifact_id)
    put_skill(refreshed)
    
    return report


def scan_all_acquired() -> list[dict]:
    """Scan all ACQUIRED skills.
    
    Returns:
        List of scan reports
    """
    reports = []
    for skill in list_skills(filter_by_state="ACQUIRED"):
        try:
            report = static_scan_skill(skill.skill_id)
            reports.append(report)
        except Exception as e:
            # Log error but continue
            reports.append({
                "skill_id": skill.skill_id,
                "error": str(e),
                "scanned_at": datetime.now(timezone.utc).isoformat(),
            })
    return reports


# Import list_skills here to avoid circular import
from api.store import list_skills
