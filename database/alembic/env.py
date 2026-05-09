"""
Alembic 迁移环境配置
用于 SQLite 数据库的版本迁移管理
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据设为 None，使用原始 SQL 迁移方式
target_metadata = None


def run_migrations_offline() -> None:
    """
    离线模式运行迁移
    仅生成 SQL 脚本而不实际执行
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        transactional_ddl=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在线模式运行迁移
    直接连接数据库并执行迁移
    """
    url = config.get_main_option("sqlalchemy.url")

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
        connect_args={"check_same_thread": False},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            transactional_ddl=False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
