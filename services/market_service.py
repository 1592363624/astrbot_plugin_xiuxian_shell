"""
万宝楼服务
处理市场挂单相关的业务逻辑，包括上架、下架、购买、搜索等
"""

import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from astrbot.api import logger

from ..database import DatabaseManager
from ..utils import bj_now, bj_now_iso

if TYPE_CHECKING:
    from ..config import ConfigManager
    from .inventory_service import InventoryService


class MarketService:
    """万宝楼服务类"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        config_manager: "ConfigManager" = None,
        inventory_service: "InventoryService" = None,
    ):
        """
        初始化万宝楼服务

        Args:
            db_manager: 数据库管理器实例
            config_manager: 配置管理器实例
            inventory_service: 物品服务实例(用于获取物品信息)
        """
        self.db = db_manager
        self.config_manager = config_manager
        self.inventory_service = inventory_service

    async def get_item_by_name(self, item_name: str) -> dict[str, Any] | None:
        """
        根据物品名称查找物品

        Args:
            item_name: 物品名称

        Returns:
            物品信息字典或None
        """
        if self.inventory_service:
            item = await self.inventory_service.get_item_by_name(item_name)
            if item:
                return item.to_dict()
        return None

    async def get_player_inventory_item(
        self, player_id: str, item_id: str
    ) -> dict[str, Any] | None:
        """
        获取玩家储物袋中指定物品

        Args:
            player_id: 玩家ID
            item_id: 物品ID

        Returns:
            储物袋物品记录或None
        """
        return await self.db.fetch_one(
            "SELECT * FROM player_inventory WHERE player_id = ? AND item_id = ?",
            (player_id, item_id),
        )

    async def create_listing(
        self,
        seller_id: str,
        seller_name: str,
        item_id: str,
        item_name: str,
        item_type: str,
        quantity: int,
        price_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        创建挂单

        Args:
            seller_id: 卖家ID
            seller_name: 卖家道号
            item_id: 物品ID
            item_name: 物品名称
            item_type: 物品类型
            quantity: 上架数量
            price_items: 价格物品列表 [{"item_id": xxx, "item_name": xxx, "quantity": xxx}]

        Returns:
            创建结果
        """
        total_price_json = json.dumps(price_items, ensure_ascii=False)

        is_bundled = False
        unit_price_json = None

        for price_item in price_items:
            total_qty = price_item["quantity"]
            if total_qty % quantity != 0:
                is_bundled = True
                break

        if not is_bundled:
            unit_prices = []
            for price_item in price_items:
                unit_qty = price_item["quantity"] // quantity
                unit_prices.append(
                    {
                        "item_id": price_item["item_id"],
                        "item_name": price_item["item_name"],
                        "unit_quantity": unit_qty,
                    }
                )
            unit_price_json = json.dumps(unit_prices, ensure_ascii=False)

        listing_id = str(uuid.uuid4())[:8].upper()

        sql = """
            INSERT INTO market_listings (
                id, seller_id, seller_name, item_id, item_name, item_type,
                quantity, remaining_quantity, total_price, is_bundled, unit_price, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """

        await self.db.execute(
            sql,
            (
                listing_id,
                seller_id,
                seller_name,
                item_id,
                item_name,
                item_type,
                quantity,
                quantity,
                total_price_json,
                1 if is_bundled else 0,
                unit_price_json,
            ),
        )
        await self.db.commit()

        return {
            "success": True,
            "listing_id": listing_id,
            "item_name": item_name,
            "quantity": quantity,
            "is_bundled": is_bundled,
            "price_items": price_items,
        }

    async def get_listing_by_id(self, listing_id: str) -> dict[str, Any] | None:
        """
        根据挂单ID获取挂单信息

        Args:
            listing_id: 挂单ID

        Returns:
            挂单信息或None
        """
        return await self.db.fetch_one(
            "SELECT * FROM market_listings WHERE id = ?",
            (listing_id,),
        )

    async def get_market_listings(
        self,
        page: int = 1,
        page_size: int = 10,
        item_name: str = None,
        item_type: str = None,
        seller_id: str = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取市场挂单列表

        Args:
            page: 页码(从1开始)
            page_size: 每页数量
            item_name: 物品名称过滤(模糊匹配)
            item_type: 物品类型过滤
            seller_id: 卖家ID过滤

        Returns:
            (挂单列表, 总数)
        """
        conditions = ["status = 'active'"]
        params: list[Any] = []

        if item_name:
            conditions.append("item_name LIKE ?")
            params.append(f"%{item_name}%")

        if item_type:
            conditions.append("item_type = ?")
            params.append(item_type)

        if seller_id:
            conditions.append("seller_id = ?")
            params.append(seller_id)

        where_clause = " AND ".join(conditions)

        count_sql = f"SELECT COUNT(*) as total FROM market_listings WHERE {where_clause}"
        count_result = await self.db.fetch_one(count_sql, tuple(params))
        total = count_result["total"] if count_result else 0

        offset = (page - 1) * page_size
        select_sql = f"""
            SELECT * FROM market_listings
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        listings = await self.db.fetch_all(select_sql, tuple(params))

        return listings, total

    async def purchase(
        self,
        buyer_id: str,
        buyer_name: str,
        listing_id: str,
        quantity: int = None,
    ) -> dict[str, Any]:
        """
        购买挂单商品

        Args:
            buyer_id: 买家ID
            buyer_name: 买家道号
            listing_id: 挂单ID
            quantity: 购买数量(None表示全部)

        Returns:
            购买结果
        """
        listing = await self.get_listing_by_id(listing_id)
        if not listing:
            return {"success": False, "message": "挂单不存在"}

        if listing["status"] != "active":
            return {"success": False, "message": "挂单已结束"}

        if listing["seller_id"] == buyer_id:
            return {"success": False, "message": "不能购买自己的商品"}

        remaining = listing["remaining_quantity"]
        is_bundled = bool(listing["is_bundled"])

        if is_bundled:
            purchase_qty = listing["quantity"]
        else:
            purchase_qty = quantity if quantity else remaining

        if purchase_qty > remaining:
            return {"success": False, "message": f"库存不足，当前剩余{remaining}件"}

        if is_bundled and quantity is not None and quantity != listing["quantity"]:
            return {
                "success": False,
                "message": "捆绑商品必须一次性购买全部",
            }

        price_items = json.loads(listing["total_price"])

        for price_item in price_items:
            price_item_id = price_item["item_id"]
            price_item_name = price_item["item_name"]
            total_price_qty = price_item["quantity"]

            price_qty_per_unit = total_price_qty // listing["quantity"]
            required_qty = price_qty_per_unit * purchase_qty

            if price_item_id == "spirit_stone":
                buyer = await self.db.fetch_one(
                    "SELECT spirit_stone FROM players WHERE id = ?",
                    (buyer_id,),
                )
                if not buyer or buyer["spirit_stone"] < required_qty:
                    return {
                        "success": False,
                        "message": f"灵石不足，需要{required_qty}灵石，你只有{buyer['spirit_stone'] if buyer else 0}灵石",
                    }
            else:
                inv_item = await self.get_player_inventory_item(
                    buyer_id, price_item_id
                )
                if not inv_item or inv_item["quantity"] < required_qty:
                    return {
                        "success": False,
                        "message": f"【{price_item_name}】不足，需要{required_qty}个，你只有{inv_item['quantity'] if inv_item else 0}个",
                    }

        for price_item in price_items:
            price_item_id = price_item["item_id"]
            total_price_qty = price_item["quantity"]
            price_qty_per_unit = total_price_qty // listing["quantity"]
            deduct_qty = price_qty_per_unit * purchase_qty

            if price_item_id == "spirit_stone":
                await self.db.execute(
                    "UPDATE players SET spirit_stone = spirit_stone - ? WHERE id = ?",
                    (deduct_qty, buyer_id),
                )
                await self.db.execute(
                    "UPDATE players SET spirit_stone = spirit_stone + ? WHERE id = ?",
                    (deduct_qty, listing["seller_id"]),
                )
            else:
                buyer_inv = await self.get_player_inventory_item(
                    buyer_id, price_item_id
                )
                await self.db.execute(
                    "UPDATE player_inventory SET quantity = quantity - ? WHERE id = ?",
                    (deduct_qty, buyer_inv["id"]),
                )

                seller_inv = await self.get_player_inventory_item(
                    listing["seller_id"], price_item_id
                )
                if seller_inv:
                    await self.db.execute(
                        "UPDATE player_inventory SET quantity = quantity + ? WHERE id = ?",
                        (deduct_qty, seller_inv["id"]),
                    )
                else:
                    new_inv_id = str(uuid.uuid4())
                    await self.db.execute(
                        "INSERT INTO player_inventory (id, player_id, item_id, quantity) VALUES (?, ?, ?, ?)",
                        (new_inv_id, listing["seller_id"], price_item_id, deduct_qty),
                    )

        new_remaining = remaining - purchase_qty
        if new_remaining == 0:
            await self.db.execute(
                "UPDATE market_listings SET remaining_quantity = ?, status = 'completed', updated_at = ? WHERE id = ?",
                (new_remaining, bj_now_iso(), listing_id),
            )
        else:
            await self.db.execute(
                "UPDATE market_listings SET remaining_quantity = ?, updated_at = ? WHERE id = ?",
                (new_remaining, bj_now_iso(), listing_id),
            )

        item_id = listing["item_id"]
        buyer_inv = await self.get_player_inventory_item(buyer_id, item_id)
        if buyer_inv:
            await self.db.execute(
                "UPDATE player_inventory SET quantity = quantity + ? WHERE id = ?",
                (purchase_qty, buyer_inv["id"]),
            )
        else:
            new_inv_id = str(uuid.uuid4())
            await self.db.execute(
                "INSERT INTO player_inventory (id, player_id, item_id, quantity) VALUES (?, ?, ?, ?)",
                (new_inv_id, buyer_id, item_id, purchase_qty),
            )

        await self.db.commit()

        return {
            "success": True,
            "message": f"购买成功！获得【{listing['item_name']}】x{purchase_qty}",
            "item_name": listing["item_name"],
            "quantity": purchase_qty,
            "remaining": new_remaining,
        }

    async def cancel_listing(self, seller_id: str, listing_id: str) -> dict[str, Any]:
        """
        取消挂单(下架)

        Args:
            seller_id: 卖家ID
            listing_id: 挂单ID

        Returns:
            操作结果
        """
        listing = await self.get_listing_by_id(listing_id)
        if not listing:
            return {"success": False, "message": "挂单不存在"}

        if listing["seller_id"] != seller_id:
            return {"success": False, "message": "只能下架自己的商品"}

        if listing["status"] != "active":
            return {"success": False, "message": "挂单已结束，无法下架"}

        remaining = listing["remaining_quantity"]
        if remaining > 0:
            item_id = listing["item_id"]
            seller_inv = await self.get_player_inventory_item(seller_id, item_id)
            if seller_inv:
                await self.db.execute(
                    "UPDATE player_inventory SET quantity = quantity + ? WHERE id = ?",
                    (remaining, seller_inv["id"]),
                )
            else:
                new_inv_id = str(uuid.uuid4())
                await self.db.execute(
                    "INSERT INTO player_inventory (id, player_id, item_id, quantity) VALUES (?, ?, ?, ?)",
                    (new_inv_id, seller_id, item_id, remaining),
                )

        await self.db.execute(
            "UPDATE market_listings SET status = 'cancelled', remaining_quantity = 0, updated_at = ? WHERE id = ?",
            (bj_now_iso(), listing_id),
        )
        await self.db.commit()

        return {
            "success": True,
            "message": f"下架成功！{'商品已全部退回储物袋' if remaining > 0 else '商品已售完无剩余'}",
        }

    async def get_seller_listings(self, seller_id: str) -> list[dict[str, Any]]:
        """
        获取卖家的所有挂单

        Args:
            seller_id: 卖家ID

        Returns:
            挂单列表
        """
        return await self.db.fetch_all(
            "SELECT * FROM market_listings WHERE seller_id = ? ORDER BY created_at DESC",
            (seller_id,),
        )
