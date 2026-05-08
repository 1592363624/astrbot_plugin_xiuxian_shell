"""
玩家服务
处理玩家相关的业务逻辑
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

    async def delete_player(self, player_id: str) -> bool:
        sql = "DELETE FROM players WHERE id = ?"
        cursor = await self.db.execute(sql, (player_id,))
        await self.db.commit()
        return cursor.rowcount > 0

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
