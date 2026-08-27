"""对外数据策略：内容字段剔除 + 证据等级钳制。

D-005/PRD 19.3：公开面不得出现 Skill 正文、脚本源码、二进制、密钥。
D-008：本期数据源未经隔离实测，证据等级最高 D（跑过形状验证）或 U。
"""

from typing import Any

# 命中即剔除的键名（递归；防御性兜底，DTO 白名单是第一道防线）
_FORBIDDEN_KEYS = frozenset(
    {
        "skill_md_body",
        "script_text",
        "source_code",
        "content",
        "body",
        "raw_text",
        "tarball_bytes",
        "api_key",
        "secret",
        "token",
        "password",
        "credentials",
    }
)

_ALLOWED_GRADES = frozenset({"D", "U"})


def scrub(value: Any) -> Any:
    """递归剔除禁止键；对字典/列表深拷贝，标量原样返回。"""
    if isinstance(value, dict):
        return {
            k: scrub(v) for k, v in value.items() if k.lower() not in _FORBIDDEN_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [scrub(item) for item in value]
    return value


def clamp_evidence_grade(grade: str | None) -> str:
    """本期任何等级都钳到 D/U：给 D 及以上一律降为 D，缺失记 U。"""
    if grade is None:
        return "U"
    return grade if grade in _ALLOWED_GRADES else "D"
