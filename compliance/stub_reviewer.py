"""Phase 0 stub 复核器：一律不确认任何权利位（保守默认，D-008 安全侧）。"""

from compliance.protocol import RightsDecision
from core.schema.skill import SourceRecord


class StubRightsReviewer:
    def review(self, source_record: SourceRecord) -> RightsDecision:
        return RightsDecision(
            confirmed=False,
            confirmed_bits=(),
            reason="phase0-stub",
            reviewer="stub",
        )
