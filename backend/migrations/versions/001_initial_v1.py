"""Initial v1 schema (existing tables).

Revision ID: initial_v1
Create Date: 2026-03-22
"""
from typing import Sequence, Union

revision: str = "initial_v1"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables already exist from schema.sql — this is a baseline stamp.
    pass


def downgrade() -> None:
    pass
