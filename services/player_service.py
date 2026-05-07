"""
玩家服务
处理玩家相关的业务逻辑
"""
import uuid
from typing import Optional, List, Dict, Any
from astrbot.api import logger
from ..database import DatabaseManager
from ..models import Player


class PlayerService:
    """玩家服务类"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化玩家服务
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager

    async def create_player(self, user_id: str, username: str) -> Player:
        """
        创建新玩家
        
        Args:
            user_id: 用户ID
            username: 用户名
            
        Returns:
            Player: 创建的玩家对象
        """
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
