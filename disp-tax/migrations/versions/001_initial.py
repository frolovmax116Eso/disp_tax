"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create dispatchers table
    op.create_table(
        'dispatchers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('session_file', sa.String(), nullable=False),
        sa.Column('session_active', sa.Boolean(), nullable=True),
        sa.Column('session_expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index(op.f('ix_dispatchers_telegram_id'), 'dispatchers', ['telegram_id'], unique=True)
    op.create_index(op.f('ix_dispatchers_session_active'), 'dispatchers', ['session_active'], unique=False)
    
    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dispatcher_id', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('normalized_content', sa.Text(), nullable=False),
        sa.Column('is_vip', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dispatcher_id'], ['dispatchers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_dispatcher_id'), 'orders', ['dispatcher_id'], unique=False)
    op.create_index(op.f('ix_orders_state'), 'orders', ['state'], unique=False)
    op.create_index(op.f('ix_orders_created_at'), 'orders', ['created_at'], unique=False)
    
    # Create groups table
    op.create_table(
        'regions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dispatcher_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dispatcher_id'], ['dispatchers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_regions_dispatcher_id'), 'regions', ['dispatcher_id'], unique=False)
    
    op.create_table(
        'groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dispatcher_id', sa.Integer(), nullable=False),
        sa.Column('telegram_group_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('region_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dispatcher_id'], ['dispatchers.id'], ),
        sa.ForeignKeyConstraint(['region_id'], ['regions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_groups_dispatcher_id'), 'groups', ['dispatcher_id'], unique=False)
    op.create_index(op.f('ix_groups_is_active'), 'groups', ['is_active'], unique=False)
    
    # Create scenarios table
    op.create_table(
        'scenarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dispatcher_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('group_ids', sa.JSON(), nullable=False),
        sa.Column('delay_min', sa.Integer(), nullable=False),
        sa.Column('delay_max', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dispatcher_id'], ['dispatchers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scenarios_dispatcher_id'), 'scenarios', ['dispatcher_id'], unique=False)
    
    # Create driver_responses table
    op.create_table(
        'driver_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('driver_telegram_id', sa.Integer(), nullable=False),
        sa.Column('driver_username', sa.String(), nullable=True),
        sa.Column('driver_name', sa.String(), nullable=False),
        sa.Column('driver_phone', sa.String(), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('response_type', sa.String(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('replied_to_message_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_driver_responses_order_id'), 'driver_responses', ['order_id'], unique=False)
    op.create_index(op.f('ix_driver_responses_driver_telegram_id'), 'driver_responses', ['driver_telegram_id'], unique=False)
    op.create_index(op.f('ix_driver_responses_created_at'), 'driver_responses', ['created_at'], unique=False)
    
    # Create assignments table
    op.create_table(
        'assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('driver_telegram_id', sa.Integer(), nullable=False),
        sa.Column('driver_username', sa.String(), nullable=True),
        sa.Column('driver_name', sa.String(), nullable=False),
        sa.Column('assigned_by', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('unassigned_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assignments_order_id'), 'assignments', ['order_id'], unique=False)
    op.create_index(op.f('ix_assignments_driver_telegram_id'), 'assignments', ['driver_telegram_id'], unique=False)
    op.create_index(op.f('ix_assignments_is_active'), 'assignments', ['is_active'], unique=False)
    
    # Create admins table
    op.create_table(
        'admins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_access_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index(op.f('ix_admins_telegram_id'), 'admins', ['telegram_id'], unique=True)
    
    # Create admin_access_logs table
    op.create_table(
        'admin_access_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_access_logs_admin_id'), 'admin_access_logs', ['admin_id'], unique=False)
    op.create_index(op.f('ix_admin_access_logs_created_at'), 'admin_access_logs', ['created_at'], unique=False)
    
    # Create order_history table
    op.create_table(
        'order_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('old_state', sa.String(), nullable=True),
        sa.Column('new_state', sa.String(), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=False),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('changes', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_history_order_id'), 'order_history', ['order_id'], unique=False)
    
    # Create group_messages table
    op.create_table(
        'group_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('telegram_message_id', sa.Integer(), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_group_messages_order_id'), 'group_messages', ['order_id'], unique=False)
    op.create_index(op.f('ix_group_messages_telegram_message_id'), 'group_messages', ['telegram_message_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_group_messages_telegram_message_id'), table_name='group_messages')
    op.drop_index(op.f('ix_group_messages_order_id'), table_name='group_messages')
    op.drop_table('group_messages')
    op.drop_index(op.f('ix_order_history_order_id'), table_name='order_history')
    op.drop_table('order_history')
    op.drop_index(op.f('ix_admin_access_logs_created_at'), table_name='admin_access_logs')
    op.drop_index(op.f('ix_admin_access_logs_admin_id'), table_name='admin_access_logs')
    op.drop_table('admin_access_logs')
    op.drop_index(op.f('ix_admins_telegram_id'), table_name='admins')
    op.drop_table('admins')
    op.drop_index(op.f('ix_assignments_is_active'), table_name='assignments')
    op.drop_index(op.f('ix_assignments_driver_telegram_id'), table_name='assignments')
    op.drop_index(op.f('ix_assignments_order_id'), table_name='assignments')
    op.drop_table('assignments')
    op.drop_index(op.f('ix_driver_responses_created_at'), table_name='driver_responses')
    op.drop_index(op.f('ix_driver_responses_driver_telegram_id'), table_name='driver_responses')
    op.drop_index(op.f('ix_driver_responses_order_id'), table_name='driver_responses')
    op.drop_table('driver_responses')
    op.drop_index(op.f('ix_scenarios_dispatcher_id'), table_name='scenarios')
    op.drop_table('scenarios')
    op.drop_index(op.f('ix_groups_is_active'), table_name='groups')
    op.drop_index(op.f('ix_groups_dispatcher_id'), table_name='groups')
    op.drop_table('groups')
    op.drop_index(op.f('ix_regions_dispatcher_id'), table_name='regions')
    op.drop_table('regions')
    op.drop_index(op.f('ix_orders_created_at'), table_name='orders')
    op.drop_index(op.f('ix_orders_state'), table_name='orders')
    op.drop_index(op.f('ix_orders_dispatcher_id'), table_name='orders')
    op.drop_table('orders')
    op.drop_index(op.f('ix_dispatchers_session_active'), table_name='dispatchers')
    op.drop_index(op.f('ix_dispatchers_telegram_id'), table_name='dispatchers')
    op.drop_table('dispatchers')

