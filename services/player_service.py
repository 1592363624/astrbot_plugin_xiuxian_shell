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

if TYPE_CHECKING:
    from ..config import ConfigManager


class PlayerService:
    """玩家服务类"""

    def __init__(self, db_manager: DatabaseManager, config_manager: "ConfigManager"):
        """
        初始化玩家服务
        
        Args:
            db_manager: 数据库管理器实例
            config_manager: 配置管理器实例
        """
        self.db = db_manager
        self.config_manager = config_manager
        self._register_timestamps: Dict[str, float] = {}

    def _validate_username(self, username: str) -> Optional[str]:
        """
        校验用户名合法性
        规则：2-10个中文字符
        
        Args:
            username: 用户名
            
        Returns:
            Optional[str]: 校验失败时返回错误信息，成功返回 None
        """
        if not username:
            return "角色名不能为空，请输入2-10个中文字符"
        if not re.fullmatch(r'^[\u4e00-\u9fa5]{2,10}$', username):
            return "角色名仅允许2-10个中文字符，请重新输入"
        return None

    def _check_register_cooldown(self, user_id: str) -> Optional[str]:
        """
        检查注册频率限制
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[str]: 频率限制触发时返回错误信息，否则返回 None
        """
        last_time = self._register_timestamps.get(user_id)
        if last_time is not None:
            cooldown = self.config_manager.get("game.register_cooldown", 60)
            elapsed = time.time() - last_time
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                return f"注册太频繁，请 {remaining} 秒后再试"
        return None

    async def check_player_registered(self, user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        统一检查玩家是否已注册的公共方法
        
        Args:
            user_id: 用户ID
            
        Returns:
            Tuple[Optional[Dict], Optional[str]]: 
                - 已注册: (player_dict, None)
                - 未注册: (None, "你还没有注册修仙角色，请先使用【修仙注册】")
        """
        player = await self.db.fetch_one(
            "SELECT id, username, realm_id, experience, spirit_stone, health, max_health, attack, defense "
            "FROM players WHERE user_id = ?",
            (user_id,)
        )
        if not player:
            return None, "你还没有注册修仙角色，请先使用【修仙注册】"
        return player, None

    async def create_player(self, user_id: str, username: str) -> Player:
        """
        创建新玩家
        
        Args:
            user_id: 用户ID
            username: 用户名
            
        Returns:
            Player: 创建的玩家对象
            
        Raises:
            ValueError: 用户名不合法、频率限制、或玩家已存在
        """
        username = username.strip()

        # 校验用户名合法性
        name_error = self._validate_username(username)
        if name_error:
            raise ValueError(name_error)

        # 检查注册频率限制
        cooldown_error = self._check_register_cooldown(user_id)
        if cooldown_error:
            raise ValueError(cooldown_error)

        # 检查玩家是否已存在
        existing = await self.get_player_by_user_id(user_id)
        if existing:
            raise ValueError("玩家已存在")

        player_id = str(uuid.uuid4())
        sql = """
            INSERT INTO players (id, user_id, username)
            VALUES (?, ?, ?)
        """
        await self.db.execute(sql, (player_id, user_id, username))
        await self.db.commit()

        # 记录注册时间，用于频率限制
        self._register_timestamps[user_id] = time.time()

        logger.info(f"新玩家创建: {username} ({user_id})")
        return await self.get_player_by_id(player_id)

    async def get_player_by_id(self, player_id: str) -> Optional[Player]:
        """
        根据ID获取玩家
        
        Args:
            player_id: 玩家ID
            
        Returns:
            Optional[Player]: 玩家对象或None
        """
        sql = "SELECT * FROM players WHERE id = ?"
        row = await self.db.fetch_one(sql, (player_id,))
        if row:
            return Player.from_dict(row)
        return None

    async def get_player_by_user_id(self, user_id: str) -> Optional[Player]:
        """
        根据用户ID获取玩家
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Player]: 玩家对象或None
        """
        sql = "SELECT * FROM players WHERE user_id = ?"
        row = await self.db.fetch_one(sql, (user_id,))
        if row:
            return Player.from_dict(row)
        return None

    async def get_all_players(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        获取所有玩家（分页）
        
        Args:
            page: 页码
            page_size: 每页数量
            
        Returns:
            Dict[str, Any]: 包含玩家列表和分页信息
        """
        offset = (page - 1) * page_size
        # 获取总数
        count_sql = "SELECT COUNT(*) as total FROM players"
        count_result = await self.db.fetch_one(count_sql)
        total = count_result["total"] if count_result else 0
        
        # 获取分页数据
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
        """
        更新玩家信息
        
        Args:
            player_id: 玩家ID
            **kwargs: 要更新的字段
            
        Returns:
            Optional[Player]: 更新后的玩家对象
        """
        allowed_fields = [
            "username", "realm_id", "experience", "spirit_stone",
            "health", "max_health", "attack", "defense"
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
        """
        删除玩家
        
        Args:
            player_id: 玩家ID
            
        Returns:
            bool: 是否删除成功
        """
        sql = "DELETE FROM players WHERE id = ?"
        cursor = await self.db.execute(sql, (player_id,))
        await self.db.commit()
        return cursor.rowcount > 0

    async def modify_resource(self, player_id: str, field: str, value: int) -> Optional[Player]:
        """
        修改玩家资源（增加或减少）
        正数表示增加，负数表示减少
        
        Args:
            player_id: 玩家ID
            field: 资源字段名
            value: 变化值（正数增加，负数减少）
            
        Returns:
            Optional[Player]: 更新后的玩家对象
        """
        allowed_fields = ["experience", "spirit_stone", "health", "attack", "defense"]
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
