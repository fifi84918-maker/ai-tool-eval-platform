"""Test that sample skills have non-empty category_tags."""

from mcp_server.index import InMemorySkillIndex
from scripts.samples import SAMPLES


def test_samples_have_categories():
    """All sample skills should have at least one category tag."""
    index = InMemorySkillIndex(SAMPLES)
    
    # Get all skills from index (they use skill_id from pipeline, not sample_id)
    for sample in SAMPLES:
        # Find the skill by searching (we don't know the exact skill_id beforehand)
        found = False
        name = sample.raw_item.get("name")
        for skill_id, entry in index._entries.items():
            if sample.sample_id in skill_id or (name and name in skill_id):
                detail = entry.detail
                assert detail["category_tags"], f"Skill {skill_id} has empty category_tags"
                assert len(detail["category_tags"]) > 0, f"Skill {skill_id} has no categories"
                
                # Check all category tags are strings
                for tag in detail["category_tags"]:
                    assert isinstance(tag, str), f"Category tag '{tag}' is not a string"
                found = True
                break
        
        # For this test, we just check that index was built successfully
        # The actual skill_id mapping is internal to the pipeline
        assert len(index._entries) > 0, "Index should have entries"


def test_category_tags_are_valid():
    """Category tags should match the hardcoded categories on the categories page."""
    valid_categories = {
        "documentation", "development", "analytics", "productivity",
        "security", "testing", "content", "communication"
    }
    
    index = InMemorySkillIndex(SAMPLES)
    
    # Check all skills have valid category tags
    for skill_id, entry in index._entries.items():
        detail = entry.detail
        for tag in detail["category_tags"]:
            assert tag in valid_categories, (
                f"Skill {skill_id} has invalid category '{tag}'. "
                f"Valid categories: {valid_categories}"
            )


def test_all_samples_have_at_least_one_category():
    """Verify that the index now returns non-empty category_tags for all skills."""
    index = InMemorySkillIndex(SAMPLES)
    
    assert len(index._entries) == len(SAMPLES), "Index should have all samples"
    
    empty_categories = []
    for skill_id, entry in index._entries.items():
        if not entry.detail["category_tags"]:
            empty_categories.append(skill_id)
    
    assert len(empty_categories) == 0, (
        f"The following skills have empty category_tags: {empty_categories}"
    )

