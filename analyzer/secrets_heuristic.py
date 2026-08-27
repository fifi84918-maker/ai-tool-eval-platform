"""密钥/凭证启发式（仅元数据级）：正则扫描清单字段值与路径名。

不扫制品正文/大文件。若后续需要扫文本内容，只接受注入的
(name, text) 迭代器（scan_injected_texts）；PoC 阶段调用方可不传。
"""

import re
from collections.abc import Iterable, Mapping
from typing import Any

from analyzer.rules import RuleFinding, RuleId, RuleOutcome

# 常见凭证特征：AWS AKIA、私钥头、通用 token/密码赋值、长 hex/base64 样值
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "credential_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token|passwd|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9+/_\-]{8,}"
        ),
    ),
)

_SUSPICIOUS_PATH = re.compile(r"(?i)(^|/)(\.env(\..+)?|id_rsa|.*\.pem|credentials(\..+)?)$")


def _scan_text(origin: str, text: str) -> list[str]:
    return [f"{name}@{origin}" for name, pattern in _PATTERNS if pattern.search(text)]


def check_secrets_heuristic(
    manifest_fields: Mapping[str, Any] | None,
    file_paths: Iterable[str] | None,
    injected_texts: Iterable[tuple[str, str]] | None = None,
) -> tuple[RuleFinding, ...]:
    """返回单条汇总 finding。命中 → FAIL（示例密钥/硬编码凭证候选信号）。"""
    hits: list[str] = []

    if manifest_fields:
        for key, value in manifest_fields.items():
            if isinstance(value, str):
                hits.extend(_scan_text(f"manifest:{key}", value))

    if file_paths is not None:
        hits.extend(
            f"suspicious_path@{p}"
            for p in file_paths
            if _SUSPICIOUS_PATH.search(p.replace("\\", "/"))
        )

    if injected_texts is not None:
        for name, text in injected_texts:
            hits.extend(_scan_text(f"text:{name}", text))

    if manifest_fields is None and file_paths is None and injected_texts is None:
        return (
            RuleFinding(
                RuleId.SECRET_METADATA_HEURISTIC,
                RuleOutcome.NEED_INFO,
                "no metadata available for secret heuristics",
            ),
        )

    if hits:
        return (
            RuleFinding(
                RuleId.SECRET_METADATA_HEURISTIC,
                RuleOutcome.FAIL,
                f"credential heuristics hit: {', '.join(sorted(hits))}",
            ),
        )
    return (
        RuleFinding(
            RuleId.SECRET_METADATA_HEURISTIC,
            RuleOutcome.PASS,
            "no credential heuristics hit at metadata level",
        ),
    )
