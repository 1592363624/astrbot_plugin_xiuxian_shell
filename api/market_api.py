"""
万宝楼API
提供万宝楼市场的接口，供命令层调用
"""

import json
import re

from ..services import MarketService, PlayerService


class MarketAPI:
    """万宝楼API类"""

    VALID_ITEM_TYPES = ["丹药", "法宝", "材料", "图纸", "种子"]

    def __init__(self, market_service: MarketService, player_service: PlayerService):
        """
        初始化万宝楼API

        Args:
            market_service: 万宝楼服务实例
            player_service: 玩家服务实例
        """
        self.market_service = market_service
        self.player_service = player_service

    async def create_listing(self, user_id: str, message: str) -> str:
        """
        处理上架指令

        格式: 上架 <物品名>*<数量> 换 <所需物品1>*<总数1> <所需物品2>*<总数2> ...
        示例: 上架 凝血散 100 换 灵石 500
              上架 增元丹 3 换 一阶妖丹 1 灵石 * 50
              上架 玄铁剑 换 灵石 * 50

        Args:
            user_id: 用户ID
            message: 指令消息

        Returns:
            str: 操作结果文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        player_id = player_dict["id"]
        username = player_dict["username"]

        if not message.startswith("上架"):
            return "指令格式错误，请使用：上架 <物品名>*<数量> 换 <所需物品1>*<数量1> ..."

        listing_str = message[2:].strip()
        if " 换 " not in listing_str:
            return "指令格式错误，请使用：上架 <物品名>*<数量> 换 <所需物品1>*<数量1> ..."

        parts = listing_str.split(" 换 ", 1)
        if len(parts) != 2:
            return "指令格式错误，请使用：上架 <物品名>*<数量> 换 <所需物品1>*<数量1> ..."

        item_part = parts[0].strip()
        price_part = parts[1].strip()

        item_pattern = r"^(.+?)(?:\s*\*\s*(\d+))?$"
        item_match = re.match(item_pattern, item_part)
        if not item_match:
            return "物品名称格式错误"

        item_name = item_match.group(1).strip()
        quantity = int(item_match.group(2)) if item_match.group(2) else 1

        item = await self.market_service.get_item_by_name(item_name)
        if not item:
            return f"物品【{item_name}】不存在"

        inv_item = await self.market_service.get_player_inventory_item(player_id, item["id"])
        if not inv_item or inv_item["quantity"] < quantity:
            owned = inv_item["quantity"] if inv_item else 0
            return f"储物袋中【{item_name}】不足，你只有{owned}个"

        price_items = []
        price_pattern = r"(.+?)\s*\*\s*(\d+)"
        price_matches = re.findall(price_pattern, price_part)

        if not price_matches:
            simple_name = price_part.strip()
            if simple_name == "灵石":
                price_items.append({"item_id": "spirit_stone", "item_name": "灵石", "quantity": 1})
            else:
                price_item = await self.market_service.get_item_by_name(simple_name)
                if not price_item:
                    return f"价格物品【{simple_name}】不存在"
                price_items.append({"item_id": price_item["id"], "item_name": price_item["name"], "quantity": 1})
        else:
            for price_name, price_qty in price_matches:
                price_name = price_name.strip()
                price_qty = int(price_qty)
                if price_name == "灵石":
                    price_items.append({"item_id": "spirit_stone", "item_name": "灵石", "quantity": price_qty})
                else:
                    price_item = await self.market_service.get_item_by_name(price_name)
                    if not price_item:
                        return f"价格物品【{price_name}】不存在"
                    price_items.append({"item_id": price_item["id"], "item_name": price_item["name"], "quantity": price_qty})

        inv_record = await self.market_service.get_player_inventory_item(player_id, item["id"])
        await self.market_service.db.execute(
            "UPDATE player_inventory SET quantity = quantity - ? WHERE id = ?",
            (quantity, inv_record["id"]),
        )
        await self.market_service.db.commit()

        result = await self.market_service.create_listing(
            seller_id=player_id,
            seller_name=username,
            item_id=item["id"],
            item_name=item["name"],
            item_type=item["item_type"],
            quantity=quantity,
            price_items=price_items,
        )

        if result["success"]:
            is_bundled = result["is_bundled"]
            price_desc = " + ".join([f"{p['item_name']}x{p['quantity']}" for p in price_items])
            if is_bundled:
                return (
                    f"【捆绑上架成功】\n"
                    f"你上架了【{item['name']}】x{quantity}\n"
                    f"总价：{price_desc}\n"
                    f"此挂单为捆绑出售，买家需一次性购买全部。"
                )
            else:
                unit_prices = []
                for price_item in price_items:
                    total_qty = price_item["quantity"]
                    unit_qty = total_qty // quantity
                    unit_prices.append(f"{price_item['item_name']}x{unit_qty}")
                unit_price_desc = " + ".join(unit_prices)
                return (
                    f"【上架成功】\n"
                    f"你上架了【{item['name']}】x{quantity}\n"
                    f"单价：{unit_price_desc}\n"
                    f"买家可按数量购买。"
                )
        else:
            return f"上架失败：{result.get('message', '未知错误')}"

    async def browse_market(
        self,
        user_id: str,
        page: int = 1,
        search_keyword: str = None,
        item_type: str = None,
    ) -> str:
        """
        浏览万宝楼市场

        Args:
            user_id: 用户ID
            page: 页码
            search_keyword: 搜索关键词
            item_type: 物品类型筛选

        Returns:
            str: 市场商品列表文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        if item_type and item_type not in self.VALID_ITEM_TYPES:
            return f"物品类型错误，可用类型：{'/'.join(self.VALID_ITEM_TYPES)}"

        listings, total = await self.market_service.get_market_listings(
            page=page,
            page_size=10,
            item_name=search_keyword,
            item_type=item_type,
        )

        if not listings:
            if search_keyword:
                return f"【万宝楼】\n未找到包含「{search_keyword}」的商品"
            if item_type:
                return f"【万宝楼】\n暂无{item_type}类商品"
            return "【万宝楼】\n万宝楼内空空如也，暂无商品上架"

        total_pages = (total + 9) // 10

        lines = [f"【万宝楼】第{page}/{total_pages}页 (共{total}件商品)"]
        lines.append("=" * 40)

        for listing in listings:
            listing_id = listing["id"]
            item_name = listing["item_name"]
            remaining = listing["remaining_quantity"]
            total_qty = listing["quantity"]
            is_bundled = bool(listing["is_bundled"])

            price_items = json.loads(listing["total_price"])
            price_desc = " + ".join(
                [f"{p['item_name']}x{p['quantity']}" for p in price_items]
            )

            lines.append(f"[{listing_id}] {item_name} x{total_qty}")

            if is_bundled:
                lines.append(f"    总价: {price_desc} (捆绑)")
            else:
                unit_prices = []
                for price_item in price_items:
                    unit_qty = price_item["quantity"] // total_qty
                    unit_prices.append(f"{price_item['item_name']}x{unit_qty}")
                unit_price_desc = " + ".join(unit_prices)
                lines.append(f"    单价: {unit_price_desc} | 剩余: {remaining}")

            lines.append("")

        lines.append("=" * 40)
        lines.append("输入「万宝楼」查看首页")
        lines.append("输入「万宝楼 2」查看第2页")
        lines.append("输入「万宝楼 搜索 <物品名>」搜索商品")
        lines.append("输入「万宝楼 筛选 <类型>」筛选类型")

        return "\n".join(lines)

    async def purchase(self, user_id: str, listing_id: str, quantity: int = None) -> str:
        """
        购买商品

        格式: 购买 <挂单ID>*<数量> 或 购买 <挂单ID>

        Args:
            user_id: 用户ID
            listing_id: 挂单ID
            quantity: 购买数量

        Returns:
            str: 购买结果文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        buyer_id = player_dict["id"]
        buyer_name = player_dict["username"]

        result = await self.market_service.purchase(
            buyer_id=buyer_id,
            buyer_name=buyer_name,
            listing_id=listing_id.upper(),
            quantity=quantity,
        )

        return result.get("message", "购买异常")

    async def get_my_stalls(self, user_id: str) -> str:
        """
        查看我的货摊

        Args:
            user_id: 用户ID

        Returns:
            str: 货摊信息文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        player_id = player_dict["id"]
        listings = await self.market_service.get_seller_listings(player_id)

        if not listings:
            return "【我的货摊】\n你暂无正在出售的商品"

        active_listings = [l for l in listings if l["status"] == "active"]
        completed_listings = [l for l in listings if l["status"] == "completed"]

        lines = ["【我的货摊】"]

        if active_listings:
            lines.append(f"正在出售 ({len(active_listings)}件)：")
            for listing in active_listings:
                listing_id = listing["id"]
                item_name = listing["item_name"]
                remaining = listing["remaining_quantity"]
                total_qty = listing["quantity"]
                is_bundled = bool(listing["is_bundled"])

                price_items = json.loads(listing["total_price"])
                price_desc = " + ".join(
                    [f"{p['item_name']}x{p['quantity']}" for p in price_items]
                )

                status_mark = "(捆绑)" if is_bundled else f"剩余{remaining}"
                lines.append(f"[{listing_id}] {item_name} x{total_qty} {status_mark}")
                lines.append(f"    总价: {price_desc}")

        if completed_listings:
            lines.append(f"\n已售罄 ({len(completed_listings)}件)：")
            for listing in completed_listings[:5]:
                lines.append(f"[{listing['id']}] {listing['item_name']} (已售完)")

        lines.append("\n下架商品：下架 <挂单ID>")

        return "\n".join(lines)

    async def cancel_listing(self, user_id: str, listing_id: str) -> str:
        """
        下架商品

        格式: 下架 <挂单ID>

        Args:
            user_id: 用户ID
            listing_id: 挂单ID

        Returns:
            str: 下架结果文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        player_id = player_dict["id"]

        result = await self.market_service.cancel_listing(
            seller_id=player_id,
            listing_id=listing_id.upper(),
        )

        return result.get("message", "下架异常")
