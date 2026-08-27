"""依赖清单规则：声明依赖的格式与来源可信信号。不递归解析 lockfile。

期望输入为清单中的声明依赖列表（字符串或 {name, source} 映射）；
None 表示未提供依赖信息。
"""

from collections.abc import Mapping, Sequence
from typing import Any

from analyzer.rules import RuleFinding, RuleId, RuleOutcome

# 声明式可信来源前缀（注册表/官方源）；直接 URL/本地路径视为需复核
_TRUSTED_SOURCE_PREFIXES = ("pypi:", "npm:", "apt:", "brew:", "builtin:")
_UNTRUSTED_MARKERS = ("http://", "file://", "\\\\", "../")


def check_deps(
    declared_deps: Sequence[str | Mapping[str, Any]] | None,
) -> tuple[RuleFinding, ...]:
    if declared_deps is None:
        return (
            RuleFinding(
                RuleId.DEPS_MANIFEST_FORMAT,
                RuleOutcome.NEED_INFO,
                "no dependency declaration available",
            ),
        )

    findings: list[RuleFinding] = []
    malformed: list[str] = []
    untrusted: list[str] = []

    for i, dep in enumerate(declared_deps):
        if isinstance(dep, str):
            name, source = dep.strip(), ""
        elif isinstance(dep, Mapping) and isinstance(dep.get("name"), str):
            name = dep["name"].strip()
            source = str(dep.get("source") or "")
        else:
            malformed.append(f"#{i}")
            continue
        if not name:
            malformed.append(f"#{i}")
            continue
        target = source or name
        if any(marker in target for marker in _UNTRUSTED_MARKERS):
            untrusted.append(name or f"#{i}")
        elif source and not source.startswith(_TRUSTED_SOURCE_PREFIXES):
            untrusted.append(name)

    findings.append(
        RuleFinding(
            RuleId.DEPS_MANIFEST_FORMAT,
            RuleOutcome.FAIL if malformed else RuleOutcome.PASS,
            f"malformed dependency entries: {', '.join(malformed)}"
            if malformed
            else f"dependency manifest well-formed ({len(declared_deps)} entries)",
        )
    )
    findings.append(
        RuleFinding(
            RuleId.DEPS_UNTRUSTED_SOURCE,
            RuleOutcome.WARN if untrusted else RuleOutcome.PASS,
            f"dependencies from unvetted sources: {', '.join(sorted(untrusted))}"
            if untrusted
            else "all dependency sources look declarative/trusted",
        )
    )
    return tuple(findings)
