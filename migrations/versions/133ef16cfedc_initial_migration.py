"""initial migration

Revision ID: 133ef16cfedc
Revises: 
Create Date: 2026-11-22 10:27:50.505756

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '133ef16cfedc'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'event_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_code', sa.String(length=100), nullable=False),
        sa.Column('event_description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'uq_event_rules_event_code_active',
        'event_rules',
        ['event_code'],
        unique=True,
        postgresql_where=sa.text('is_deleted = false'),
        sqlite_where=sa.text('is_deleted = 0'),
    )

    op.create_table(
        'monitoring_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('machine_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('stop_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('interval_seconds', sa.Integer(), nullable=False),
        sa.Column('last_processed_cursor', sa.Integer(), nullable=False),
        sa.Column('last_attempt', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_attempt', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_monitoring_tasks_machine_id'), 'monitoring_tasks', ['machine_id'], unique=False)

    op.create_table(
        'monitored_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('machine_id', sa.String(length=100), nullable=False),
        sa.Column('cursor', sa.Integer(), nullable=False),
        sa.Column('event_code', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['monitoring_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('machine_id', 'cursor', name='uq_machine_cursor'),
    )
    op.create_index(op.f('ix_monitored_events_event_code'), 'monitored_events', ['event_code'], unique=False)
    op.create_index(op.f('ix_monitored_events_machine_id'), 'monitored_events', ['machine_id'], unique=False)

    op.create_table(
        'task_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('start_cursor', sa.Integer(), nullable=True),
        sa.Column('end_cursor', sa.Integer(), nullable=True),
        sa.Column('records_downloaded', sa.Integer(), nullable=False),
        sa.Column('matched_events', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['monitoring_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('task_executions')
    op.drop_index(op.f('ix_monitored_events_machine_id'), table_name='monitored_events')
    op.drop_index(op.f('ix_monitored_events_event_code'), table_name='monitored_events')
    op.drop_table('monitored_events')
    op.drop_index(op.f('ix_monitoring_tasks_machine_id'), table_name='monitoring_tasks')
    op.drop_table('monitoring_tasks')
    op.drop_index('uq_event_rules_event_code_active', table_name='event_rules')
    op.drop_table('event_rules')
