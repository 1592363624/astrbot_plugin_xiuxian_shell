---
name: "astrbot-db-migration"
description: "修仙插件数据库迁移管理。当修改数据库表结构（新增表、增删改列、修改约束/索引）时必须调用此 skill 创建对应的 Alembic 迁移脚本。调用时机：任何涉及 database schema 变更的操作完成后。"
---

# 数据库迁移 - Alembic 版本管理

## 触发规则（必须遵守）

**凡是对数据库表结构做任何变更，都必须创建一个 Alembic 迁移脚本。** 包括但不限于：
- 新增一张表
- 给已有表添加列
- 删除已有列
- 修改列的类型、默认值、nullable 等属性
- 新增/删除索引或约束
- 插入或修改种子数据（默认配置数据）

---

## 操作流程

### 第一步：在 `database/alembic/versions/` 下创建迁移文件

文件命名：`v{序号}_{功能描述}.py`

例如：`v002_add_player_sect.py`、`v003_add_item_durability.py`

### 第二步：填写迁移文件

模板如下——**关键**：`down_revision` 必须正确指向上一个版本的 `revision` 值：

```python
"""
{功能描述}

Revision ID: {版本号}
Revises: {上一个版本号}
Create Date: {当前日期}
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "{版本号}"           # 如 "v002"
down_revision: Union[str, None] = "{上一个版本号}"  # 如 "v001"，首版本为 None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：执行表结构变更"""
    pass  # ← 写入建表/加列/改列等操作


def downgrade() -> None:
    """降级：撤销升级的变更"""
    pass  # ← 写入删表/删列/还原等操作
```

### 第三步：确定 `down_revision` 的值

在 `database/alembic/versions/` 目录中查看已有的迁移文件，找到最新版本的 `revision` 值，将其作为新文件的 `down_revision`。

```
当前已有文件              新文件应设的 down_revision
─────────────────        ─────────────────────────
v001_initial_schema.py   → revision="v001"  → 新文件 down_revision="v001"
（revision="v001"）
```

### 第四步：编写 `upgrade()` 和 `downgrade()`

#### SQLite 注意事项（必须用 batch 模式）

```python
# ✅ 正确：所有列变更包裹在 batch_alter_table 中
with op.batch_alter_table("players") as batch_op:
    batch_op.add_column(sa.Column("new_field", sa.Text, server_default=""))
    batch_op.drop_column("old_field")

# ❌ 错误：直接调用（SQLite 不支持）
op.add_column("players", sa.Column("new_field", sa.Text))
```

#### 常用操作参考

```python
# 创建表
op.create_table(
    "table_name",
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("created_at", sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
)

# 删除表
op.drop_table("table_name")

# 添加列
with op.batch_alter_table("players") as batch_op:
    batch_op.add_column(sa.Column("luck", sa.Integer, server_default="5"))

# 删除列
with op.batch_alter_table("players") as batch_op:
    batch_op.drop_column("luck")

# 执行原始 SQL
op.execute("UPDATE players SET realm_id = 'realm_001' WHERE realm_id IS NULL")

# 插入种子数据
op.bulk_insert(
    sa.table("realms", sa.column("id", sa.Text), sa.column("name", sa.Text)),
    [{"id": "realm_010", "name": "真仙境"}],
)
```

---

## 完整示例

假设上一个版本是 `v001`，现在需要新增"玩家宗门"字段和"宗门表"：

```python
# database/alembic/versions/v002_add_sect_system.py
"""新增宗门系统

Revision ID: v002
Revises: v001
Create Date: 2026-05-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v002"
down_revision: Union[str, None] = "v001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 创建宗门表
    op.create_table(
        "sects",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("leader_id", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )
    
    # 2. 玩家表添加宗门字段
    with op.batch_alter_table("players") as batch_op:
        batch_op.add_column(sa.Column("sect_id", sa.Text, nullable=True))
        batch_op.add_column(sa.Column("sect_position", sa.Text, server_default="弟子"))
    
    # 3. 创建索引
    op.create_index("idx_players_sect", "players", ["sect_id"])


def downgrade() -> None:
    op.drop_index("idx_players_sect", table_name="players")
    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_column("sect_position")
        batch_op.drop_column("sect_id")
    op.drop_table("sects")
```

---

## 幂等性检查（推荐）

为防止重复执行时报错，可在 `upgrade()` 中添加存在性检查：

```python
def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(players)"))
    columns = [row[1] for row in result]
    
    if "sect_id" not in columns:
        with op.batch_alter_table("players") as batch_op:
            batch_op.add_column(sa.Column("sect_id", sa.Text, nullable=True))
```

---

## 必须遵守的原则

1. **一个迁移一个功能**：不要在一个迁移文件中混合多个不相关的变更
2. **双向可逆**：`downgrade()` 必须能完整撤销 `upgrade()` 的效果
3. **不修改历史迁移**：已存在的迁移文件绝对不改，新变更写新迁移文件
4. **正确链式引用**：`down_revision` 必须正确指向直接前驱版本
5. **SQLite 用 batch**：所有列级变更包裹在 `with op.batch_alter_table() as batch_op:` 中

---

## 相关文件路径

| 用途 | 路径 |
|------|------|
| 迁移脚本目录 | `database/alembic/versions/` |
| 迁移环境配置 | `database/alembic/env.py` |
| 主配置文件 | `alembic.ini`（插件根目录） |
| 完整开发指南 | `doc/数据库迁移开发指南.md` |
