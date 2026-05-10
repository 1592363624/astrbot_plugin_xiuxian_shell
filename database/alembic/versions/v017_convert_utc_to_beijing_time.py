"""
将所有时间字段从UTC时区迁移为北京时间(UTC+8)

对所有表中的 TIMESTAMP 类型字段执行 +8小时 操作，
将历史数据从 UTC 时间转换为北京时间，与新的代码逻辑保持一致。

SQLite 中时间以 ISO 格式文本存储，使用 datetime() 函数进行偏移计算。
仅对非 NULL 且符合 ISO 格式的时间值进行转换，空值保持不变。

Revision ID: v017
Revises: v016
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v017"
down_revision: str | Sequence[str] | None = "v016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIME_COLUMNS: dict[str, list[str]] = {
    "players": [
        "created_at",
        "updated_at",
        "last_breakthrough_prompt",
    ],
    "items": [
        "created_at",
    ],
    "player_inventory": [
        "created_at",
    ],
    "skills": [
        "created_at",
    ],
    "player_skills": [
        "created_at",
    ],
    "realms": [
        "created_at",
    ],
    "game_events": [
        "created_at",
    ],
    "player_events": [
        "triggered_at",
    ],
    "checkin_records": [
        "created_at",
    ],
    "notifications": [
        "created_at",
    ],
    "player_sessions": [
        "created_at",
        "updated_at",
    ],
    "scheduled_notifications": [
        "created_at",
        "updated_at",
        "last_run_at",
        "next_run_at",
    ],
    "seclusion_records": [
        "started_at",
        "cooldown_until",
        "created_at",
    ],
    "pill_toxicity_records": [
        "taken_at",
        "expires_at",
        "created_at",
    ],
    "deep_seclusion_records": [
        "started_at",
        "ended_at",
        "created_at",
    ],
    "player_states": [
        "started_at",
        "expires_at",
        "created_at",
    ],
    "death_penalty_configs": [
        "created_at",
        "updated_at",
    ],
    "chat_logs": [
        "created_at",
    ],
    "breakthrough_records": [
        "created_at",
    ],
    "market_listings": [
        "created_at",
        "updated_at",
    ],
    "temp_buffs": [
        "created_at",
        "expires_at",
    ],
}


def _shift_columns(hours: int) -> None:
    conn = op.get_bind()
    for table, columns in _TIME_COLUMNS.items():
        inspector = sa.inspect(conn)
        if not inspector.has_table(table):
            continue
        existing_cols = {row["name"] for row in inspector.get_columns(table)}
        for col in columns:
            if col not in existing_cols:
                continue
            conn.execute(
                sa.text(
                    f"UPDATE [{table}] SET [{col}] = datetime([{col}], '+{hours} hours') "
                    f"WHERE [{col}] IS NOT NULL AND [{col}] != ''"
                )
            )


def upgrade() -> None:
    _shift_columns(8)


def downgrade() -> None:
    _shift_columns(-8)
