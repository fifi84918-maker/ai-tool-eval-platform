"""权利复核协议：对 SourceRecord 的三个许可判断位给出复核结论。"""

from dataclasses import dataclass
from typing import Literal, Protocol

from core.schema.skill import SourceRecord


@dataclass(frozen=True)
class RightsDecision:
    """一次权利复核结论。

    confirmed_bits 为被确认的权利位名（如 "allow_internal_test"）；
    confirmed=False 时应为空元组。
    """

    confirmed: bool
    confirmed_bits: tuple[str, ...]
    reason: str
    reviewer: Literal["auto", "human", "stub"]


class RightsReviewer(Protocol):
    """权利复核方：自动规则、人工队列或 stub。"""

    def review(self, source_record: SourceRecord) -> RightsDecision: ...
