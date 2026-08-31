"""Compatibility Judgment Service — PRD §6.3.

Dual-path analysis:
  ① Portable Core extraction  (deterministic, YAML/regex)
  ② Host Overlay analysis      (gap detection vs target host)
  → 7-state CompatStatus

CompatStatus precedence (highest wins):
  BLOCKED > INCOMPATIBLE > PENDING_VERIFICATION > COMPATIBLE_WITH_ADAPTER > COMPATIBLE
  (UNKNOWN = default when evidence is insufficient; PARTIAL = partial structure)

Hard constraint (§6.3):
  **No load evidence → NEVER mark COMPATIBLE.**
  Must be PENDING_VERIFICATION or lower.

Load evidence sources:
  - dynamic_result with example_command_runnable=True  (dynamic smoke)
  - caller explicitly passes has_load_evidence=True     (manual or CI)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CompatStatus = Literal[
    "COMPATIBLE",
    "COMPATIBLE_WITH_ADAPTER",
    "PARTIAL",
    "UNKNOWN",
    "INCOMPATIBLE",
    "PENDING_VERIFICATION",
    "BLOCKED",
]

# Ordinal priority for comparison (higher = stronger signal)
_STATUS_PRIORITY: dict[str, int] = {
    "UNKNOWN":                 0,
    "PARTIAL":                 1,
    "COMPATIBLE":              2,
    "COMPATIBLE_WITH_ADAPTER": 3,
    "PENDING_VERIFICATION":    4,
    "INCOMPATIBLE":            5,
    "BLOCKED":                 6,
}

AdaptationCost = Literal["low", "medium", "high"]

# Host Overlay items that must be checked (§6.3)
HOST_OVERLAY_ITEMS: list[str] = [
    "directory_convention",      # 目录位置约定
    "frontmatter_extensions",    # Frontmatter 扩展字段
    "allowed_tools",             # allowed-tools 声明
    "hooks",                     # 生命周期 hooks
    "sub_agents",                # 子 Agent 协议
    "ui_components",             # UI 组件声明
    "connector_ids",             # 内置连接器 ID
    "proprietary_variables",     # 专有变量/运行时
    "platform_approval",         # 平台审批要求
]

# How many missing items map to each cost tier
_COST_MAP = {0: "low", 1: "low", 2: "medium", 3: "medium"}  # 4+ → "high"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class PortableCoreProfile:
    """Extracted portable core from skill artifacts."""
    name:         Optional[str] = None
    description:  Optional[str] = None
    scripts:      list[str]     = field(default_factory=list)   # entry filenames/cmds
    references:   list[str]     = field(default_factory=list)   # URLs, asset refs
    inputs:       list[str]     = field(default_factory=list)   # declared input params
    outputs:      list[str]     = field(default_factory=list)   # declared output params
    dependencies: list[str]     = field(default_factory=list)   # deps from lock files
    permissions:  list[str]     = field(default_factory=list)   # allowed-tools / scopes

    @property
    def is_complete(self) -> bool:
        """True if at minimum name + description present."""
        return bool(self.name and self.description)

    @property
    def has_entry_point(self) -> bool:
        """True if at least one script or reference is found."""
        return bool(self.scripts or self.references)

    def to_dict(self) -> dict:
        return {
            "name":         self.name,
            "description":  self.description,
            "scripts":      self.scripts,
            "references":   self.references,
            "inputs":       self.inputs,
            "outputs":      self.outputs,
            "dependencies": self.dependencies,
            "permissions":  self.permissions,
            "is_complete":  self.is_complete,
            "has_entry_point": self.has_entry_point,
        }


@dataclass
class HostOverlayReport:
    """Gap analysis between Portable Core and target host requirements."""
    missing_items:    list[str]    = field(default_factory=list)
    present_items:    list[str]    = field(default_factory=list)
    adaptation_cost:  AdaptationCost = "low"

    def to_dict(self) -> dict:
        return {
            "missing_items":   self.missing_items,
            "present_items":   self.present_items,
            "adaptation_cost": self.adaptation_cost,
        }


@dataclass
class CompatEvidence:
    has_load_evidence: bool  = False
    source:            str   = "static_only"   # static_only / dynamic_smoke / manual

    def to_dict(self) -> dict:
        return {
            "has_load_evidence": self.has_load_evidence,
            "source":            self.source,
        }


@dataclass
class CompatResult:
    skill_id:        str
    compat_status:   CompatStatus            = "UNKNOWN"
    portable_core:   PortableCoreProfile     = field(default_factory=PortableCoreProfile)
    host_overlay:    HostOverlayReport       = field(default_factory=HostOverlayReport)
    evidence:        CompatEvidence          = field(default_factory=CompatEvidence)
    recommendations: list[str]              = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "skill_id":        self.skill_id,
            "compat_status":   self.compat_status,
            "portable_core":   self.portable_core.to_dict(),
            "host_overlay":    self.host_overlay.to_dict(),
            "evidence":        self.evidence.to_dict(),
            "recommendations": self.recommendations,
        }


# ---------------------------------------------------------------------------
# Portable Core extractor
# ---------------------------------------------------------------------------

def _extract_portable_core(skill_md: str, artifacts: list[dict]) -> PortableCoreProfile:
    """Extract portable core from SKILL.md + artifact list.

    Uses YAML frontmatter + section headings + code blocks (deterministic).
    """
    profile = PortableCoreProfile()

    # --- Frontmatter ----------------------------------------------------------
    if skill_md and skill_md.strip().startswith("---"):
        try:
            import yaml
            lines = skill_md.split("\n")
            fm_lines: list[str] = []
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                fm_lines.append(line)
            fm = yaml.safe_load("\n".join(fm_lines)) or {}
        except Exception:
            fm = {}
    else:
        fm = {}

    profile.name        = fm.get("name") or None
    profile.description = fm.get("description") or None

    # Permissions from frontmatter
    allowed = fm.get("allowed-tools") or fm.get("allowed_tools") or []
    if isinstance(allowed, str):
        allowed = [allowed]
    if isinstance(allowed, list):
        profile.permissions.extend(str(x) for x in allowed)

    # Dependencies (requirements / package.json style)
    deps = fm.get("dependencies") or fm.get("requirements") or []
    if isinstance(deps, str):
        deps = [deps]
    if isinstance(deps, list):
        profile.dependencies.extend(str(x) for x in deps)

    # Inputs / outputs declared in frontmatter
    for field_name, target in (("inputs", profile.inputs), ("outputs", profile.outputs)):
        declared = fm.get(field_name) or []
        if isinstance(declared, str):
            declared = [declared]
        if isinstance(declared, list):
            target.extend(str(x) for x in declared)

    # --- SKILL.md body analysis -----------------------------------------------
    if skill_md:
        # Scripts: lines that look like commands or file references
        for m in re.finditer(
            r"(?:run|execute|python|node|bash|sh|npx|pip)\s+([\w./-]+\.?\w*)",
            skill_md, re.IGNORECASE,
        ):
            entry = m.group(1).strip()
            if entry and entry not in profile.scripts:
                profile.scripts.append(entry)

        # References: URLs and asset names
        for m in re.finditer(r"https?://\S+", skill_md):
            url = m.group(0).rstrip(")")
            if url not in profile.references:
                profile.references.append(url)

        # Input/output params from ## Parameters / ## Inputs sections
        if not profile.inputs:
            in_section = False
            for line in skill_md.split("\n"):
                if re.match(r"^#+\s*(inputs?|parameters?|args?)", line, re.IGNORECASE):
                    in_section = True
                    continue
                if in_section:
                    if line.startswith("#"):
                        in_section = False
                    m = re.match(r"\s*[-*]\s*`?(\w+)`?", line)
                    if m:
                        profile.inputs.append(m.group(1))

    # --- Artifacts (scripts, package files) ------------------------------------
    for a in artifacts:
        kind    = (a.get("kind") or "").lower()
        content = a.get("content", "") or ""
        name_   = (a.get("name") or "").lower()

        if kind in ("script", "python", "js", "ts", "bash", "shell") or \
           name_.endswith((".py", ".js", ".ts", ".sh")):
            # Use the kind/name as the entry point reference
            entry = a.get("name") or kind
            if entry and entry not in profile.scripts:
                profile.scripts.append(entry)

        # Dependencies from requirements.txt / package.json
        if kind == "requirements" or name_ in ("requirements.txt",):
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    pkg = re.split(r"[>=<! ]", line)[0].strip()
                    if pkg and pkg not in profile.dependencies:
                        profile.dependencies.append(pkg)

        if kind == "package_json" or name_ == "package.json":
            try:
                import json
                pkg_data = json.loads(content)
                deps_dict = pkg_data.get("dependencies", {})
                for dep_name in deps_dict:
                    if dep_name not in profile.dependencies:
                        profile.dependencies.append(dep_name)
            except Exception:
                pass

    return profile


# ---------------------------------------------------------------------------
# Host Overlay analyzer
# ---------------------------------------------------------------------------

def _analyze_host_overlay(skill_md: str, portable_core: PortableCoreProfile) -> HostOverlayReport:
    """Detect which Host Overlay items are present or missing.

    Checks SKILL.md text + portable_core for signals of each overlay item.
    """
    present: list[str]  = []
    missing: list[str]  = []

    md_lower = skill_md.lower() if skill_md else ""

    # 1. directory_convention  — any relative path reference in md
    if re.search(r"(\.\/|\/\w+\/|~\/)", skill_md or ""):
        present.append("directory_convention")
    else:
        missing.append("directory_convention")

    # 2. frontmatter_extensions — frontmatter beyond name/description/version
    _base_keys = {"name", "description", "version", "license"}
    has_ext = False
    if skill_md and skill_md.strip().startswith("---"):
        try:
            import yaml
            lines = skill_md.split("\n")
            fm_lines = []
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                fm_lines.append(line)
            fm = yaml.safe_load("\n".join(fm_lines)) or {}
            has_ext = bool(set(fm.keys()) - _base_keys)
        except Exception:
            pass
    if has_ext:
        present.append("frontmatter_extensions")
    else:
        missing.append("frontmatter_extensions")

    # 3. allowed_tools — explicit permission declaration
    if portable_core.permissions or re.search(r"allowed.tool", md_lower):
        present.append("allowed_tools")
    else:
        missing.append("allowed_tools")

    # 4. hooks — lifecycle hooks (onStart, onError, etc.)
    if re.search(r"\bhooks?\b|\bon_?start\b|\bon_?end\b|\bon_?error\b", md_lower):
        present.append("hooks")
    else:
        missing.append("hooks")

    # 5. sub_agents — sub-agent orchestration
    if re.search(r"\bsub[_-]?agent|\bagent\s+spawn|\bspawn\s+agent\b", md_lower):
        present.append("sub_agents")
    else:
        missing.append("sub_agents")

    # 6. ui_components — any UI component references
    if re.search(r"\bui\b|\bcomponent|\bwidget|\bpanel\b|\bsidebar\b", md_lower):
        present.append("ui_components")
    else:
        missing.append("ui_components")

    # 7. connector_ids — built-in connector declarations
    if re.search(r"\bconnector[_-]?id|\bconnector\s*[:=]", md_lower):
        present.append("connector_ids")
    else:
        missing.append("connector_ids")

    # 8. proprietary_variables — runtime-specific variable syntax ${VAR} or @{VAR}
    if re.search(r"\$\{[A-Z_]+\}|@\{[A-Z_]+\}", skill_md or ""):
        present.append("proprietary_variables")
    else:
        missing.append("proprietary_variables")

    # 9. platform_approval — any mention of review/approval/publish flow
    if re.search(r"\bapproval\b|\bapprove\b|\breview\b|\bpublish\b", md_lower):
        present.append("platform_approval")
    else:
        missing.append("platform_approval")

    # Adaptation cost
    n = len(missing)
    if n >= 4:
        cost: AdaptationCost = "high"
    elif n >= 2:
        cost = "medium"
    else:
        cost = "low"

    return HostOverlayReport(
        missing_items=missing,
        present_items=present,
        adaptation_cost=cost,
    )


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

def _determine_status(
    portable_core: PortableCoreProfile,
    host_overlay: HostOverlayReport,
    evidence: CompatEvidence,
    static_result=None,
) -> tuple[CompatStatus, list[str]]:
    """Return (compat_status, recommendations).

    Priority (highest wins):
      BLOCKED > INCOMPATIBLE > PENDING_VERIFICATION > COMPATIBLE_WITH_ADAPTER > COMPATIBLE
    UNKNOWN = default when evidence is insufficient.
    PARTIAL = portable core partially complete (has some elements but incomplete structure).

    Hard constraint (§6.3):
      No load evidence → cannot be COMPATIBLE.
      Without evidence: COMPATIBLE_WITH_ADAPTER → PENDING_VERIFICATION.
    """
    recommendations: list[str] = []

    # ── BLOCKED: static_result has a block risk_flag ────────────────────────
    if static_result is not None:
        risk_flags = getattr(static_result, "risk_flags", [])
        if any(f.get("severity") == "block" for f in risk_flags):
            return "BLOCKED", ["Remove dangerous patterns before deployment"]

    # ── UNKNOWN: no content at all ──────────────────────────────────────────
    if not portable_core.is_complete and not portable_core.has_entry_point:
        return "UNKNOWN", ["Provide SKILL.md with name, description, and usage"]

    # ── INCOMPATIBLE: has metadata but absolutely no entry point ────────────
    if portable_core.is_complete and not portable_core.has_entry_point:
        recommendations.append("Add entry point script or usage command")
        return "INCOMPATIBLE", recommendations

    # ── Has content + entry point: apply overlay + evidence logic ───────────
    n_missing = len(host_overlay.missing_items)

    # Build overlay recommendations (top items first)
    overlay_recs: list[str] = []
    for item in host_overlay.missing_items[:3]:
        overlay_recs.append(f"Add {item.replace('_', '-')} declaration")
    if n_missing > 3:
        overlay_recs.append(
            f"Review {n_missing - 3} additional overlay items"
        )

    # Evidence check recommendation
    smoke_rec = "Run smoke test to confirm compatibility"
    pv_rec    = "Run smoke test to promote from PENDING_VERIFICATION to COMPATIBLE"

    if n_missing == 0:
        # Perfect overlay coverage
        if evidence.has_load_evidence:
            return "COMPATIBLE", recommendations
        else:
            recommendations.append(pv_rec)
            return "PENDING_VERIFICATION", recommendations

    elif n_missing <= 3:
        # Few overlay items missing
        recommendations.extend(overlay_recs)
        if evidence.has_load_evidence:
            return "COMPATIBLE_WITH_ADAPTER", recommendations
        else:
            # Hard constraint: cannot be COMPATIBLE_WITH_ADAPTER without evidence
            recommendations.append(smoke_rec)
            return "PENDING_VERIFICATION", recommendations

    else:
        # Many overlay items missing
        recommendations.extend(overlay_recs)
        if evidence.has_load_evidence:
            # With evidence but many gaps → still COMPATIBLE_WITH_ADAPTER
            # (high adaptation cost, but structure is workable)
            return "COMPATIBLE_WITH_ADAPTER", recommendations
        else:
            # No evidence + many gaps → PENDING_VERIFICATION
            # (PARTIAL reserved for genuinely partial/broken structure)
            recommendations.append(smoke_rec)
            return "PENDING_VERIFICATION", recommendations


# ---------------------------------------------------------------------------
# Main analyzer
# ---------------------------------------------------------------------------

class CompatAnalyzer:
    """Dual-path compatibility analyzer (PRD §6.3).

    No LLM calls — deterministic YAML/regex only.

    Parameters
    ----------
    skill : dict
        skill_id, skill_md, artifacts, [optional] repo_metadata
    static_result : StaticResult | None
    dynamic_result : DynamicResult | None
        If provided and example_command_runnable check passed → load evidence.
    has_load_evidence : bool
        Caller-supplied override (manual / CI test).
    """

    def analyze(
        self,
        skill: dict,
        static_result=None,
        dynamic_result=None,
        has_load_evidence: bool = False,
    ) -> CompatResult:
        skill_id  = skill.get("skill_id", "unknown")
        skill_md  = skill.get("skill_md", "") or ""
        artifacts = skill.get("artifacts", []) or []

        result = CompatResult(skill_id=skill_id)

        # ── ① Portable Core extraction ────────────────────────────────────
        portable_core = _extract_portable_core(skill_md, artifacts)
        result.portable_core = portable_core

        # ── ② Host Overlay analysis ───────────────────────────────────────
        host_overlay = _analyze_host_overlay(skill_md, portable_core)
        result.host_overlay = host_overlay

        # ── Evidence determination ────────────────────────────────────────
        evidence = CompatEvidence(has_load_evidence=False, source="static_only")

        if has_load_evidence:
            evidence.has_load_evidence = True
            evidence.source = "manual"
        elif dynamic_result is not None:
            # Check for example_command_runnable in dynamic checks
            checks = getattr(dynamic_result, "checks", [])
            for c in checks:
                name   = getattr(c, "name", "")
                passed = getattr(c, "passed", False)
                if "example_command" in name and passed:
                    evidence.has_load_evidence = True
                    evidence.source = "dynamic_smoke"
                    break
            # Also accept: dynamic_result has a real score (syntax check passed)
            dyn_score = getattr(dynamic_result, "score", None)
            if dyn_score is not None and dyn_score > 0:
                # Syntax checks passed → weak smoke evidence (not a full run)
                # This still does NOT count as load evidence per §6.3 hard rule.
                # Only example_command_runnable check qualifies.
                pass

        result.evidence = evidence

        # ── Verdict ───────────────────────────────────────────────────────
        status, recs = _determine_status(
            portable_core, host_overlay, evidence, static_result
        )
        result.compat_status   = status
        result.recommendations = recs

        logger.info(
            "compat_analyze skill=%s status=%s overlay_missing=%d evidence=%s",
            skill_id[:12], status, len(host_overlay.missing_items),
            evidence.source,
        )
        return result
