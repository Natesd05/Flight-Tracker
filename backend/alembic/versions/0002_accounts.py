"""Personal accounts and expiring sessions."""
from alembic import op
import sqlalchemy as sa
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('accounts', sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(254), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('profile_id', sa.Integer(), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, unique=True))
    op.create_table('login_sessions', sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_login_sessions_account_id', 'login_sessions', ['account_id'])
    op.execute("SELECT setval(pg_get_serial_sequence('profiles', 'id'), GREATEST(COALESCE((SELECT MAX(id) FROM profiles), 1), 1))")


def downgrade():
    op.drop_table('login_sessions')
    op.drop_table('accounts')
