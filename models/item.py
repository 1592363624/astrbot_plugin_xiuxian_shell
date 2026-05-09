"""
物品数据模型
定义游戏物品的数据结构，支持高扩展性效果系统
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Item:
    """
    物品数据模型

    支持新效果系统的扩展字段:
    - stackable: 是否可堆叠（默认True，所有物品无限堆叠）
    - use_type: 使用类型（active主动/passive被动）
    - use_conditions: 使用条件列表
    - consume_num: 使用时消耗数量
    - effect_ids: 关联的效果ID列表
    - prompt_key_success: 使用成功提示文案键名
    """

    id: str
    name: str
    description: str
    item_type: str  # consumable, equipment, material, currency
    rarity: str = "common"  # common, uncommon, rare, epic, legendary
    effect_type: str | None = None  # heal, exp, attack, defense, spirit_stone
    effect_value: int = 0
    price: int = 0
    is_usable: bool = True
    realm_requirement: str | None = None
    created_at: datetime | None = None
    # 新效果系统扩展字段
    stackable: bool = True
    """是否可堆叠，所有物品默认无限堆叠"""

    use_type: str = "active"
    """使用类型: active(主动使用) / passive(被动触发)"""

    use_conditions: list[dict[str, Any]] = field(default_factory=list)
    """使用条件列表，每个条件包含 condition_type/condition_value/prompt_key"""

    consume_num: int = 1
    """使用时消耗的本物品数量"""

    effect_ids: list[str] = field(default_factory=list)
    """关联的效果ID列表，按顺序触发"""

    prompt_key_success: str | None = None
    """使用成功时的提示文案键名"""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "item_type": self.item_type,
            "rarity": self.rarity,
            "effect_type": self.effect_type,
            "effect_value": self.effect_value,
            "price": self.price,
            "is_usable": self.is_usable,
            "realm_requirement": self.realm_requirement,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "stackable": self.stackable,
            "use_type": self.use_type,
            "use_conditions": self.use_conditions,
            "consume_num": self.consume_num,
            "effect_ids": self.effect_ids,
            "prompt_key_success": self.prompt_key_success,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        """从字典创建实例"""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            item_type=data.get("item_type"),
            rarity=data.get("rarity", "common"),
            effect_type=data.get("effect_type"),
            effect_value=data.get("effect_value", 0),
            price=data.get("price", 0),
            is_usable=bool(data.get("is_usable", 1)),
            realm_requirement=data.get("realm_requirement"),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            stackable=data.get("stackable", True),
            use_type=data.get("use_type", "active"),
            use_conditions=data.get("use_conditions", []),
            consume_num=data.get("consume_num", 1),
            effect_ids=data.get("effect_ids", []),
            prompt_key_success=data.get("prompt_key_success"),
        )


@dataclass
class InventoryItem:
    """储物袋物品数据模型"""

    id: str
    player_id: str
    item_id: str
    quantity: int = 1
    equipped: bool = False
    created_at: datetime | None = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "player_id": self.player_id,
            "item_id": self.item_id,
            "quantity": self.quantity,
            "equipped": self.equipped,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
