"""
玩家服务
处理玩家相关的业务逻辑，包括注册、查询、修改、删除、重置、软删除等
"""
import re
import time
import uuid
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from astrbot.api import logger
from ..database import DatabaseManager
from ..models import Player
from ..utils import calc_battle_attrs

if TYPE_CHECKING:
    from ..config import ConfigManager


class PlayerService:
    """玩家服务类"""

    def __init__(self, db_manager: DatabaseManager, config_manager: "ConfigManager"):
        self.db = db_manager
        self.config_manager = config_manager
        self._register_timestamps: Dict[str, float] = {}
        self._registered_players_cache: Dict[str, Dict[str, Any]] = {}

    def _validate_username(self, username: str) -> Optional[str]:
        if not username:
            return "角色名不能为空，请输入2-10个中文字符"
        if not re.fullmatch(r'^[\u4e00-\u9fa5]{2,10}$', username):
            return "角色名仅允许2-10个中文字符，请重新输入"
        return None

    def _check_register_cooldown(self, user_id: str) -> Optional[str]:
        last_time = self._register_timestamps.get(user_id)
        if last_time is not None:
            cooldown = self.config_manager.get("game.register_cooldown", 60)
            elapsed = time.time() - last_time
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                return f"注册太频繁，请 {remaining} 秒后再试"
        return None

    async def load_all_players_to_cache(self) -> int:
        try:
            rows = await self.db.fetch_all(
                "SELECT id, user_id, username, realm_id, experience, spirit_stone, "
                "bone, spirit, intel, str, percep, luck, "
                "health, mp, stamina FROM players"
            )
            self._registered_players_cache.clear()
            for row in rows:
                self._registered_players_cache[row["user_id"]] = row
            logger.info(f"已加载 {len(rows)} 个玩家到内存缓存")
            return len(rows)
        except Exception as e:
            logger.error(f"加载玩家缓存失败: {e}")
            return 0

    async def _create_player_internal(
        self, user_id: str, username: str
    ) -> Player:
        """
        内部方法：创建玩家记录

        后天属性初始全部为0，通过修炼/装备/机遇等行为增长。
        以凡人境（level=1）计算初始资源值后写入数据库。
        战斗属性（衍生属性）不存入数据库，动态计算。
        """
        battle_attrs = calc_battle_attrs(level=1, bone=0, spirit=0, intel=0, str_=0, percep=0, luck=0)

        player_id = str(uuid.uuid4())
        sql = """
            INSERT INTO players (
                id, user_id, username,
                bone, spirit, intel, str, percep, luck,
                health, mp, stamina
            ) VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, ?, ?, ?)
        """
        await self.db.execute(sql, (
            player_id, user_id, username,
            battle_attrs["max_health"], battle_attrs["max_mp"], battle_attrs["max_stamina"],
        ))
        await self.db.commit()

        return await self.get_player_by_id(player_id)

    async def auto_register_player(self, user_id: str, username: str = None) -> Dict[str, Any]:
        if not username:
            username = user_id

        player = await self._create_player_internal(user_id, username)
        if player:
            player_dict = player.to_dict()
            self._registered_players_cache[user_id] = player_dict
            logger.info(f"自动注册新玩家: {username} ({user_id})")
            return player_dict

        return {}

    async def check_player_registered(self, user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if user_id in self._registered_players_cache:
            return self._registered_players_cache[user_id], None

        player = await self.db.fetch_one(
            "SELECT id, user_id, username, realm_id, experience, spirit_stone, "
            "bone, spirit, intel, str, percep, luck, "
            "health, mp, stamina "
            "FROM players WHERE user_id = ?",
            (user_id,)
        )
        if not player:
            return None, "你还没有修仙角色，系统将自动为你创建..."

        self._registered_players_cache[user_id] = player
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

    async def get_player_by_id(self, player_id: str) -> Optional[Player]:
        sql = "SELECT * FROM players WHERE id = ?"
        row = await self.db.fetch_one(sql, (player_id,))
        if row:
            return Player.from_dict(row)
        return None

    async def get_player_by_user_id(self, user_id: str) -> Optional[Player]:
        sql = "SELECT * FROM players WHERE user_id = ?"
        row = await self.db.fetch_one(sql, (user_id,))
        if row:
            return Player.from_dict(row)
        return None

    async def get_all_players(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
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

    async def update_player(self, player_id: str, **kwargs) -> Optional[Player]:
        allowed_fields = [
            "username", "realm_id", "experience", "spirit_stone",
            "bone", "spirit", "intel", "str", "percep", "luck",
            "health", "mp", "stamina",
        ]
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if not updates:
            return await self.get_player_by_id(player_id)

        values.append(player_id)
        sql = f"""
            UPDATE players 
            SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        await self.db.execute(sql, tuple(values))
        await self.db.commit()

        return await self.get_player_by_id(player_id)

    async def delete_player(self, player_id: str, user_id: str = None) -> bool:
        """
        彻底删除玩家及其所有关联数据（级联删除）

        删除范围包括：
        - 玩家背包物品 (player_inventory)
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

            # 清理缓存
            if user_id and user_id in self._registered_players_cache:
                del self._registered_players_cache[user_id]

            logger.info(f"玩家 {player_id} 及其所有关联数据已被彻底删除")
            return cursor.rowcount > 0
        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除玩家 {player_id} 失败: {e}")
            return False

    async def reset_player(self, player_id: str, user_id: str = None) -> Optional[Player]:
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
            # 1. 清空玩家背包
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
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    battle_attrs["max_health"],
                    battle_attrs["max_mp"],
                    battle_attrs["max_stamina"],
                    player_id,
                ),
            )
            await self.db.commit()

            # 更新缓存
            if user_id and user_id in self._registered_players_cache:
                del self._registered_players_cache[user_id]

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
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (ban_reason, player_id),
            )
            await self.db.commit()

            # 清理缓存
            if user_id and user_id in self._registered_players_cache:
                del self._registered_players_cache[user_id]

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
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (player_id,),
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

    async def modify_resource(self, player_id: str, field: str, value: int) -> Optional[Player]:
        allowed_fields = [
            "experience", "spirit_stone",
            "health", "mp", "stamina",
            "bone", "spirit", "intel", "str", "percep", "luck",
        ]
        if field not in allowed_fields:
            raise ValueError(f"不允许修改字段: {field}")

        sql = f"""
            UPDATE players 
            SET {field} = MAX(0, {field} + ?), updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        await self.db.execute(sql, (value, player_id))
        await self.db.commit()

        return await self.get_player_by_id(player_id)

    async def change_username(self, user_id: str, new_username: str) -> Tuple[Optional[str], Optional[str]]:
        name_error = self._validate_username(new_username)
        if name_error:
            return None, name_error

        player = await self.get_player_by_user_id(user_id)
        if not player:
            return None, "你还没有修仙角色"

        existing = await self.db.fetch_one(
            "SELECT id FROM players WHERE username = ? AND user_id != ?",
            (new_username, user_id)
        )
        if existing:
            return None, "该道号已被其他修士使用，请换一个"

        sql = """
            UPDATE players 
            SET username = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """
        await self.db.execute(sql, (new_username, user_id))
        await self.db.commit()

        if user_id in self._registered_players_cache:
            self._registered_players_cache[user_id]["username"] = new_username

        logger.info(f"玩家 {user_id} 修改道号: {player.username} -> {new_username}")
        return new_username, None
