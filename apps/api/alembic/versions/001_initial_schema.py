"""Initial schema with all tables (non-PostGIS version)

Revision ID: 001
Revises:
Create Date: 2026-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # sources table
    op.create_table(
        'sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('category', sa.Text()),
        sa.Column('url', sa.Text()),
        sa.Column('api_type', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # raw_documents table
    op.create_table(
        'raw_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sources.id'), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('content_type', sa.Text()),
        sa.Column('content', sa.Text()),
        sa.Column('hash', sa.Text()),
    )

    # nrhp_points table (using lat/lon instead of geometry)
    op.create_table(
        'nrhp_points',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nris_refnum', sa.Text(), unique=True, nullable=True),
        sa.Column('resname', sa.Text()),
        sa.Column('state', sa.Text()),
        sa.Column('county', sa.Text()),
        sa.Column('status', sa.Text()),
        sa.Column('is_nhl', sa.Text()),
        sa.Column('nara_url', sa.Text()),
        sa.Column('edit_date', sa.Text()),
        sa.Column('source', sa.Text()),
        sa.Column('lon', sa.Float()),
        sa.Column('lat', sa.Float()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_nrhp_points_lat', 'nrhp_points', ['lat'])
    op.create_index('idx_nrhp_points_lon', 'nrhp_points', ['lon'])
    op.create_index('idx_nrhp_points_state', 'nrhp_points', ['state'])

    # targets table (using lat/lon instead of geometry)
    op.create_table(
        'targets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.Text()),
        sa.Column('target_type', sa.Text()),
        sa.Column('lon', sa.Float()),
        sa.Column('lat', sa.Float()),
        sa.Column('black_sky_score', sa.Integer(), server_default='0'),
        sa.Column('confidence', sa.Float(), server_default='0.5'),
        sa.Column('review_status', sa.Text(), server_default="'unreviewed'"),
        sa.Column('review_notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_targets_lat', 'targets', ['lat'])
    op.create_index('idx_targets_lon', 'targets', ['lon'])
    op.create_index('idx_targets_review_status', 'targets', ['review_status'])
    op.create_index('idx_targets_black_sky_score', 'targets', ['black_sky_score'])

    # target_flags table
    op.create_table(
        'target_flags',
        sa.Column('target_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('targets.id'), primary_key=True),
        sa.Column('nrhp_near_count_1km', sa.Integer()),
        sa.Column('nrhp_min_distance_m', sa.Float()),
        sa.Column('nrhp_has_nhl_nearby_1km', sa.Boolean()),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('target_flags')
    op.drop_table('targets')
    op.drop_table('nrhp_points')
    op.drop_table('raw_documents')
    op.drop_table('sources')
