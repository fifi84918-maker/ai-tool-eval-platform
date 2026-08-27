"""结构与规范检查（PRD 12.2-A 的元数据/目录树级子集）。

输入是已注入的清单字段与相对路径列表（假想解包目录树），不读网络、
不读磁盘、不读制品正文。

TODO(字段口径)：PRD 12.2-A 只要求"名称、描述、触发条件"存在且
Frontmatter 有效，未规定字段的确切键名（name/description/triggers?
x-permissions 亦非 PRD 用词）。当前采用 name/description 为必填、
triggers 缺失记 WARN；键名待 Canonical Skill Schema（Phase 0 交付物）
定稿后统一修订。
"""

from collections.abc import Mapping, Sequence
from typing import Any

from analyzer.rules import RuleFinding, RuleId, RuleOutcome

_REQUIRED_FIELDS = ("name", "description")
_RECOMMENDED_FIELDS = ("triggers",)
_PLACEHOLDER_MARKERS = ("todo", "tbd", "fixme", "changeme", "xxx")


def check_structure(
    manifest_fields: Mapping[str, Any] | None,
    file_paths: Sequence[str] | None,
) -> tuple[RuleFinding, ...]:
    """结构检查。manifest_fields=None 表示清单不可得（NEED_INFO）。"""
    findings: list[RuleFinding] = []

    # SKILL.md 存在性（基于注入的目录树）
    if file_paths is None:
        findings.append(
            RuleFinding(
                RuleId.STRUCT_SKILL_MD_PRESENT,
                RuleOutcome.NEED_INFO,
                "no file listing provided; cannot verify SKILL.md presence",
            )
        )
    elif any(p.replace("\\", "/").split("/")[-1].lower() == "skill.md" for p in file_paths):
        findings.append(
            RuleFinding(
                RuleId.STRUCT_SKILL_MD_PRESENT, RuleOutcome.PASS, "SKILL.md found"
            )
        )
    else:
        findings.append(
            RuleFinding(
                RuleId.STRUCT_SKILL_MD_PRESENT,
                RuleOutcome.FAIL,
                "SKILL.md not found in artifact file listing",
            )
        )

    # Frontmatter 必填/建议字段
    if manifest_fields is None:
        findings.append(
            RuleFinding(
                RuleId.STRUCT_FRONTMATTER_FIELDS,
                RuleOutcome.NEED_INFO,
                "no manifest fields provided",
            )
        )
    else:
        missing = [f for f in _REQUIRED_FIELDS if not manifest_fields.get(f)]
        if missing:
            findings.append(
                RuleFinding(
                    RuleId.STRUCT_FRONTMATTER_FIELDS,
                    RuleOutcome.FAIL,
                    f"missing required fields: {', '.join(missing)}",
                )
            )
        else:
            recommended_missing = [
                f for f in _RECOMMENDED_FIELDS if not manifest_fields.get(f)
            ]
            findings.append(
                RuleFinding(
                    RuleId.STRUCT_FRONTMATTER_FIELDS,
                    RuleOutcome.WARN
                    if recommended_missing
                    else RuleOutcome.PASS,
                    "required fields present"
                    + (
                        f"; recommended missing: {', '.join(recommended_missing)}"
                        if recommended_missing
                        else ""
                    ),
                )
            )

    # 不可移植路径（绝对路径 / 作者本机路径特征）
    if file_paths is not None:
        bad = [
            p
            for p in file_paths
            if p.startswith(("/", "~"))
            or (len(p) >= 3 and p[1] == ":" and (p[2] == "\\" or p[2] == "/"))
        ]
        findings.append(
            RuleFinding(
                RuleId.STRUCT_PORTABLE_PATHS,
                RuleOutcome.WARN if bad else RuleOutcome.PASS,
                f"non-portable paths: {', '.join(bad)}" if bad else "paths portable",
            )
        )

    # 未完成占位符（仅扫描清单字段值，不扫正文）
    if manifest_fields is not None:
        hits = [
            key
            for key, value in manifest_fields.items()
            if isinstance(value, str)
            and any(marker in value.lower() for marker in _PLACEHOLDER_MARKERS)
        ]
        findings.append(
            RuleFinding(
                RuleId.STRUCT_PLACEHOLDERS,
                RuleOutcome.WARN if hits else RuleOutcome.PASS,
                f"placeholder markers in fields: {', '.join(hits)}"
                if hits
                else "no placeholder markers in manifest fields",
            )
        )

    return tuple(findings)
