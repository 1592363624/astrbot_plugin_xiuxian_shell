"""
物品数据模型
定义游戏物品的数据结构
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Item:
    """物品数据模型"""

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
