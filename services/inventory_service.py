"""
背包服务
处理物品和背包相关的业务逻辑
"""
import uuid
from typing import Optional, List, Dict, Any
from astrbot.api import logger
from ..database import DatabaseManager
from ..models import Item, InventoryItem


class InventoryService:
    """背包服务类"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化背包服务
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager

    async def get_player_inventory(self, player_id: str) -> List[Dict[str, Any]]:
        """
        获取玩家背包
        
        Args:
            player_id: 玩家ID
            
        Returns:
            List[Dict[str, Any]]: 背包物品列表
        """
        sql = """
            SELECT pi.*, i.name, i.description, i.item_type, i.rarity, i.effect_type, i.effect_value
            FROM player_inventory pi
            JOIN items i ON pi.item_id = i.id
            WHERE pi.player_id = ?
            ORDER BY pi.created_at DESC
        """
        rows = await self.db.fetch_all(sql, (player_id,))
        return rows

    async def add_item(self, player_id: str, item_id: str, quantity: int = 1) -> Dict[str, Any]:
        """
        添加物品到背包
        
        Args:
            player_id: 玩家ID
            item_id: 物品ID
            quantity: 数量
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        # 检查物品是否存在
        item = await self.get_item_by_id(item_id)
        if not item:
            raise ValueError("物品不存在")
        
        # 检查玩家背包中是否已有该物品
        existing = await self.db.fetch_one(
            "SELECT * FROM player_inventory WHERE player_id = ? AND item_id = ?",
            (player_id, item_id)
        )
        
        if existing:
            # 更新数量
            await self.db.execute(
                "UPDATE player_inventory SET quantity = quantity + ? WHERE id = ?",
                (quantity, existing["id"])
            )
        else:
            # 新增物品
            inventory_id = str(uuid.uuid4())
            await self.db.execute(
                "INSERT INTO player_inventory (id, player_id, item_id, quantity) VALUES (?, ?, ?, ?)",
                (inventory_id, player_id, item_id, quantity)
            )
        
        await self.db.commit()
        
        return {
            "success": True,
            "item_name": item.name,
            "quantity": quantity,
            "message": f"获得 {quantity} 个【{item.name}】",
        }

    async def remove_item(self, player_id: str, item_id: str, quantity: int = 1) -> Dict[str, Any]:
        """
        从背包移除物品
        
        Args:
            player_id: 玩家ID
            item_id: 物品ID
            quantity: 数量
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        existing = await self.db.fetch_one(
            "SELECT * FROM player_inventory WHERE player_id = ? AND item_id = ?",
            (player_id, item_id)
        )
        
        if not existing:
            raise ValueError("物品不存在于背包中")
        
        if existing["quantity"] < quantity:
            raise ValueError("物品数量不足")
        
        if existing["quantity"] == quantity:
            # 删除记录
            await self.db.execute(
                "DELETE FROM player_inventory WHERE id = ?",
                (existing["id"],)
            )
        else:
            # 减少数量
            await self.db.execute(
                "UPDATE player_inventory SET quantity = quantity - ? WHERE id = ?",
                (quantity, existing["id"])
            )
        
        await self.db.commit()
        
        item = await self.get_item_by_id(item_id)
        return {
            "success": True,
            "item_name": item.name if item else "未知物品",
            "quantity": quantity,
            "message": f"使用了 {quantity} 个【{item.name if item else '未知物品'}】",
        }

    async def use_item(self, player_id: str, item_id: str) -> Dict[str, Any]:
        """
        使用物品
        
        Args:
            player_id: 玩家ID
            item_id: 物品ID
            
        Returns:
            Dict[str, Any]: 使用结果
        """
        # 获取物品信息
        item = await self.get_item_by_id(item_id)
        if not item:
            raise ValueError("物品不存在")
        
        if not item.is_usable:
            raise ValueError("该物品不可使用")
        
        # 检查玩家是否有该物品
        inventory_item = await self.db.fetch_one(
            "SELECT * FROM player_inventory WHERE player_id = ? AND item_id = ?",
            (player_id, item_id)
        )
        
        if not inventory_item or inventory_item["quantity"] <= 0:
            raise ValueError("你没有这个物品")
        
        # 应用物品效果
        effect_message = await self._apply_item_effect(player_id, item)
        
        # 移除物品
        await self.remove_item(player_id, item_id, 1)
        
        return {
            "success": True,
            "item_name": item.name,
            "effect_message": effect_message,
            "message": f"使用了【{item.name}】，{effect_message}",
        }

    async def _apply_item_effect(self, player_id: str, item: Item) -> str:
        """
        应用物品效果
        
        Args:
            player_id: 玩家ID
            item: 物品对象
            
        Returns:
            str: 效果描述
        """
        if item.effect_type == "heal":
            # 恢复生命值
            await self.db.execute(
                "UPDATE players SET health = MIN(max_health, health + ?) WHERE id = ?",
                (item.effect_value, player_id)
            )
            await self.db.commit()
            return f"恢复了 {item.effect_value} 点生命值"
        
        elif item.effect_type == "exp":
            # 增加修为
            await self.db.execute(
                "UPDATE players SET experience = experience + ? WHERE id = ?",
                (item.effect_value, player_id)
            )
            await self.db.commit()
            return f"增加了 {item.effect_value} 点修为"
        
        elif item.effect_type == "attack":
            # 临时增加攻击（可设计为buff）
            return f"攻击力临时提升 {item.effect_value} 点"
        
        elif item.effect_type == "defense":
            # 临时增加防御
            return f"防御力临时提升 {item.effect_value} 点"
        
        elif item.effect_type == "spirit_stone":
            # 增加灵石
            await self.db.execute(
                "UPDATE players SET spirit_stone = spirit_stone + ? WHERE id = ?",
                (item.effect_value, player_id)
            )
            await self.db.commit()
            return f"获得了 {item.effect_value} 灵石"
        
        return "物品已使用"

    # ==================== 物品管理 ====================

    async def get_item_by_id(self, item_id: str) -> Optional[Item]:
        """根据ID获取物品"""
        sql = "SELECT * FROM items WHERE id = ?"
        row = await self.db.fetch_one(sql, (item_id,))
        if row:
            return Item.from_dict(row)
        return None

    async def get_item_by_name(self, name: str) -> Optional[Item]:
        """根据名称获取物品"""
        sql = "SELECT * FROM items WHERE name = ?"
        row = await self.db.fetch_one(sql, (name,))
        if row:
            return Item.from_dict(row)
        return None

    async def get_all_items(self) -> List[Item]:
        """获取所有物品"""
        sql = "SELECT * FROM items ORDER BY id"
        rows = await self.db.fetch_all(sql)
        return [Item.from_dict(row) for row in rows]

    async def create_item(self, item_data: Dict[str, Any]) -> Item:
        """创建物品"""
        item_id = item_data.get("id", str(uuid.uuid4()))
        sql = """
            INSERT INTO items (id, name, description, item_type, rarity, effect_type, effect_value, price, is_usable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(sql, (
            item_id,
            item_data["name"],
            item_data.get("description"),
            item_data["item_type"],
            item_data.get("rarity", "common"),
            item_data.get("effect_type"),
            item_data.get("effect_value", 0),
            item_data.get("price", 0),
            item_data.get("is_usable", 1),
        ))
        await self.db.commit()
        return await self.get_item_by_id(item_id)

    async def update_item(self, item_id: str, **kwargs) -> Optional[Item]:
        """更新物品"""
        allowed_fields = ["name", "description", "item_type", "rarity", "effect_type", "effect_value", "price", "is_usable"]
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return await self.get_item_by_id(item_id)
        
        values.append(item_id)
        sql = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
        await self.db.execute(sql, tuple(values))
        await self.db.commit()
        return await self.get_item_by_id(item_id)

    async def delete_item(self, item_id: str) -> bool:
        """删除物品"""
        sql = "DELETE FROM items WHERE id = ?"
        cursor = await self.db.execute(sql, (item_id,))
        await self.db.commit()
        return cursor.rowcount > 0
