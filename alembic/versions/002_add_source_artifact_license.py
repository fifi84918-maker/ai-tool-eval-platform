"""add source_records, artifact_versions and license_assessments

Revision ID: 002_v1a_source
Revises: 001_initial
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_v1a_source'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create source_records table
    op.create_table('source_records',
    sa.Column('id', sa.String(length=256), nullable=False),
    sa.Column('platform', sa.String(length=32), nullable=False),
    sa.Column('platform_object_id', sa.String(length=256), nullable=True),
    sa.Column('skill_name', sa.String(length=256), nullable=True),
    sa.Column('raw_description', sa.Text(), nullable=False),
    sa.Column('author', sa.String(length=256), nullable=False),
    sa.Column('origin_url', sa.Text(), nullable=False),
    sa.Column('discovered_at', sa.DateTime(), nullable=False),
    sa.Column('last_synced_at', sa.DateTime(), nullable=True),
    sa.Column('visibility', sa.String(length=16), nullable=False),
    sa.Column('license', sa.String(length=64), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=True),
    sa.Column('acquired', sa.Boolean(), nullable=False),
    sa.Column('allow_internal_test', sa.Boolean(), nullable=False),
    sa.Column('allow_public_display', sa.Boolean(), nullable=False),
    sa.Column('allow_retain_copy', sa.Boolean(), nullable=False),
    sa.Column('withdrawn', sa.Boolean(), nullable=False),
    sa.Column('raw_payload', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_source_records_content_hash'), 'source_records', ['content_hash'], unique=False)
    op.create_index(op.f('ix_source_records_origin_url'), 'source_records', ['origin_url'], unique=False)
    op.create_index('ix_source_records_platform_object', 'source_records', ['platform', 'platform_object_id'], unique=True)

    # Create artifact_versions table
    op.create_table('artifact_versions',
    sa.Column('id', sa.String(length=256), nullable=False),
    sa.Column('skill_id', sa.String(length=128), nullable=True),
    sa.Column('source_id', sa.String(length=256), nullable=True),
    sa.Column('version', sa.String(length=128), nullable=False),
    sa.Column('fetched_at', sa.DateTime(), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('archive_path', sa.String(length=512), nullable=True),
    sa.Column('normalized', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.ForeignKeyConstraint(['source_id'], ['source_records.id'], ondelete='SET NULL')
    )
    op.create_index(op.f('ix_artifact_versions_content_hash'), 'artifact_versions', ['content_hash'], unique=False)
    op.create_index(op.f('ix_artifact_versions_skill_id'), 'artifact_versions', ['skill_id'], unique=False)
    op.create_index(op.f('ix_artifact_versions_source_id'), 'artifact_versions', ['source_id'], unique=False)

    # Create license_assessments table
    op.create_table('license_assessments',
    sa.Column('id', sa.String(length=256), nullable=False),
    sa.Column('artifact_version_id', sa.String(length=256), nullable=True),
    sa.Column('license', sa.String(length=64), nullable=False),
    sa.Column('allows_archival', sa.Boolean(), nullable=False),
    sa.Column('allows_public_display', sa.Boolean(), nullable=False),
    sa.Column('allows_internal_test', sa.Boolean(), nullable=False),
    sa.Column('allows_modification', sa.Boolean(), nullable=False),
    sa.Column('confidence', sa.String(length=16), nullable=False),
    sa.Column('needs_human_review', sa.Boolean(), nullable=False),
    sa.Column('detected_files', sa.JSON(), nullable=True),
    sa.Column('assessed_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.ForeignKeyConstraint(['artifact_version_id'], ['artifact_versions.id'], ondelete='CASCADE'),
    sa.UniqueConstraint('artifact_version_id')
    )
    op.create_index(op.f('ix_license_assessments_artifact_version_id'), 'license_assessments', ['artifact_version_id'], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order (child tables first)
    op.drop_index(op.f('ix_license_assessments_artifact_version_id'), table_name='license_assessments')
    op.drop_table('license_assessments')
    
    op.drop_index(op.f('ix_artifact_versions_source_id'), table_name='artifact_versions')
    op.drop_index(op.f('ix_artifact_versions_skill_id'), table_name='artifact_versions')
    op.drop_index(op.f('ix_artifact_versions_content_hash'), table_name='artifact_versions')
    op.drop_table('artifact_versions')
    
    op.drop_index('ix_source_records_platform_object', table_name='source_records')
    op.drop_index(op.f('ix_source_records_origin_url'), table_name='source_records')
    op.drop_index(op.f('ix_source_records_content_hash'), table_name='source_records')
    op.drop_table('source_records')
