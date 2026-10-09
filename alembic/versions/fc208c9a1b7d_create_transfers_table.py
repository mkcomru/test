"""create transfers table

Revision ID: fc208c9a1b7d
Revises:
Create Date: 2026-10-09 18:26:23.513855

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fc208c9a1b7d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

transfer_status = postgresql.ENUM(
    'pending', 'completed', 'failed', name='transfer_status', create_type=False
)


def upgrade() -> None:
    """Upgrade schema."""
    transfer_status.create(op.get_bind(), checkfirst=True)
    op.create_table('transfers',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('external_id', sa.String(length=128), nullable=False),
    sa.Column('currency', sa.String(length=16), nullable=False),
    sa.Column('amount', sa.Numeric(precision=36, scale=18), nullable=False),
    sa.Column('destination', sa.Text(), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('status', transfer_status, server_default='pending', nullable=False),
    sa.Column('tx_hash', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transfers_external_id'), 'transfers', ['external_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_transfers_external_id'), table_name='transfers')
    op.drop_table('transfers')
    transfer_status.drop(op.get_bind(), checkfirst=True)
