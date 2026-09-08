"""Initial demo profile, schedule, search, and saved itinerary tables."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('profiles', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('preferences', postgresql.JSONB(), nullable=False))
    for table in ('classes', 'schedule_exceptions'):
        cols = [sa.Column('id', sa.Integer(), primary_key=True), sa.Column('profile_id', sa.Integer(), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False), sa.Column('data', postgresql.JSONB(), nullable=False)]
        if table == 'schedule_exceptions':
            cols.append(sa.Column('class_id', sa.Integer(), sa.ForeignKey('classes.id', ondelete='CASCADE')))
        op.create_table(table, *cols)
        op.create_index(f'ix_{table}_profile_id', table, ['profile_id'])
    op.create_index('ix_schedule_exceptions_class_id', 'schedule_exceptions', ['class_id'])
    op.create_table('searches', sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('profile_id', sa.Integer(), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('request', postgresql.JSONB(), nullable=False), sa.Column('context', postgresql.JSONB(), nullable=False), sa.Column('response', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_searches_profile_id', 'searches', ['profile_id'])
    op.create_index('ix_search_profile_created', 'searches', ['profile_id', 'created_at'])
    op.create_table('saved_itineraries', sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('profile_id', sa.Integer(), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('search_id', sa.Integer(), sa.ForeignKey('searches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('itinerary_id', sa.String(128), nullable=False), sa.Column('evaluation', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('profile_id', 'search_id', 'itinerary_id', name='uq_saved_option'))
    for column in ('profile_id', 'search_id'):
        op.create_index(f'ix_saved_itineraries_{column}', 'saved_itineraries', [column])


def downgrade():
    for table in ('saved_itineraries', 'searches', 'schedule_exceptions', 'classes', 'profiles'):
        op.drop_table(table)
