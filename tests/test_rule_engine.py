"""Tests for Rule Engine (V1A 29.2.2)."""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.rules import RuleEngine, BUILTIN_RULES
from api.rules.builtin import (
    SecurityTierMismatchRule,
    HighRiskSkillInStrictRule,
    DomainOverlapRule,
    LanguageOverlapRule,
)
from api.schemas import ProjectProfileBase, BundleOut

client = TestClient(app)


def test_engine_loads_6_rules():
    """Test that engine loads all 6 built-in rules."""
    engine = RuleEngine(BUILTIN_RULES)
    assert len(engine.rules) == 6


def test_r001_blocks_when_security_mismatch():
    """Test R001: security_tier_mismatch blocks when mismatch."""
    rule = SecurityTierMismatchRule()
    
    profile = ProjectProfileBase(
        name="test",
        security_requirement="strict",
        domains=[],
        languages=[]
    )
    
    bundle = BundleOut(
        bundle_id="test-bundle",
        name="Test Bundle",
        tier="starter",  # lax level
        description="",
        category="test",
        skill_ids=[],
        tags=[],
        security_level="lax"
    )
    
    result = rule.check(profile, bundle)
    
    assert result.filtered is True
    assert len(result.violations) == 1
    assert result.violations[0].severity == "block"


def test_r002_blocks_high_risk_in_strict():
    """Test R002: high_risk_skill_in_strict blocks leaky-skill in strict mode (non-enterprise)."""
    rule = HighRiskSkillInStrictRule()
    
    profile = ProjectProfileBase(
        name="test",
        security_requirement="strict",
        domains=[],
        languages=[]
    )
    
    # Standard bundle (not enterprise) with leaky-skill
    bundle = BundleOut(
        bundle_id="test-bundle",
        name="Test Bundle",
        tier="standard",  # Not enterprise, so rule should block
        description="",
        category="test",
        skill_ids=["c2025e6a6d0d23aa57da5beb1fd95ceb65cc6c52e4caaca6ed0a213508ea7dd7"],  # leaky-skill
        tags=[],
        security_level="standard"
    )
    
    result = rule.check(profile, bundle)
    
    assert result.filtered is True
    assert len(result.violations) == 1
    assert result.violations[0].severity == "block"


def test_r003_r004_score_contribution():
    """Test R003/R004: domain and language overlap contribute to score."""
    domain_rule = DomainOverlapRule()
    language_rule = LanguageOverlapRule()
    
    profile = ProjectProfileBase(
        name="test",
        security_requirement="lax",
        domains=["documentation", "development"],
        languages=["python", "typescript"]
    )
    
    bundle = BundleOut(
        bundle_id="test-bundle",
        name="Test Bundle",
        tier="standard",
        description="",
        category="test",
        skill_ids=[],
        tags=[],
        target_domains=["documentation", "development"],
        required_languages=["python"],
        security_level="standard"
    )
    
    domain_result = domain_rule.check(profile, bundle)
    language_result = language_rule.check(profile, bundle)
    
    # 2 domains * 10 = 20
    assert domain_result.score_adjustment == 20.0
    assert len(domain_result.violations) == 2  # info violations
    
    # 1 language * 5 = 5
    assert language_result.score_adjustment == 5.0
    assert len(language_result.violations) == 1


def test_r005_detects_duplicate_capability():
    """Test R005: duplicate_capability detects duplicate domains."""
    from api.rules.builtin import DuplicateCapabilityRule
    
    rule = DuplicateCapabilityRule()
    
    profile = ProjectProfileBase(
        name="test",
        security_requirement="lax",
        domains=[],
        languages=[]
    )
    
    # Bundle with duplicate domain
    bundle = BundleOut(
        bundle_id="test-bundle",
        name="Test Bundle",
        tier="standard",
        description="",
        category="test",
        skill_ids=[],
        tags=[],
        target_domains=["documentation", "documentation"],  # duplicate
        required_languages=[],
        security_level="standard"
    )
    
    result = rule.check(profile, bundle)
    
    assert len(result.violations) == 1
    assert result.violations[0].severity == "warning"


def test_r006_permission_warning():
    """Test R006: permission_aggregation warns for enterprise in lax mode."""
    from api.rules.builtin import PermissionAggregationRule
    
    rule = PermissionAggregationRule()
    
    profile = ProjectProfileBase(
        name="test",
        security_requirement="lax",
        domains=[],
        languages=[]
    )
    
    bundle = BundleOut(
        bundle_id="test-bundle",
        name="Test Bundle",
        tier="enterprise",  # Enterprise in lax mode
        description="",
        category="test",
        skill_ids=["skill1", "skill2", "skill3", "skill4", "skill5"],
        tags=[],
        security_level="strict"
    )
    
    result = rule.check(profile, bundle)
    
    assert len(result.violations) == 1
    assert result.violations[0].severity == "warning"


def test_recommend_uses_engine():
    """Test that recommendation endpoint uses rule engine and returns rule_findings."""
    payload = {
        "name": "engine-test",
        "domains": ["documentation"],
        "languages": ["python"],
        "security_requirement": "lax"
    }
    
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] > 0
    
    # Check first bundle has rule_findings
    first_bundle = data["items"][0]
    assert "rule_findings" in first_bundle
    assert isinstance(first_bundle["rule_findings"], list)
    
    # Should have at least info-level findings (domain/language overlaps)
    if len(first_bundle["rule_findings"]) > 0:
        first_finding = first_bundle["rule_findings"][0]
        assert "rule_id" in first_finding
        assert "severity" in first_finding
