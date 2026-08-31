"""In-Memory Skill Store for L2 Data Layer (V1A L2)."""

from datetime import datetime, timezone
from api.models import (
    CanonicalSkill,
    SourceRecord,
    ArtifactRecord,
    create_transition,
)


# In-memory storage
_skills: dict[str, CanonicalSkill] = {}
_sources: dict[str, SourceRecord] = {}
_artifacts: dict[str, ArtifactRecord] = {}


def put_skill(skill: CanonicalSkill) -> None:
    """存储或更新技能。
    
    Args:
        skill: CanonicalSkill 实例
    """
    skill.updated_at = datetime.now(timezone.utc)
    _skills[skill.skill_id] = skill


def get_skill(skill_id: str) -> CanonicalSkill | None:
    """获取技能。
    
    Args:
        skill_id: 技能 ID
        
    Returns:
        CanonicalSkill 或 None
    """
    return _skills.get(skill_id)


def list_skills(filter_by_state: str | None = None) -> list[CanonicalSkill]:
    """列出技能，可按状态过滤。
    
    Args:
        filter_by_state: 可选状态过滤
        
    Returns:
        CanonicalSkill 列表
    """
    if filter_by_state is None:
        return list(_skills.values())
    
    return [s for s in _skills.values() if s.state == filter_by_state]


def put_source(source: SourceRecord) -> None:
    """存储源记录。
    
    Args:
        source: SourceRecord 实例
    """
    _sources[source.source_id] = source


def get_source(source_id: str) -> SourceRecord | None:
    """获取源记录。
    
    Args:
        source_id: 源 ID
        
    Returns:
        SourceRecord 或 None
    """
    return _sources.get(source_id)


def list_sources() -> list[SourceRecord]:
    """列出所有源记录。
    
    Returns:
        SourceRecord 列表
    """
    return list(_sources.values())


def put_artifact(artifact: ArtifactRecord) -> None:
    """存储制品记录。
    
    Args:
        artifact: ArtifactRecord 实例
    """
    _artifacts[artifact.artifact_id] = artifact


def get_artifact(artifact_id: str) -> ArtifactRecord | None:
    """获取制品记录。
    
    Args:
        artifact_id: 制品 ID
        
    Returns:
        ArtifactRecord 或 None
    """
    return _artifacts.get(artifact_id)


def list_artifacts(skill_id: str | None = None) -> list[ArtifactRecord]:
    """列出制品记录，可按技能过滤。
    
    Args:
        skill_id: 可选技能 ID
        
    Returns:
        ArtifactRecord 列表
    """
    if skill_id is None:
        return list(_artifacts.values())
    
    return [a for a in _artifacts.values() if a.skill_id == skill_id]


def transition_state(skill_id: str, to_state: str, reason: str) -> None:
    """执行状态转换（含校验）。
    
    Args:
        skill_id: 技能 ID
        to_state: 目标状态
        reason: 转换原因
        
    Raises:
        ValueError: 技能不存在或不允许的转换
    """
    skill = get_skill(skill_id)
    if skill is None:
        raise ValueError(f"Skill not found: {skill_id}")
    
    # Create transition (this validates it)
    transition = create_transition(skill.state, to_state, reason)
    
    # Update skill
    skill.state = to_state
    skill.state_history.append(transition.model_dump())
    skill.updated_at = datetime.now(timezone.utc)
    
    # Save back
    put_skill(skill)


def clear_all() -> None:
    """清空所有存储（测试用）。"""
    global _skills, _sources, _artifacts
    _skills.clear()
    _sources.clear()
    _artifacts.clear()
