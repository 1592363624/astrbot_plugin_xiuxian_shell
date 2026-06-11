"""
玩家服务
处理玩家相关的业务逻辑，包括注册、查询、修改、删除、重置、软删除等
"""

import re
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from astrbot.api import logger

from ..database import DatabaseManager
from ..models import Player
from ..utils import bj_now, bj_now_iso, bj_today_str, calc_battle_attrs

if TYPE_CHECKING:
    from ..config import ConfigManager
    from .cultivation_service import CultivationService


class PlayerService:
    """玩家服务类"""

    def __init__(self, db_manager: DatabaseManager, config_manager: "ConfigManager", cultivation_service: "CultivationService" = None):
        self.db = db_manager
        self.config_manager = config_manager
        self.cultivation_service = cultivation_service
        self._register_timestamps: dict[str, float] = {}
        self._passive_exp_cooldowns: dict[str, float] = {}
        self._passive_exp_daily: dict[str, int] = {}
        self._daily_stats_ready = False
        self._realms_cache: dict[int, str] = {}

    async def ensure_daily_stats_table(self):
        """
        确保 player_daily_stats 表存在

        此方法在插件初始化时调用，以轻量级方式创建表（不依赖Alembic迁移），
        确保 Bot 重启后被动修为每日上限数据不丢失。
        """
        table_exists = await self.db.table_exists("player_daily_stats")
        if not table_exists:
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS player_daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    stat_date TEXT NOT NULL,
                    passive_exp_accumulated INTEGER DEFAULT 0,
                    UNIQUE(user_id, stat_date)
                )
            """)
            await self.db.commit()
            logger.info("player_daily_stats 表已创建，被动修为每日上限数据将持久化存储")
        self._daily_stats_ready = True

    def _validate_username(self, username: str) -> str | None:
        if not username:
            return "道号不能为空，请输入2-6个中文字符"
        if not re.fullmatch(r"^[\u4e00-\u9fa5]{2,6}$", username):
            return "道号仅允许2-6个中文字符，请重新输入"
        return None

    def _normalize_username(self, username: str, user_id: str) -> str:
        if not username:
            return user_id[:6]
        username = username.strip()
        if not re.fullmatch(r"^[\u4e00-\u9fa5]{2,6}$", username):
            return user_id[:6]
        return username

    def _check_register_cooldown(self, user_id: str) -> str | None:
        last_time = self._register_timestamps.get(user_id)
        if last_time is not None:
            cooldown = self.config_manager.get("game.register_cooldown", 60)
            elapsed = time.time() - last_time
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                return f"注册太频繁，请 {remaining} 秒后再试"
        return None

    async def load_all_players_to_cache(self) -> int:
        """
        加载所有玩家到内存（已废弃，保留方法名兼容旧调用）

        原用于缓存玩家数据，现改为仅统计玩家数量并记录日志。
        玩家数据改为实时查询数据库，避免缓存不一致问题。

        Returns:
            int: 玩家总数
        """
        try:
            rows = await self.db.fetch_all(
                "SELECT id, user_id, username, realm_id, experience, spirit_stone, "
                "bone, spirit, intel, str, percep, luck, "
                "health, mp, stamina FROM players"
            )
            logger.info(f"已加载 {len(rows)} 个玩家信息")
            return len(rows)
        except Exception as e:
            logger.error(f"加载玩家信息失败: {e}")
            return 0

    async def _create_player_internal(self, user_id: str, username: str) -> Player:
        """
        内部方法：创建玩家记录

        后天属性初始全部为0，通过修炼/装备/机遇等行为增长。
        以凡人境（level=1）计算初始资源值后写入数据库。
        战斗属性（衍生属性）不存入数据库，动态计算。
        """
        battle_attrs = calc_battle_attrs(
            level=1, bone=0, spirit=0, intel=0, str_=0, percep=0, luck=0
        )

        player_id = str(uuid.uuid4())
        sql = """
            INSERT INTO players (
                id, user_id, username,
                bone, spirit, intel, str, percep, luck,
                health, mp, stamina
            ) VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, ?, ?, ?)
        """
        await self.db.execute(
            sql,
            (
                player_id,
                user_id,
                username,
                battle_attrs["max_health"],
                battle_attrs["max_mp"],
                battle_attrs["max_stamina"],
            ),
        )
        await self.db.commit()

        return await self.get_player_by_id(player_id)

    async def auto_register_player(
        self, user_id: str, username: str = None
    ) -> dict[str, Any]:
        username = self._normalize_username(username, user_id)

        player = await self._create_player_internal(user_id, username)
        if player:
            player_dict = player.to_dict()
            logger.info(f"自动注册新玩家: {username} ({user_id})")
            return player_dict

        return {}

    async def check_player_registered(
        self, user_id: str
    ) -> tuple[dict[str, Any] | None, str | None]:
        """
        检查玩家是否已注册

        直接从数据库查询玩家信息，不使用缓存，
        确保每次获取的都是最新数据，避免缓存不一致问题。

        Args:
            user_id: 用户ID

        Returns:
            tuple[dict|None, str|None]: (玩家数据, 错误信息)
        """
        player = await self.db.fetch_one(
            "SELECT id, user_id, username, realm_id, experience, spirit_stone, "
            "bone, spirit, intel, str, percep, luck, "
            "health, mp, stamina "
            "FROM players WHERE user_id = ?",
            (user_id,),
        )
        if not player:
            return None, "你还没有修仙角色，系统将自动为你创建..."

        return player, None

    async def create_player(self, user_id: str, username: str) -> Player:
        username = username.strip()

        name_error = self._validate_username(username)
        if name_error:
            raise ValueError(name_error)

        cooldown_error = self._check_register_cooldown(user_id)
        if cooldown_error:
            raise ValueError(cooldown_error)

        existing = await self.get_player_by_user_id(user_id)
        if existing:
            raise ValueError("玩家已存在")

        player = await self._create_player_internal(user_id, username)

        self._register_timestamps[user_id] = time.time()

        logger.info(f"新玩家创建: {username} ({user_id})")
        return player

    async def get_player_by_id(self, player_id: str) -> Player | None:
        sql = "SELECT * FROM players WHERE id = ?"
        row = await self.db.fetch_one(sql, (player_id,))
        if row:
            return Player.from_dict(row)
        return None

    async def get_player_by_user_id(self, user_id: str) -> Player | None:
        sql = "SELECT * FROM players WHERE user_id = ?"
        row = await self.db.fetch_one(sql, (user_id,))
        if row:
            return Player.from_dict(row)
        return None

    async def get_all_players(
        self, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        count_sql = "SELECT COUNT(*) as total FROM players"
        count_result = await self.db.fetch_one(count_sql)
        total = count_result["total"] if count_result else 0

        sql = "SELECT * FROM players ORDER BY created_at DESC LIMIT ? OFFSET ?"
        rows = await self.db.fetch_all(sql, (page_size, offset))
        players = [Player.from_dict(row) for row in rows]

        return {
            "players": [p.to_dict() for p in players],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    async def update_player(self, player_id: str, **kwargs) -> Player | None:
        allowed_fields = [
            "username",
            "realm_id",
            "experience",
            "spirit_stone",
            "bone",
            "spirit",
            "intel",
            "str",
            "percep",
            "luck",
            "health",
            "mp",
            "stamina",
        ]
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if not updates:
            return await self.get_player_by_id(player_id)

        values.append(bj_now_iso())
        values.append(player_id)
        sql = f"""
            UPDATE players
            SET {", ".join(updates)}, updated_at = ?
            WHERE id = ?
        """
        await self.db.execute(sql, tuple(values))
        await self.db.commit()

        return await self.get_player_by_id(player_id)

    async def delete_player(self, player_id: str, user_id: str = None) -> bool:
        """
        彻底删除玩家及其所有关联数据（级联删除）

        删除范围包括：
        - 玩家储物袋物品 (player_inventory)
        - 玩家功法 (player_skills)
        - 玩家事件记录 (player_events)
        - 签到记录 (checkin_records)
        - 闭关记录 (seclusion_records)
        - 丹毒记录 (pill_toxicity_records)
        - 玩家会话 (player_sessions)
        - 玩家主表 (players)

        Args:
            player_id: 玩家ID
            user_id: 用户ID（可选，用于删除会话记录）

        Returns:
            bool: 是否删除成功
        """
        try:
            # 1. 删除玩家背包
            await self.db.execute(
                "DELETE FROM player_inventory WHERE player_id = ?", (player_id,)
            )
            # 2. 删除玩家功法
            await self.db.execute(
                "DELETE FROM player_skills WHERE player_id = ?", (player_id,)
            )
            # 3. 删除玩家事件记录
            await self.db.execute(
                "DELETE FROM player_events WHERE player_id = ?", (player_id,)
            )
            # 4. 删除签到记录
            await self.db.execute(
                "DELETE FROM checkin_records WHERE player_id = ?", (player_id,)
            )
            # 5. 删除闭关记录
            await self.db.execute(
                "DELETE FROM seclusion_records WHERE player_id = ?", (player_id,)
            )
            # 6. 删除丹毒记录
            await self.db.execute(
                "DELETE FROM pill_toxicity_records WHERE player_id = ?", (player_id,)
            )
            # 7. 删除玩家主表
            cursor = await self.db.execute(
                "DELETE FROM players WHERE id = ?", (player_id,)
            )
            # 8. 删除会话记录（如果有 user_id）
            if user_id:
                await self.db.execute(
                    "DELETE FROM player_sessions WHERE user_id = ?", (user_id,)
                )

            await self.db.commit()

            logger.info(f"玩家 {player_id} 及其所有关联数据已被彻底删除")
            return cursor.rowcount > 0
        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除玩家 {player_id} 失败: {e}")
            return False

    async def reset_player(self, player_id: str, user_id: str = None) -> Player | None:
        """
        重置玩家数据，保留账号但清空所有游戏进度

        清空范围包括：
        - 背包物品
        - 已学功法
        - 事件记录
        - 签到记录
        - 闭关记录
        - 丹毒记录

        重置玩家属性到初始状态：
        - 境界回到 realm_001（凡人）
        - 修为清零
        - 灵石回到初始值 100
        - 后天属性清零
        - 气血/法力/体力回到初始值

        Args:
            player_id: 玩家ID
            user_id: 用户ID（可选，用于更新缓存）

        Returns:
            Optional[Player]: 重置后的玩家对象，失败返回 None
        """
        try:
            # 1. 清空玩家储物袋
            await self.db.execute(
                "DELETE FROM player_inventory WHERE player_id = ?", (player_id,)
            )
            # 2. 清空玩家功法
            await self.db.execute(
                "DELETE FROM player_skills WHERE player_id = ?", (player_id,)
            )
            # 3. 清空玩家事件记录
            await self.db.execute(
                "DELETE FROM player_events WHERE player_id = ?", (player_id,)
            )
            # 4. 清空签到记录
            await self.db.execute(
                "DELETE FROM checkin_records WHERE player_id = ?", (player_id,)
            )
            # 5. 清空闭关记录
            await self.db.execute(
                "DELETE FROM seclusion_records WHERE player_id = ?", (player_id,)
            )
            # 6. 清空丹毒记录
            await self.db.execute(
                "DELETE FROM pill_toxicity_records WHERE player_id = ?", (player_id,)
            )

            # 7. 重置玩家属性到初始状态
            battle_attrs = calc_battle_attrs(
                level=1, bone=0, spirit=0, intel=0, str_=0, percep=0, luck=0
            )
            await self.db.execute(
                """
                UPDATE players
                SET realm_id = 'realm_001',
                    experience = 0,
                    spirit_stone = 100,
                    bone = 0,
                    spirit = 0,
                    intel = 0,
                    str = 0,
                    percep = 0,
                    luck = 0,
                    health = ?,
                    mp = ?,
                    stamina = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    battle_attrs["max_health"],
                    battle_attrs["max_mp"],
                    battle_attrs["max_stamina"],
                    bj_now_iso(),
                    player_id,
                ),
            )
            await self.db.commit()

            logger.info(f"玩家 {player_id} 数据已重置")
            return await self.get_player_by_id(player_id)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"重置玩家 {player_id} 失败: {e}")
            return None

    async def soft_delete_player(
        self, player_id: str, user_id: str = None, ban_reason: str = None
    ) -> bool:
        """
        软删除玩家（封禁/BAN）

        不真正删除数据，而是将 is_deleted 标记为 1，
        被软删除的玩家无法正常使用游戏功能。

        Args:
            player_id: 玩家ID
            user_id: 用户ID（可选，用于更新缓存）
            ban_reason: 封禁理由（可选，记录封禁原因）

        Returns:
            bool: 是否操作成功
        """
        try:
            cursor = await self.db.execute(
                """
                UPDATE players
                SET is_deleted = 1,
                    ban_reason = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (ban_reason, bj_now_iso(), player_id),
            )
            await self.db.commit()

            reason_text = f"，理由：{ban_reason}" if ban_reason else ""
            logger.info(f"玩家 {player_id} 已被软删除（封禁）{reason_text}")
            return cursor.rowcount > 0
        except Exception as e:
            await self.db.rollback()
            logger.error(f"软删除玩家 {player_id} 失败: {e}")
            return False

    async def restore_player(self, player_id: str) -> bool:
        """
        恢复被软删除的玩家（解封）

        将 is_deleted 标记重置为 0，清空 ban_reason，恢复玩家正常使用权限。

        Args:
            player_id: 玩家ID

        Returns:
            bool: 是否操作成功
        """
        try:
            cursor = await self.db.execute(
                """
                UPDATE players
                SET is_deleted = 0,
                    ban_reason = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (bj_now_iso(), player_id),
            )
            await self.db.commit()

            logger.info(f"玩家 {player_id} 已恢复（解封）")
            return cursor.rowcount > 0
        except Exception as e:
            await self.db.rollback()
            logger.error(f"恢复玩家 {player_id} 失败: {e}")
            return False

    async def is_player_banned(self, player_id: str) -> bool:
        """
        检查玩家是否被封禁

        Args:
            player_id: 玩家ID

        Returns:
            bool: 是否被封禁
        """
        row = await self.db.fetch_one(
            "SELECT is_deleted FROM players WHERE id = ?", (player_id,)
        )
        return bool(row and row.get("is_deleted"))

    async def get_ban_info(self, player_id: str) -> dict:
        """
        获取玩家封禁信息

        Args:
            player_id: 玩家ID

        Returns:
            dict: 包含 is_banned 和 ban_reason 的字典
        """
        row = await self.db.fetch_one(
            "SELECT is_deleted, ban_reason FROM players WHERE id = ?", (player_id,)
        )
        if not row:
            return {"is_banned": False, "ban_reason": None}
        return {
            "is_banned": bool(row.get("is_deleted")),
            "ban_reason": row.get("ban_reason"),
        }

    async def modify_resource(
        self, player_id: str, field: str, value: int
    ) -> Player | None:
        allowed_fields = [
            "experience",
            "spirit_stone",
            "health",
            "mp",
            "stamina",
            "bone",
            "spirit",
            "intel",
            "str",
            "percep",
            "luck",
        ]
        if field not in allowed_fields:
            raise ValueError(f"不允许修改字段: {field}")

        # 修为字段通过统一入口处理截断和溢出
        if field == "experience" and self.cultivation_service:
            await self.cultivation_service.add_experience(player_id, value)
            return await self.get_player_by_id(player_id)

        sql = f"""
            UPDATE players
            SET {field} = MAX(0, {field} + ?), updated_at = ?
            WHERE id = ?
        """
        await self.db.execute(sql, (value, bj_now_iso(), player_id))
        await self.db.commit()

        return await self.get_player_by_id(player_id)

    async def change_username(
        self, user_id: str, new_username: str
    ) -> tuple[str | None, str | None]:
        new_username = self._normalize_username(new_username, user_id)

        name_error = self._validate_username(new_username)
        if name_error:
            return None, name_error

        player = await self.get_player_by_user_id(user_id)
        if not player:
            return None, "你还没有修仙角色"

        existing = await self.db.fetch_one(
            "SELECT id FROM players WHERE username = ? AND user_id != ?",
            (new_username, user_id),
        )
        if existing:
            return None, "该道号已被其他修士使用，请换一个"

        sql = """
            UPDATE players
            SET username = ?, updated_at = ?
            WHERE user_id = ?
        """
        await self.db.execute(sql, (new_username, bj_now_iso(), user_id))
        await self.db.commit()

        logger.info(f"玩家 {user_id} 修改道号: {player.username} -> {new_username}")
        return new_username, None

    async def add_passive_experience(
        self, player_id: str, user_id: str, message_content: str, group_id: str | None
    ) -> dict[str, Any]:
        """
        为玩家增加被动发言修为

        群聊有效发言自动增加微量修为，受境界上限控制。
        超过当前境界升级所需修为的部分会存入临时修为。
        包含防刷机制：n秒冷却、消息长度限制、每日上限。

        Args:
            player_id: 玩家ID
            user_id: 用户ID
            message_content: 发言内容
            group_id: 群组ID（群聊时传入）

        Returns:
            Dict[str, Any]: 增长结果
        """
        # 获取防刷配置
        config_rows = await self.db.fetch_all(
            "SELECT config_key, config_value FROM death_penalty_configs WHERE config_key IN (?, ?, ?, ?)",
            (
                "passive_exp_per_message",
                "passive_exp_cooldown_seconds",
                "passive_exp_min_message_length",
                "passive_exp_daily_limit",
            ),
        )
        configs = {row["config_key"]: row["config_value"] for row in config_rows}

        exp_per_message = int(configs.get("passive_exp_per_message", 10))
        cooldown_seconds = int(configs.get("passive_exp_cooldown_seconds", 30))
        min_length = int(configs.get("passive_exp_min_message_length", 3))
        daily_limit = int(configs.get("passive_exp_daily_limit", 200))

        if exp_per_message <= 0:
            return {"gained": 0, "message": "", "needs_breakthrough": False}

        # 防刷：消息长度检查
        if len(message_content.strip()) < min_length:
            return {"gained": 0, "message": "", "needs_breakthrough": False}

        # 防刷：冷却时间检查
        now = bj_now()
        now_timestamp = now.timestamp()
        last_time = self._passive_exp_cooldowns.get(user_id)
        if last_time is not None:
            elapsed = now_timestamp - last_time
            if elapsed < cooldown_seconds:
                return {"gained": 0, "message": "", "needs_breakthrough": False}

        # 防刷：每日上限检查（使用本地时区日期，确保"每日"边界对齐用户自然日）
        today_str = bj_today_str()
        daily_key = f"{user_id}:{today_str}"
        current_daily = self._passive_exp_daily.get(daily_key)
        if current_daily is None:
            if self._daily_stats_ready:
                db_record = await self.db.fetch_one(
                    "SELECT passive_exp_accumulated FROM player_daily_stats WHERE user_id = ? AND stat_date = ?",
                    (user_id, today_str),
                )
                current_daily = db_record["passive_exp_accumulated"] if db_record else 0
                self._passive_exp_daily[daily_key] = current_daily
            else:
                current_daily = 0

        if current_daily >= daily_limit:
            return {"gained": 0, "message": "", "needs_breakthrough": False}

        # 清理过期的每日累计key（非今日的key不再需要，避免内存泄漏）
        # 降低阈值到300，并且每天至少触发一次清理
        if len(self._passive_exp_daily) > 300:
            expired_keys = [k for k in self._passive_exp_daily if not k.endswith(today_str)]
            for k in expired_keys:
                del self._passive_exp_daily[k]

        # 计算本次实际可获得的修为（不超过每日上限）
        remaining_daily = daily_limit - current_daily
        actual_exp_gain = min(exp_per_message, remaining_daily)
        if actual_exp_gain <= 0:
            return {"gained": 0, "message": "", "needs_breakthrough": False}

        # 更新冷却和每日累计（内存 + 数据库双重持久化）
        self._passive_exp_cooldowns[user_id] = now_timestamp
        new_daily = current_daily + actual_exp_gain
        self._passive_exp_daily[daily_key] = new_daily

        if self._daily_stats_ready:
            await self.db.execute(
                """INSERT INTO player_daily_stats (user_id, stat_date, passive_exp_accumulated)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, stat_date) DO UPDATE SET passive_exp_accumulated = ?""",
                (user_id, today_str, new_daily, new_daily),
            )
            await self.db.commit()

        # 获取玩家当前境界和修为
        player = await self.db.fetch_one(
            "SELECT * FROM players WHERE id = ?",
            (player_id,),
        )
        if not player:
            return {"gained": 0, "message": "", "needs_breakthrough": False}

        realm_name = "未知"
        exp_cap = 0
        if self.cultivation_service:
            realm = await self.cultivation_service.get_realm_by_id(player["realm_id"])
            if realm:
                realm_name = realm.name
            exp_cap = await self.cultivation_service.get_exp_cap_for_realm(player["realm_id"])

        current_exp = player["experience"]

        # 通过统一入口增加修为，自动处理截断和溢出
        if self.cultivation_service:
            exp_result = await self.cultivation_service.add_experience(player_id, actual_exp_gain)
            new_exp = exp_result["current_exp"]
            temp_exp = exp_result["temp_exp"]
            overflow = exp_result["overflow"]
        else:
            await self.db.execute(
                """
                UPDATE players
                SET experience = experience + ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (actual_exp_gain, bj_now_iso(), player_id),
            )
            await self.db.commit()
            updated_player = await self.db.fetch_one(
                "SELECT experience, temp_experience FROM players WHERE id = ?",
                (player_id,),
            )
            new_exp = updated_player["experience"] if updated_player else current_exp
            temp_exp = updated_player.get("temp_experience", 0) if updated_player else 0
            overflow = 0

        # 记录发言日志
        log_id = str(uuid.uuid4())
        await self.db.execute(
            """
            INSERT INTO chat_logs (id, player_id, user_id, username, realm_name, experience, message_content, group_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                player_id,
                user_id,
                player["username"],
                realm_name,
                current_exp,
                message_content,
                group_id,
            ),
        )
        await self.db.commit()

        result = {
            "gained": actual_exp_gain,
            "actual_exp": new_exp,
            "overflow": overflow,
            "message": f"你在群聊中有所感悟，修为增加{actual_exp_gain}点。",
        }

        logger.info(
            f"玩家 {player_id} 被动增长修为 +{actual_exp_gain}，当前修为: {new_exp}，临时修为: {temp_exp + overflow}"
        )
        return result

    async def _get_realms_cache(self) -> dict[int, str]:
        """获取境界等级→名称映射缓存，避免重复查询"""
        if not self._realms_cache and self.cultivation_service:
            realms = await self.cultivation_service.get_all_realms()
            self._realms_cache = {r.level: r.name for r in realms}
        return self._realms_cache

    async def get_leaderboard(
        self, category: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        获取排行榜

        Args:
            category: 排行类别 - realm(境界修为)/chat(发言次数)/wealth(财富值)
            limit: 返回数量

        Returns:
            List[Dict[str, Any]]: 排行列表
        """
        realms_cache = await self._get_realms_cache()

        if category == "realm":
            # 按境界等级降序，同境界按修为降序
            rows = await self.db.fetch_all(
                """
                SELECT username, experience, realm_level,
                       bone, spirit, intel, str, percep, luck
                FROM players
                WHERE is_deleted = 0 OR is_deleted IS NULL
                ORDER BY realm_level DESC, experience DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [
                {
                    "rank": i + 1,
                    "username": row["username"],
                    "realm_name": realms_cache.get(row["realm_level"], "未知"),
                    "experience": row["experience"],
                    "realm_level": row["realm_level"],
                    "total_attrs": (
                        row["bone"]
                        + row["spirit"]
                        + row["intel"]
                        + row["str"]
                        + row["percep"]
                        + row["luck"]
                    ),
                }
                for i, row in enumerate(rows)
            ]

        elif category == "chat":
            # 按发言次数降序
            rows = await self.db.fetch_all(
                """
                SELECT p.username, p.realm_level, COUNT(c.id) as chat_count
                FROM players p
                LEFT JOIN chat_logs c ON p.id = c.player_id
                WHERE p.is_deleted = 0 OR p.is_deleted IS NULL
                GROUP BY p.id
                ORDER BY chat_count DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [
                {
                    "rank": i + 1,
                    "username": row["username"],
                    "realm_name": realms_cache.get(row["realm_level"], "未知"),
                    "chat_count": row["chat_count"],
                }
                for i, row in enumerate(rows)
            ]

        elif category == "wealth":
            # 按灵石数量降序
            rows = await self.db.fetch_all(
                """
                SELECT username, realm_level, spirit_stone
                FROM players
                WHERE is_deleted = 0 OR is_deleted IS NULL
                ORDER BY spirit_stone DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [
                {
                    "rank": i + 1,
                    "username": row["username"],
                    "realm_name": realms_cache.get(row["realm_level"], "未知"),
                    "spirit_stone": row["spirit_stone"],
                }
                for i, row in enumerate(rows)
            ]

        return []

    async def get_chat_logs(
        self,
        page: int = 1,
        page_size: int = 100,
        sort_field: str = "created_at",
        sort_order: str = "DESC",
        keyword: str = None,
    ) -> dict[str, Any]:
        """
        获取发言日志（后台管理用）

        Args:
            page: 页码
            page_size: 每页数量
            sort_field: 排序字段
            sort_order: 排序方向 ASC/DESC
            keyword: 模糊查询关键词

        Returns:
            Dict[str, Any]: 分页结果
        """
        # 验证排序字段，防止SQL注入
        allowed_sort_fields = {"created_at", "username", "realm_name", "experience"}
        if sort_field not in allowed_sort_fields:
            sort_field = "created_at"
        sort_order = "ASC" if sort_order.upper() == "ASC" else "DESC"

        # 构建查询条件
        where_clause = ""
        params = []
        if keyword:
            where_clause = "WHERE c.username LIKE ? OR c.message_content LIKE ? OR c.realm_name LIKE ?"
            like_keyword = f"%{keyword}%"
            params = [like_keyword, like_keyword, like_keyword]

        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM chat_logs c {where_clause}"
        count_result = await self.db.fetch_one(count_sql, tuple(params))
        total = count_result["total"] if count_result else 0

        # 查询数据
        offset = (page - 1) * page_size
        data_sql = f"""
            SELECT c.*, p.user_id
            FROM chat_logs c
            LEFT JOIN players p ON c.player_id = p.id
            {where_clause}
            ORDER BY c.{sort_field} {sort_order}
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        rows = await self.db.fetch_all(data_sql, tuple(params))

        return {
            "logs": [dict(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
