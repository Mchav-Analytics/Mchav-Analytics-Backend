"""create initial application tables

Revision ID: eb42e7a9a3e2
Revises: 
Create Date: 2026-07-06 15:49:11.931650

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb42e7a9a3e2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('roles',
    sa.Column('id_role', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id_role'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_roles_id_role'), 'roles', ['id_role'], unique=False)

    op.create_table('users',
    sa.Column('id_user', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('full_name', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('id_role', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_role'], ['roles.id_role'], ),
    sa.PrimaryKeyConstraint('id_user'),
    sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_id_user'), 'users', ['id_user'], unique=False)

    op.create_table('oauth_tokens',
    sa.Column('id_token', sa.Integer(), nullable=False),
    sa.Column('access_token', sa.String(), nullable=False),
    sa.Column('refresh_token', sa.String(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id_user', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_user'], ['users.id_user'], ),
    sa.PrimaryKeyConstraint('id_token'),
    sa.UniqueConstraint('id_user')
    )
    op.create_index(op.f('ix_oauth_tokens_id_token'), 'oauth_tokens', ['id_token'], unique=False)

    op.create_table('projects',
    sa.Column('id_project', sa.Integer(), nullable=False),
    sa.Column('jira_project_id', sa.String(), nullable=False),
    sa.Column('project_key', sa.String(), nullable=False),
    sa.Column('project_name', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id_project'),
    sa.UniqueConstraint('jira_project_id'),
    sa.UniqueConstraint('project_key')
    )
    op.create_index(op.f('ix_projects_id_project'), 'projects', ['id_project'], unique=False)
    op.create_index(op.f('ix_projects_jira_project_id'), 'projects', ['jira_project_id'], unique=False)

    op.create_table('boards',
    sa.Column('id_board', sa.Integer(), nullable=False),
    sa.Column('jira_board_id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('type', sa.String(), nullable=True),
    sa.Column('id_project', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_project'], ['projects.id_project'], ),
    sa.PrimaryKeyConstraint('id_board'),
    sa.UniqueConstraint('jira_board_id')
    )
    op.create_index(op.f('ix_boards_id_board'), 'boards', ['id_board'], unique=False)
    op.create_index(op.f('ix_boards_jira_board_id'), 'boards', ['jira_board_id'], unique=False)

    op.create_table('project_members',
    sa.Column('id_project_member', sa.Integer(), nullable=False),
    sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('id_user', sa.Integer(), nullable=False),
    sa.Column('id_project', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_project'], ['projects.id_project'], ),
    sa.ForeignKeyConstraint(['id_user'], ['users.id_user'], ),
    sa.PrimaryKeyConstraint('id_project_member')
    )
    op.create_index(op.f('ix_project_members_id_project_member'), 'project_members', ['id_project_member'], unique=False)

    op.create_table('issue_types',
    sa.Column('id_type', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id_type'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_issue_types_id_type'), 'issue_types', ['id_type'], unique=False)

    op.create_table('sprints',
    sa.Column('id_sprint', sa.Integer(), nullable=False),
    sa.Column('jira_sprint_id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('state', sa.String(), nullable=False),
    sa.Column('id_board', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_board'], ['boards.id_board'], ),
    sa.PrimaryKeyConstraint('id_sprint'),
    sa.UniqueConstraint('jira_sprint_id')
    )
    op.create_index(op.f('ix_sprints_id_sprint'), 'sprints', ['id_sprint'], unique=False)
    op.create_index(op.f('ix_sprints_jira_sprint_id'), 'sprints', ['jira_sprint_id'], unique=False)

    op.create_table('issues',
    sa.Column('id_issue', sa.Integer(), nullable=False),
    sa.Column('jira_issue_id', sa.String(), nullable=False),
    sa.Column('issue_key', sa.String(), nullable=False),
    sa.Column('summary', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('assignee', sa.String(), nullable=True),
    sa.Column('story_points', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id_type', sa.Integer(), nullable=False),
    sa.Column('id_sprint', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id_sprint'], ['sprints.id_sprint'], ),
    sa.ForeignKeyConstraint(['id_type'], ['issue_types.id_type'], ),
    sa.PrimaryKeyConstraint('id_issue'),
    sa.UniqueConstraint('jira_issue_id')
    )
    op.create_index(op.f('ix_issues_id_issue'), 'issues', ['id_issue'], unique=False)
    op.create_index(op.f('ix_issues_jira_issue_id'), 'issues', ['jira_issue_id'], unique=False)

    op.create_table('state_changelogs',
    sa.Column('id_changelog', sa.Integer(), nullable=False),
    sa.Column('status_from', sa.String(), nullable=False),
    sa.Column('status_to', sa.String(), nullable=False),
    sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id_issue', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_issue'], ['issues.id_issue'], ),
    sa.PrimaryKeyConstraint('id_changelog')
    )
    op.create_index(op.f('ix_state_changelogs_id_changelog'), 'state_changelogs', ['id_changelog'], unique=False)

    op.create_table('kpi_types',
    sa.Column('id_kpi_type', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('unit', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id_kpi_type'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_kpi_types_id_kpi_type'), 'kpi_types', ['id_kpi_type'], unique=False)

    op.create_table('kpi_history',
    sa.Column('id_kpi', sa.Integer(), nullable=False),
    sa.Column('metric_value', sa.Float(), nullable=False),
    sa.Column('calc_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('id_sprint', sa.Integer(), nullable=False),
    sa.Column('id_kpi_type', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_kpi_type'], ['kpi_types.id_kpi_type'], ),
    sa.ForeignKeyConstraint(['id_sprint'], ['sprints.id_sprint'], ),
    sa.PrimaryKeyConstraint('id_kpi')
    )
    op.create_index(op.f('ix_kpi_history_id_kpi'), 'kpi_history', ['id_kpi'], unique=False)

    op.create_table('sync_jobs',
    sa.Column('id_job', sa.Integer(), nullable=False),
    sa.Column('job_name', sa.String(), nullable=False),
    sa.Column('job_type', sa.String(), nullable=False),
    sa.Column('frequency', sa.String(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id_job')
    )
    op.create_index(op.f('ix_sync_jobs_id_job'), 'sync_jobs', ['id_job'], unique=False)

    op.create_table('sync_logs',
    sa.Column('id_log', sa.Integer(), nullable=False),
    sa.Column('execution_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('duration_sec', sa.Integer(), nullable=True),
    sa.Column('records_count', sa.Integer(), nullable=True),
    sa.Column('message', sa.String(), nullable=True),
    sa.Column('id_job', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_job'], ['sync_jobs.id_job'], ),
    sa.PrimaryKeyConstraint('id_log')
    )
    op.create_index(op.f('ix_sync_logs_id_log'), 'sync_logs', ['id_log'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_sync_logs_id_log'), table_name='sync_logs')
    op.drop_table('sync_logs')
    op.drop_index(op.f('ix_sync_jobs_id_job'), table_name='sync_jobs')
    op.drop_table('sync_jobs')
    op.drop_index(op.f('ix_kpi_history_id_kpi'), table_name='kpi_history')
    op.drop_table('kpi_history')
    op.drop_index(op.f('ix_kpi_types_id_kpi_type'), table_name='kpi_types')
    op.drop_table('kpi_types')
    op.drop_index(op.f('ix_state_changelogs_id_changelog'), table_name='state_changelogs')
    op.drop_table('state_changelogs')
    op.drop_index(op.f('ix_issues_jira_issue_id'), table_name='issues')
    op.drop_index(op.f('ix_issues_id_issue'), table_name='issues')
    op.drop_table('issues')
    op.drop_index(op.f('ix_sprints_jira_sprint_id'), table_name='sprints')
    op.drop_index(op.f('ix_sprints_id_sprint'), table_name='sprints')
    op.drop_table('sprints')
    op.drop_index(op.f('ix_issue_types_id_type'), table_name='issue_types')
    op.drop_table('issue_types')
    op.drop_index(op.f('ix_project_members_id_project_member'), table_name='project_members')
    op.drop_table('project_members')
    op.drop_index(op.f('ix_boards_jira_board_id'), table_name='boards')
    op.drop_index(op.f('ix_boards_id_board'), table_name='boards')
    op.drop_table('boards')
    op.drop_index(op.f('ix_projects_jira_project_id'), table_name='projects')
    op.drop_index(op.f('ix_projects_id_project'), table_name='projects')
    op.drop_table('projects')
    op.drop_index(op.f('ix_oauth_tokens_id_token'), table_name='oauth_tokens')
    op.drop_table('oauth_tokens')
    op.drop_index(op.f('ix_users_id_user'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_roles_id_role'), table_name='roles')
    op.drop_table('roles')
