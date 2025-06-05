"""Create LTI results table

Revision ID: 440475e5a399
Revises:
Create Date: 2023-01-01
"""

import sqlalchemy as sa
from CTFd.plugins.migrations import get_all_tables

revision = "440475e5a399"
down_revision = None
branch_labels = None
depends_on = None


def upgrade(op=None):
    tables = get_all_tables(op=op)
    if "lti_results" not in tables:
        op.create_table(
            "lti_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("sourcedid", sa.Text(), nullable=True),
            sa.Column("service_url", sa.Text(), nullable=True),
            sa.Column("sent", sa.Boolean(), default=False),
        )


def downgrade(op=None):
    tables = get_all_tables(op=op)
    if "lti_results" in tables:
        op.drop_table("lti_results")
