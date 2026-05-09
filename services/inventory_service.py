"""
背包服务
处理物品和背包相关的业务逻辑，包括丹药服用和丹毒系统
"""

import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from astrbot.api import logger

from ..database import DatabaseManager
from ..models import Item

if TYPE_CHECKING:
    from ..config import ConfigManager


class InventoryService:
    """背包服务类"""

    def __init__(
        self, db_manager: DatabaseManager, config_manager: "ConfigManager" = None
    ):
        """
        初始化储物袋服务

        Args:
            db_manager: 数据库管理器实例
            config_manager: 配置管理器实例
        """
        self.db = db_manager
        self.config_manager = config_manager

    def _get_pill_config(self) -> dict[str, Any]:
        """获取丹药配置"""
        if self.config_manager:
            return self.config_manager.get("pill", {})
        return {}

    async def get_player_inventory(self, player_id: str) -> list[dict[str, Any]]:
        """
        获取玩家储物袋

        Args:
            player_id: 玩家ID

        Returns:
            List[Dict[str, Any]]: 储物袋物品列表
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

    async def add_item(
        self, player_id: str, item_id: str, quantity: int = 1
    ) -> dict[str, Any]:
        """
        添加物品到储物袋

        Args:
            player_id: 玩家ID
            item_id: 物品ID
            quantity: 数量

        Returns:
            Dict[str, Any]: 操作结果
        """
        item = await self.get_item_by_id(item_id)
        if not item:
            raise ValueError("物品不存在")

        existing = await self.db.fetch_one(
            "SELECT * FROM player_inventory WHERE player_id = ? AND item_id = ?",
            (player_id, item_id),
        )

        if existing:
            await self.db.execute(
                "UPDATE player_inventory SET quantity = quantity + ? WHERE id = ?",
                (quantity, existing["id"]),
            )
        else:
            inventory_id = str(uuid.uuid4())
            await self.db.execute(
                "INSERT INTO player_inventory (id, player_id, item_id, quantity) VALUES (?, ?, ?, ?)",
                (inventory_id, player_id, item_id, quantity),
            )

        await self.db.commit()

        return {
            "success": True,
            "item_name": item.name,
            "quantity": quantity,
            "message": f"获得 {quantity} 个【{item.name}】",
        }

    async def remove_item(
        self, player_id: str, item_id: str, quantity: int = 1
    ) -> dict[str, Any]:
        """
        从储物袋移除物品

        Args:
            player_id: 玩家ID
            item_id: 物品ID
            quantity: 数量

        Returns:
            Dict[str, Any]: 操作结果
        """
        existing = await self.db.fetch_one(
            "SELECT * FROM player_inventory WHERE player_id = ? AND item_id = ?",
            (player_id, item_id),
        )

        if not existing:
            raise ValueError("物品不存在于背包中")

        if existing["quantity"] < quantity:
            raise ValueError("物品数量不足")

        if existing["quantity"] == quantity:
            await self.db.execute(
                "DELETE FROM player_inventory WHERE id = ?", (existing["id"],)
            )
        else:
            await self.db.execute(
                "UPDATE player_inventory SET quantity = quantity - ? WHERE id = ?",
                (quantity, existing["id"]),
            )

        await self.db.commit()

        item = await self.get_item_by_id(item_id)
        return {
            "success": True,
            "item_name": item.name if item else "未知物品",
            "quantity": quantity,
            "message": f"使用了 {quantity} 个【{item.name if item else '未知物品'}】",
        }

    async def use_item(self, player_id: str, item_id: str) -> dict[str, Any]:
        """
        使用物品

        Args:
            player_id: 玩家ID
            item_id: 物品ID

        Returns:
            Dict[str, Any]: 使用结果
        """
        item = await self.get_item_by_id(item_id)
        if not item:
            raise ValueError("物品不存在")

        if not item.is_usable:
            raise ValueError("该物品不可使用")

        inventory_item = await self.db.fetch_one(
            "SELECT * FROM player_inventory WHERE player_id = ? AND item_id = ?",
            (player_id, item_id),
        )

        if not inventory_item or inventory_item["quantity"] <= 0:
            raise ValueError("你没有这个物品")

        effect_message = await self._apply_item_effect(player_id, item)

        await self.remove_item(player_id, item_id, 1)

        return {
            "success": True,
            "item_name": item.name,
            "effect_message": effect_message,
            "message": f"使用了【{item.name}】，{effect_message}",
        }

    # ==================== 服用丹药 ====================

    async def use_pill(
        self, player_id: str, item_name: str, quantity: int = 1
    ) -> dict[str, Any]:
        """
        服用丹药
        支持按名称服用，含境界壁垒检查和丹毒系统

        Args:
            player_id: 玩家ID
            item_name: 丹药名称
            quantity: 服用数量

        Returns:
            Dict[str, Any]: 服用结果
        """
        if quantity < 1:
            raise ValueError("服用数量必须大于0")

        item = await self.get_item_by_name(item_name)
        if not item:
            raise ValueError(f"未找到名为【{item_name}】的物品")

        if item.item_type != "consumable":
            raise ValueError(f"【{item.name}】不是丹药，无法服用")

        if not item.is_usable:
            raise ValueError(f"【{item.name}】不可服用")

        inventory_item = await self.db.fetch_one(
            "SELECT * FROM player_inventory WHERE player_id = ? AND item_id = ?",
            (player_id, item.id),
        )

        if not inventory_item or inventory_item["quantity"] < quantity:
            owned = inventory_item["quantity"] if inventory_item else 0
            raise ValueError(
                f"【{item.name}】数量不足，你拥有{owned}个，尝试服用{quantity}个"
            )

        realm_check = await self._check_pill_realm_requirement(player_id, item)
        if not realm_check["passed"]:
            return {
                "success": False,
                "message": f"【境界壁垒】你的境界为{realm_check['player_realm']}，无法承受【{item.name}】的药力，需要达到{realm_check['required_realm']}方可服用。",
            }

        await self.remove_item(player_id, item.id, quantity)

        item.effect_value * quantity
        pill_cfg = self._get_pill_config()
        is_detox = item.id == pill_cfg.get("detox_item_id", "item_detox")

        if is_detox:
            detox_result = await self._clear_toxicity(player_id)
            message_lines = [
                f"你服下了{quantity}枚【{item.name}】。",
                detox_result["message"],
            ]
            return {
                "success": True,
                "item_name": item.name,
                "quantity": quantity,
                "is_detox": True,
                "message": "\n".join(message_lines),
            }

        effect_messages = []
        for _ in range(quantity):
            effect_msg = await self._apply_item_effect(player_id, item)
            effect_messages.append(effect_msg)

        toxicity_result = await self._apply_pill_toxicity(player_id, item, quantity)

        message_lines = [f"你服下了{quantity}枚【{item.name}】。"]
        for msg in effect_messages:
            message_lines.append(msg)

        if toxicity_result["toxicity_added"] > 0:
            message_lines.append(
                f"【丹毒警告】连续服用同类丹药，体内丹毒累积了{toxicity_result['toxicity_added']}点！"
                f"当前丹毒总量：{toxicity_result['total_toxicity']}点。"
                f"丹毒会影响闭关收益和炼制成功率，可使用【清灵丹】清除。"
            )

        logger.info(
            f"玩家 {player_id} 服用 {item.name} x{quantity}, "
            f"丹毒: +{toxicity_result['toxicity_added']}, 总计: {toxicity_result['total_toxicity']}"
        )

        return {
            "success": True,
            "item_name": item.name,
            "quantity": quantity,
            "effect_messages": effect_messages,
            "toxicity": toxicity_result,
            "message": "\n".join(message_lines),
        }

    async def _check_pill_realm_requirement(
        self, player_id: str, item: Item
    ) -> dict[str, Any]:
        """
        检查丹药的境界壁垒

        Args:
            player_id: 玩家ID
            item: 物品对象

        Returns:
            Dict[str, Any]: 检查结果
        """
        if not item.realm_requirement:
            return {"passed": True}

        player = await self.db.fetch_one(
            "SELECT p.*, r.level as realm_level, r.name as realm_name FROM players p JOIN realms r ON p.realm_id = r.id WHERE p.id = ?",
            (player_id,),
        )
        if not player:
            return {"passed": False, "player_realm": "未知", "required_realm": "未知"}

        required_realm = await self.db.fetch_one(
            "SELECT level, name FROM realms WHERE id = ?", (item.realm_requirement,)
        )
        if not required_realm:
            return {"passed": True}

        if player["realm_level"] < required_realm["level"]:
            return {
                "passed": False,
                "player_realm": player["realm_name"],
                "required_realm": required_realm["name"],
            }

        return {"passed": True}

    async def _apply_pill_toxicity(
        self, player_id: str, item: Item, quantity: int
    ) -> dict[str, Any]:
        """
        应用丹毒效果
        24小时内连续服用同类丹药会积累丹毒

        Args:
            player_id: 玩家ID
            item: 丹药物品对象
            quantity: 服用数量

        Returns:
            Dict[str, Any]: 丹毒结果
        """
        pill_cfg = self._get_pill_config()
        duration_hours = pill_cfg.get("toxicity_duration_hours", 24)
        same_pill_toxicity = pill_cfg.get("same_pill_toxicity", 1)

        now = datetime.utcnow()
        expires_at = now + timedelta(hours=duration_hours)

        existing_active = await self.db.fetch_one(
            "SELECT * FROM pill_toxicity_records WHERE player_id = ? AND item_id = ? AND expires_at > ?",
            (player_id, item.id, now.isoformat()),
        )

        toxicity_added = 0
        if existing_active:
            toxicity_added = same_pill_toxicity * quantity
            await self.db.execute(
                "UPDATE pill_toxicity_records SET toxicity_value = toxicity_value + ?, expires_at = ? WHERE id = ?",
                (toxicity_added, expires_at.isoformat(), existing_active["id"]),
            )
        else:
            toxicity_added = 0
            record_id = str(uuid.uuid4())
            await self.db.execute(
                """INSERT INTO pill_toxicity_records
                (id, player_id, item_id, item_name, toxicity_value, taken_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    record_id,
                    player_id,
                    item.id,
                    item.name,
                    0,
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )

        await self.db.commit()

        total_toxicity = await self._get_total_toxicity(player_id)

        return {
            "toxicity_added": toxicity_added,
            "total_toxicity": total_toxicity,
        }

    async def _get_total_toxicity(self, player_id: str) -> int:
        """
        获取玩家当前丹毒总量

        Args:
            player_id: 玩家ID

        Returns:
            int: 丹毒总量
        """
        now = datetime.utcnow()
        await self._cleanup_expired_toxicity(player_id)

        result = await self.db.fetch_one(
            "SELECT COALESCE(SUM(toxicity_value), 0) as total FROM pill_toxicity_records WHERE player_id = ? AND expires_at > ?",
            (player_id, now.isoformat()),
        )
        return result["total"] if result else 0

    async def _cleanup_expired_toxicity(self, player_id: str):
        """
        清理过期的丹毒记录

        Args:
            player_id: 玩家ID
        """
        now = datetime.utcnow()
        await self.db.execute(
            "DELETE FROM pill_toxicity_records WHERE player_id = ? AND expires_at <= ?",
            (player_id, now.isoformat()),
        )
        await self.db.commit()

    async def _clear_toxicity(self, player_id: str) -> dict[str, Any]:
        """
        清除玩家所有丹毒（使用清灵丹）

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 清除结果
        """
        total = await self._get_total_toxicity(player_id)

        await self.db.execute(
            "DELETE FROM pill_toxicity_records WHERE player_id = ?", (player_id,)
        )
        await self.db.commit()

        if total > 0:
            return {
                "success": True,
                "cleared_toxicity": total,
                "message": f"清灵丹入腹，体内{total}点丹毒已被尽数化解，经脉重新通畅！",
            }
        else:
            return {
                "success": True,
                "cleared_toxicity": 0,
                "message": "清灵丹入腹，你体内并无丹毒积聚，药力温和地滋养了经脉。",
            }

    async def get_toxicity_status(self, player_id: str) -> dict[str, Any]:
        """
        获取玩家丹毒状态

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 丹毒状态信息
        """
        await self._cleanup_expired_toxicity(player_id)

        now = datetime.utcnow()
        records = await self.db.fetch_all(
            "SELECT * FROM pill_toxicity_records WHERE player_id = ? AND expires_at > ? ORDER BY taken_at DESC",
            (player_id, now.isoformat()),
        )

        total_toxicity = sum(r["toxicity_value"] for r in records)

        return {
            "total_toxicity": total_toxicity,
            "active_records": [dict(r) for r in records],
            "has_toxicity": total_toxicity > 0,
        }

    async def _apply_item_effect(self, player_id: str, item: Item) -> str:
        if item.effect_type == "heal":
            player = await self.db.fetch_one(
                "SELECT p.*, r.level as realm_level FROM players p JOIN realms r ON p.realm_id = r.id WHERE p.id = ?",
                (player_id,),
            )
            if player:
                from ..utils.attributes import calc_battle_attrs

                battle_attrs = calc_battle_attrs(
                    level=player["realm_level"],
                    bone=player["bone"],
                    spirit=player["spirit"],
                    intel=player["intel"],
                    str_=player["str"],
                    percep=player["percep"],
                    luck=player["luck"],
                )
                max_health = battle_attrs["max_health"]
            else:
                max_health = 100
            await self.db.execute(
                "UPDATE players SET health = MIN(?, health + ?) WHERE id = ?",
                (max_health, item.effect_value, player_id),
            )
            await self.db.commit()
            return f"恢复了 {item.effect_value} 点生命值"

        elif item.effect_type == "exp":
            await self.db.execute(
                "UPDATE players SET experience = experience + ? WHERE id = ?",
                (item.effect_value, player_id),
            )
            await self.db.commit()
            return f"增加了 {item.effect_value} 点修为"

        elif item.effect_type == "attack":
            return f"攻击力临时提升 {item.effect_value} 点"

        elif item.effect_type == "defense":
            return f"防御力临时提升 {item.effect_value} 点"

        elif item.effect_type == "spirit_stone":
            await self.db.execute(
                "UPDATE players SET spirit_stone = spirit_stone + ? WHERE id = ?",
                (item.effect_value, player_id),
            )
            await self.db.commit()
            return f"获得了 {item.effect_value} 灵石"

        elif item.effect_type == "detox":
            return "丹毒已被清除"

        return "物品已使用"

    # ==================== 物品管理 ====================

    async def get_item_by_id(self, item_id: str) -> Item | None:
        """根据ID获取物品"""
        sql = "SELECT * FROM items WHERE id = ?"
        row = await self.db.fetch_one(sql, (item_id,))
        if row:
            return Item.from_dict(row)
        return None

    async def get_item_by_name(self, name: str) -> Item | None:
        """根据名称获取物品"""
        sql = "SELECT * FROM items WHERE name = ?"
        row = await self.db.fetch_one(sql, (name,))
        if row:
            return Item.from_dict(row)
        return None

    async def get_all_items(self) -> list[Item]:
        """获取所有物品"""
        sql = "SELECT * FROM items ORDER BY id"
        rows = await self.db.fetch_all(sql)
        return [Item.from_dict(row) for row in rows]

    async def create_item(self, item_data: dict[str, Any]) -> Item:
        """创建物品"""
        item_id = item_data.get("id", str(uuid.uuid4()))
        sql = """
            INSERT INTO items (id, name, description, item_type, rarity, effect_type, effect_value, price, is_usable, realm_requirement)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(
            sql,
            (
                item_id,
                item_data["name"],
                item_data.get("description"),
                item_data["item_type"],
                item_data.get("rarity", "common"),
                item_data.get("effect_type"),
                item_data.get("effect_value", 0),
                item_data.get("price", 0),
                item_data.get("is_usable", 1),
                item_data.get("realm_requirement"),
            ),
        )
        await self.db.commit()
        return await self.get_item_by_id(item_id)

    async def update_item(self, item_id: str, **kwargs) -> Item | None:
        """更新物品"""
        allowed_fields = [
            "name",
            "description",
            "item_type",
            "rarity",
            "effect_type",
            "effect_value",
            "price",
            "is_usable",
            "realm_requirement",
        ]
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
