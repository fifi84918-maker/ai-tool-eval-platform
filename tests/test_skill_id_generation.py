"""Test skill_id generation from repository URLs."""

from api.routers.eval import _skill_id_from_url


def test_skill_id_from_github_url():
    """Test skill_id generation from GitHub URLs."""
    assert _skill_id_from_url("https://github.com/acme/doc-skill") == "github-acme-doc-skill"
    assert _skill_id_from_url("https://github.com/owner/repo") == "github-owner-repo"
    assert _skill_id_from_url("https://github.com/test/my-project") == "github-test-my-project"


def test_skill_id_from_gitlab_url():
    """Test skill_id generation from GitLab URLs."""
    assert _skill_id_from_url("https://gitlab.com/acme/project") == "gitlab-acme-project"


def test_skill_id_from_url_variations():
    """Test skill_id generation handles URL variations."""
    # Trailing slash
    assert _skill_id_from_url("https://github.com/owner/repo/") == "github-owner-repo"
    
    # HTTP instead of HTTPS
    assert _skill_id_from_url("http://github.com/owner/repo") == "github-owner-repo"
    
    # Mixed case (should be lowercased)
    assert _skill_id_from_url("https://GitHub.com/Owner/Repo") == "github-owner-repo"


def test_skill_id_from_url_with_subpaths():
    """Test skill_id generation with deep paths."""
    # GitLab group/subgroup/project
    assert _skill_id_from_url("https://gitlab.com/group/subgroup/project") == "gitlab-group-subgroup-project"
