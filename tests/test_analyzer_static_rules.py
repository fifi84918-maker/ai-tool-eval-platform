"""analyzer 静态规则测试：全部注入输入，无 IO、无网络。"""

from datetime import datetime

from analyzer.deps_rule import check_deps
from analyzer.license_rule import check_license_signals
from analyzer.permissions_rule import check_permissions
from analyzer.pipeline import static_review
from analyzer.rules import RuleId, RuleOutcome
from analyzer.secrets_heuristic import check_secrets_heuristic
from analyzer.structure import check_structure
from core.enums import EntityType, LicenseClass, SourceKind
from core.schema.artifact import ArtifactRef
from core.schema.skill import Skill, SourceRecord
from core.state import SkillStatus


def _source(**overrides) -> SourceRecord:
    base = dict(
        source_kind=SourceKind.GITHUB,
        origin_url="https://github.com/owner/repo",
        source_object_id="owner/repo",
        author="owner",
        raw_name="skill",
        raw_description="desc",
        discovered_at=datetime(2026, 1, 1),
        last_synced_at=None,
        is_alive=True,
        allow_internal_test=None,
        allow_public_derived_result=None,
        allow_retain_test_copy=None,
    )
    base.update(overrides)
    return SourceRecord(**base)


def _skill(**overrides) -> Skill:
    base = dict(
        skill_id="s" * 64,
        canonical_name="skill",
        entity_type=EntityType.SKILL,
        status=SkillStatus.ACQUIRED,
        category_tags=("doc",),
        license_class=LicenseClass.UNKNOWN,
        license_spdx=None,
        declared_permissions=frozenset(),
        sources=(_source(),),
    )
    base.update(overrides)
    return Skill(**base)


_REF = ArtifactRef(
    bucket="external:github",
    key="https://api.github.com/repos/owner/repo/tarball/main",
    sha256="0" * 64,
    size_bytes=0,
    summary=None,
)


def _by_rule(findings, rule_id):
    return [f for f in findings if f.rule_id is rule_id]


class TestStructure:
    def test_skill_md_pass_and_fail(self):
        ok = check_structure({"name": "x", "description": "y"}, ["SKILL.md", "a.py"])
        assert _by_rule(ok, RuleId.STRUCT_SKILL_MD_PRESENT)[0].outcome is RuleOutcome.PASS

        bad = check_structure({"name": "x", "description": "y"}, ["readme.md"])
        assert _by_rule(bad, RuleId.STRUCT_SKILL_MD_PRESENT)[0].outcome is RuleOutcome.FAIL

    def test_missing_required_fields_fail(self):
        findings = check_structure({"name": "x"}, ["SKILL.md"])
        f = _by_rule(findings, RuleId.STRUCT_FRONTMATTER_FIELDS)[0]
        assert f.outcome is RuleOutcome.FAIL and "description" in f.message

    def test_none_inputs_need_info_not_crash(self):
        findings = check_structure(None, None)
        outcomes = {f.outcome for f in findings}
        assert RuleOutcome.NEED_INFO in outcomes
        assert RuleOutcome.FAIL not in outcomes  # 信息缺失≠失败

    def test_non_portable_paths_warn(self):
        findings = check_structure(
            {"name": "x", "description": "y", "triggers": "t"},
            ["SKILL.md", "C:\\Users\\author\\data.txt"],
        )
        assert _by_rule(findings, RuleId.STRUCT_PORTABLE_PATHS)[0].outcome is RuleOutcome.WARN


class TestLicense:
    def test_three_bits_mapping(self):
        record = _source(
            allow_internal_test=True,
            allow_public_derived_result=False,
            allow_retain_test_copy=None,
        )
        findings = check_license_signals(record, "MIT")
        assert _by_rule(findings, RuleId.LICENSE_PRESENT)[0].outcome is RuleOutcome.PASS
        assert _by_rule(findings, RuleId.LICENSE_TEST_RIGHTS)[0].outcome is RuleOutcome.PASS
        assert (
            _by_rule(findings, RuleId.LICENSE_PUBLIC_RESULT_RIGHTS)[0].outcome
            is RuleOutcome.WARN
        )
        assert (
            _by_rule(findings, RuleId.LICENSE_RETAIN_RIGHTS)[0].outcome
            is RuleOutcome.NEED_INFO
        )

    def test_no_license_need_info(self):
        findings = check_license_signals(_source(), None)
        assert _by_rule(findings, RuleId.LICENSE_PRESENT)[0].outcome is RuleOutcome.NEED_INFO


class TestPermissions:
    def test_unknown_scope_warn(self):
        findings = check_permissions(["file_read", "quantum_teleport"])
        f = _by_rule(findings, RuleId.PERM_UNKNOWN_SCOPE)[0]
        assert f.outcome is RuleOutcome.WARN and "quantum_teleport" in f.message

    def test_high_risk_warn(self):
        findings = check_permissions(["payment", "file_read"])
        f = _by_rule(findings, RuleId.PERM_HIGH_RISK)[0]
        assert f.outcome is RuleOutcome.WARN and "payment" in f.message

    def test_clean_scopes_pass(self):
        findings = check_permissions(["file_read", "network"])
        assert all(
            f.outcome is RuleOutcome.PASS
            for f in findings
            if f.rule_id in (RuleId.PERM_UNKNOWN_SCOPE, RuleId.PERM_HIGH_RISK)
        )

    def test_none_need_info(self):
        findings = check_permissions(None)
        assert findings[0].outcome is RuleOutcome.NEED_INFO


class TestSecretsHeuristic:
    def test_metadata_hit_fail(self):
        findings = check_secrets_heuristic(
            {"description": "api_key = 'abcdefgh12345678'"}, ["SKILL.md"]
        )
        assert findings[0].outcome is RuleOutcome.FAIL

    def test_suspicious_path_hit(self):
        findings = check_secrets_heuristic({"name": "x"}, ["scripts/id_rsa"])
        assert findings[0].outcome is RuleOutcome.FAIL

    def test_clean_pass_without_touching_content(self):
        # 未注入任何文本内容，仅元数据/路径 → 正常 PASS，证明不需要制品正文
        findings = check_secrets_heuristic({"name": "x"}, ["SKILL.md", "run.py"])
        assert findings[0].outcome is RuleOutcome.PASS

    def test_all_none_need_info(self):
        findings = check_secrets_heuristic(None, None, None)
        assert findings[0].outcome is RuleOutcome.NEED_INFO


class TestDeps:
    def test_wellformed_pass(self):
        findings = check_deps(["pandas", {"name": "ffmpeg", "source": "apt:ffmpeg"}])
        assert _by_rule(findings, RuleId.DEPS_MANIFEST_FORMAT)[0].outcome is RuleOutcome.PASS

    def test_malformed_fail(self):
        findings = check_deps([{"noname": True}, ""])
        assert _by_rule(findings, RuleId.DEPS_MANIFEST_FORMAT)[0].outcome is RuleOutcome.FAIL

    def test_untrusted_source_warn(self):
        findings = check_deps([{"name": "tool", "source": "http://evil.example/x"}])
        assert _by_rule(findings, RuleId.DEPS_UNTRUSTED_SOURCE)[0].outcome is RuleOutcome.WARN


class TestPipeline:
    def test_report_shape_and_summary_counts(self):
        report = static_review(
            _skill(),
            [_REF],
            manifest_fields={"name": "x", "description": "y", "triggers": "t"},
            file_paths=["SKILL.md"],
            declared_permissions=["file_read"],
            declared_deps=["pandas"],
        )
        assert report.skill_id == "s" * 64
        assert report.artifact_ref_keys == (_REF.key,)
        assert sum(report.summary.values()) == len(report.findings)
        assert report.summary[RuleOutcome.FAIL.value] == 0
        assert report.has_fail is False

    def test_fail_signal_propagates(self):
        report = static_review(
            _skill(),
            [_REF],
            manifest_fields={"name": "x", "description": "api_key = 'abcdefgh12345678'"},
            file_paths=["SKILL.md"],
        )
        assert report.has_fail is True

    def test_rule_crash_becomes_need_info(self):
        class Exploding:
            """Mapping 协议炸裂的对象：迫使结构规则抛异常。"""

            def get(self, *_):
                raise RuntimeError("boom")

            def items(self):
                raise RuntimeError("boom")

        report = static_review(_skill(), [_REF], manifest_fields=Exploding())
        crashes = [
            f for f in report.findings if f.rule_id is RuleId.PIPELINE_RULE_CRASH
        ]
        assert crashes and all(f.outcome is RuleOutcome.NEED_INFO for f in crashes)
        # 其他规则仍然产出
        assert any(f.rule_id is RuleId.LICENSE_PRESENT for f in report.findings)
