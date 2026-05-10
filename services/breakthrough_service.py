"""
突破服务
处理境界突破条件检查、自动突破、手动渡劫等业务逻辑
"""

import json
import random
from typing import TYPE_CHECKING, Any

from astrbot.api import logger

from ..database import DatabaseManager
from ..utils import bj_now_iso

if TYPE_CHECKING:
    from ..config import ConfigManager
    from .cultivation_service import CultivationService


class BreakthroughService:
    """突破服务类"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        config_manager: "ConfigManager" = None,
        cultivation_service: "CultivationService" = None,
    ):
        """
        初始化突破服务

        Args:
            db_manager: 数据库管理器实例
            config_manager: 配置管理器实例
            cultivation_service: 修炼服务实例(用于获取境界信息)
        """
        self.db = db_manager
        self.config_manager = config_manager
        self.cultivation_service = cultivation_service

    async def get_breakthrough_condition(self, realm_id: str) -> dict[str, Any] | None:
        """
        获取境界突破条件

        Args:
            realm_id: 境界ID

        Returns:
            Optional[Dict[str, Any]]: 突破条件，无则返回None
        """
        row = await self.db.fetch_one(
            "SELECT * FROM realm_breakthrough_conditions WHERE realm_id = ?",
            (realm_id,),
        )
        if not row:
            return None
        result = dict(row)
        if result.get("item_requirements"):
            try:
                result["item_requirements"] = json.loads(result["item_requirements"])
            except json.JSONDecodeError:
                result["item_requirements"] = []
        return result

    async def get_all_breakthrough_conditions(self) -> list[dict[str, Any]]:
        """
        获取所有境界突破条件

        Returns:
            List[Dict[str, Any]]: 突破条件列表
        """
        rows = await self.db.fetch_all(
            "SELECT * FROM realm_breakthrough_conditions ORDER BY realm_id"
        )
        result = []
        for row in rows:
            item = dict(row)
            if item.get("item_requirements"):
                try:
                    item["item_requirements"] = json.loads(item["item_requirements"])
                except json.JSONDecodeError:
                    item["item_requirements"] = []
            result.append(item)
        return result

    async def update_breakthrough_condition(
        self, condition_id: str, **kwargs
    ) -> dict[str, Any] | None:
        """
        更新突破条件（后台管理用）

        Args:
            condition_id: 条件记录ID
            **kwargs: 要更新的字段

        Returns:
            Optional[Dict[str, Any]]: 更新后的条件
        """
        allowed_fields = [
            "realm_id",
            "realm_name",
            "condition_type",
            "item_requirements",
            "description",
        ]
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                if key == "item_requirements" and isinstance(value, list):
                    values.append(json.dumps(value, ensure_ascii=False))
                else:
                    values.append(value)

        if not updates:
            return await self.get_breakthrough_condition_by_id(condition_id)

        values.append(condition_id)
        sql = f"UPDATE realm_breakthrough_conditions SET {', '.join(updates)} WHERE id = ?"
        await self.db.execute(sql, tuple(values))
        await self.db.commit()
        return await self.get_breakthrough_condition_by_id(condition_id)

    async def get_breakthrough_condition_by_id(
        self, condition_id: str
    ) -> dict[str, Any] | None:
        """根据ID获取突破条件"""
        row = await self.db.fetch_one(
            "SELECT * FROM realm_breakthrough_conditions WHERE id = ?",
            (condition_id,),
        )
        if not row:
            return None
        result = dict(row)
        if result.get("item_requirements"):
            try:
                result["item_requirements"] = json.loads(result["item_requirements"])
            except json.JSONDecodeError:
                result["item_requirements"] = []
        return result

    async def check_breakthrough_items(
        self, player_id: str, item_requirements: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        检查玩家是否拥有突破所需物品

        Args:
            player_id: 玩家ID
            item_requirements: 物品需求列表

        Returns:
            Dict[str, Any]: 检查结果
        """
        missing = []
        owned = []

        for req in item_requirements:
            item_id = req["item_id"]
            item_name = req["item_name"]
            required_qty = req["quantity"]

            inventory = await self.db.fetch_one(
                "SELECT quantity FROM player_inventory WHERE player_id = ? AND item_id = ?",
                (player_id, item_id),
            )
            current_qty = inventory["quantity"] if inventory else 0

            if current_qty < required_qty:
                missing.append(
                    {
                        "item_id": item_id,
                        "item_name": item_name,
                        "required": required_qty,
                        "current": current_qty,
                    }
                )
            else:
                owned.append(
                    {
                        "item_id": item_id,
                        "item_name": item_name,
                        "required": required_qty,
                        "current": current_qty,
                    }
                )

        return {
            "can_breakthrough": len(missing) == 0,
            "missing": missing,
            "owned": owned,
        }

    async def consume_breakthrough_items(
        self, player_id: str, item_requirements: list[dict[str, Any]]
    ) -> bool:
        """
        消耗突破所需物品

        Args:
            player_id: 玩家ID
            item_requirements: 物品需求列表

        Returns:
            bool: 是否成功消耗
        """
        for req in item_requirements:
            item_id = req["item_id"]
            required_qty = req["quantity"]

            inventory = await self.db.fetch_one(
                "SELECT id, quantity FROM player_inventory WHERE player_id = ? AND item_id = ?",
                (player_id, item_id),
            )
            if not inventory or inventory["quantity"] < required_qty:
                return False

            new_qty = inventory["quantity"] - required_qty
            if new_qty <= 0:
                await self.db.execute(
                    "DELETE FROM player_inventory WHERE id = ?", (inventory["id"],)
                )
            else:
                await self.db.execute(
                    "UPDATE player_inventory SET quantity = ? WHERE id = ?",
                    (new_qty, inventory["id"]),
                )

        await self.db.commit()
        return True

    async def try_auto_breakthrough(self, player_id: str) -> dict[str, Any] | None:
        """
        尝试自动突破（用于筑基期等自动突破境界）

        当玩家修为达到上限且拥有所需物品时，自动突破。

        Args:
            player_id: 玩家ID

        Returns:
            Optional[Dict[str, Any]]: 突破结果，不满足条件返回None
        """
        player = await self.db.fetch_one(
            "SELECT * FROM players WHERE id = ?",
            (player_id,),
        )
        if not player:
            return None

        player_realm = None
        if self.cultivation_service:
            player_realm = await self.cultivation_service.get_realm_by_id(player["realm_id"])

        current_level = player_realm.level if player_realm and hasattr(player_realm, 'level') else player.get("realm_level", 1)
        current_exp = player["experience"]

        next_realm = None
        next_realm_dict = None
        if self.cultivation_service:
            next_realm = await self.cultivation_service.get_next_realm(current_level)
            if next_realm and hasattr(next_realm, 'to_dict'):
                next_realm_dict = next_realm.to_dict()
            elif next_realm:
                next_realm_dict = next_realm

        if not next_realm or not next_realm_dict:
            return None

        # 检查修为是否达到要求
        if current_exp < next_realm_dict["experience_required"]:
            return None

        # 查询是否有突破条件
        condition = await self.get_breakthrough_condition(next_realm_dict["id"])
        if not condition:
            # 无条件限制，直接突破
            return await self._perform_breakthrough(player_id, player, next_realm_dict)

        # 根据突破条件类型处理
        if condition["condition_type"] == "manual":
            # 手动突破类型：不自动突破，返回标记（提示已由 check_breakthrough_prompt 统一生成）
            return {
                "success": False,
                "can_breakthrough": False,
                "is_manual_condition": True,
            }

        # 检查物品需求
        item_requirements = condition.get("item_requirements", [])
        if item_requirements:
            item_check = await self.check_breakthrough_items(
                player_id, item_requirements
            )
            if not item_check["can_breakthrough"]:
                # 物品不足，静默返回失败（提示已由 check_breakthrough_prompt 统一生成，每日一次）
                return {
                    "success": False,
                    "can_breakthrough": False,
                }

            # 消耗物品并突破
            await self.consume_breakthrough_items(player_id, item_requirements)

        return await self._perform_breakthrough(
            player_id, player, next_realm_dict, condition
        )

    async def try_manual_breakthrough(
        self, player_id: str, target_realm_id: str | None = None
    ) -> dict[str, Any]:
        """
        尝试手动突破（用于结丹之劫、元婴之劫等）

        Args:
            player_id: 玩家ID
            target_realm_id: 目标境界ID（可选，默认检查下一境界）

        Returns:
            Dict[str, Any]: 突破结果
        """
        player = await self.db.fetch_one(
            "SELECT * FROM players WHERE id = ?",
            (player_id,),
        )
        if not player:
            raise ValueError("玩家不存在")

        player_realm = None
        if self.cultivation_service:
            player_realm = await self.cultivation_service.get_realm_by_id(player["realm_id"])

        current_level = player_realm.level if player_realm and hasattr(player_realm, 'level') else player.get("realm_level", 1)
        current_exp = player["experience"]

        # 确定目标境界
        next_realm = None
        next_realm_dict = None
        if target_realm_id:
            if self.cultivation_service:
                next_realm = await self.cultivation_service.get_realm_by_id(target_realm_id)
                if next_realm and hasattr(next_realm, 'to_dict'):
                    next_realm_dict = next_realm.to_dict()
                elif next_realm:
                    next_realm_dict = next_realm
        else:
            if self.cultivation_service:
                next_realm = await self.cultivation_service.get_next_realm(current_level)
                if next_realm and hasattr(next_realm, 'to_dict'):
                    next_realm_dict = next_realm.to_dict()
                elif next_realm:
                    next_realm_dict = next_realm

        if not next_realm or not next_realm_dict:
            return {
                "success": False,
                "message": "你已达到最高境界，无法继续突破",
            }

        # 检查修为是否达到要求
        if current_exp < next_realm_dict["experience_required"]:
            return {
                "success": False,
                "message": f"修为不足，需要 {next_realm_dict['experience_required']} 点修为，当前仅有 {current_exp} 点",
            }

        # 查询突破条件
        condition = await self.get_breakthrough_condition(next_realm_dict["id"])
        if condition and condition["condition_type"] == "manual":
            # 手动突破需要检查物品
            item_requirements = condition.get("item_requirements", [])
            if item_requirements:
                item_check = await self.check_breakthrough_items(
                    player_id, item_requirements
                )
                if not item_check["can_breakthrough"]:
                    missing_names = [
                        f"【{m['item_name']}】x{m['required']}"
                        for m in item_check["missing"]
                    ]
                    return {
                        "success": False,
                        "message": (
                            f"【{next_realm_dict['name']}之劫】"
                            f"集齐以下至宝方可渡劫：{', '.join(missing_names)}"
                        ),
                    }

                # 消耗物品
                await self.consume_breakthrough_items(player_id, item_requirements)

        # 执行突破（带概率）
        return await self._perform_breakthrough(
            player_id, player, next_realm_dict, condition, is_manual=True
        )

    async def _perform_breakthrough(
        self,
        player_id: str,
        player: dict[str, Any],
        next_realm: dict[str, Any],
        condition: dict[str, Any] | None = None,
        is_manual: bool = False,
    ) -> dict[str, Any]:
        """
        执行突破操作

        Args:
            player_id: 玩家ID
            player: 玩家数据
            next_realm: 目标境界数据
            condition: 突破条件（可选）
            is_manual: 是否为手动突破（手动突破有概率失败）

        Returns:
            Dict[str, Any]: 突破结果
        """
        current_realm_name = "未知"
        if self.cultivation_service:
            current_realm = await self.cultivation_service.get_realm_by_id(player["realm_id"])
            if current_realm:
                current_realm_name = current_realm.name
        next_realm_name = next_realm["name"]

        # 自动突破100%成功，手动突破按概率
        if is_manual:
            success_rate = next_realm.get("breakthrough_probability", 50) / 100.0
            if random.random() >= success_rate:
                # 突破失败：损失50%修为和突破材料
                current_exp = player["experience"]
                exp_loss = int(current_exp * 0.5)

                # 扣除修为，通过统一入口处理
                if self.cultivation_service:
                    await self.cultivation_service.add_experience(player_id, -exp_loss)
                else:
                    await self.db.execute(
                        "UPDATE players SET experience = MAX(0, experience - ?), updated_at = ? WHERE id = ?",
                        (exp_loss, bj_now_iso(), player_id),
                    )

                # 扣除突破材料（如果条件中有物品需求）
                lost_items_msg = ""
                if condition:
                    item_requirements = condition.get("item_requirements", [])
                    if item_requirements:
                        # 消耗一半的材料（向上取整）
                        for req in item_requirements:
                            item_id = req["item_id"]
                            required_qty = req["quantity"]
                            loss_qty = max(1, required_qty // 2)

                            inventory = await self.db.fetch_one(
                                "SELECT id, quantity FROM player_inventory WHERE player_id = ? AND item_id = ?",
                                (player_id, item_id),
                            )
                            if inventory:
                                new_qty = max(0, inventory["quantity"] - loss_qty)
                                if new_qty <= 0:
                                    await self.db.execute(
                                        "DELETE FROM player_inventory WHERE id = ?",
                                        (inventory["id"],),
                                    )
                                else:
                                    await self.db.execute(
                                        "UPDATE player_inventory SET quantity = ? WHERE id = ?",
                                        (new_qty, inventory["id"]),
                                    )

                        lost_items_msg = "突破材料亦在天劫中损毁大半！"

                await self.db.commit()

                message_lines = [
                    f"【{next_realm_name}之劫】",
                    "天劫凶猛，你未能抵挡，突破失败！",
                    f"修为受损，损失了 {exp_loss} 点修为。",
                ]
                if lost_items_msg:
                    message_lines.append(lost_items_msg)
                message_lines.append("请重整旗鼓，待时机成熟再试。")

                return {
                    "success": False,
                    "exp_loss": exp_loss,
                    "message": "\n".join(message_lines),
                }

        # 突破成功
        from ..utils.attributes import calc_battle_attrs

        new_attrs = calc_battle_attrs(
            level=next_realm["level"],
            bone=player["bone"],
            spirit=player["spirit"],
            intel=player["intel"],
            str_=player["str"],
            percep=player["percep"],
            luck=player["luck"],
        )

        # 通过统一入口重置修为为0（遵循"所有数值增减用同一接口"规范）
        if self.cultivation_service:
            await self.cultivation_service.add_experience(player_id, -player["experience"])
        else:
            await self.db.execute(
                "UPDATE players SET experience = 0, updated_at = ? WHERE id = ?",
                (bj_now_iso(), player_id),
            )

        # 清空临时修为并更新境界和属性
        await self.db.execute(
            """UPDATE players
            SET realm_id = ?,
                temp_experience = 0,
                health = ?,
                mp = ?,
                stamina = ?,
                updated_at = ?
            WHERE id = ?""",
            (
                next_realm["id"],
                new_attrs["max_health"],
                new_attrs["max_mp"],
                new_attrs["max_stamina"],
                bj_now_iso(),
                player_id,
            ),
        )
        await self.db.commit()

        # 构建突破消息
        condition_desc = condition["description"] if condition else ""
        if is_manual:
            message = (
                f"【{next_realm_name}之劫】"
                f"天雷滚滚，你凭借至宝护体，成功渡过天劫！\n"
                f"恭喜！你成功突破到【{next_realm_name}】！\n"
            )
            if condition_desc:
                message += f"{condition_desc}"
        else:
            message = (
                f"【自动突破】"
                f"你的修为已达巅峰，{condition_desc if condition_desc else '顺势突破'}！\n"
                f"恭喜！你成功突破到【{next_realm_name}】！"
            )

        logger.info(
            f"玩家 {player_id} 突破成功，从 {current_realm_name} 晋升为 {next_realm_name}"
        )

        return {
            "success": True,
            "old_realm": current_realm_name,
            "new_realm": next_realm_name,
            "message": message,
        }

    async def get_breakthrough_status(self, player_id: str) -> dict[str, Any]:
        """
        获取玩家突破状态

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 突破状态信息
        """
        player = await self.db.fetch_one(
            "SELECT * FROM players WHERE id = ?",
            (player_id,),
        )
        if not player:
            raise ValueError("玩家不存在")

        player_realm = None
        if self.cultivation_service:
            player_realm = await self.cultivation_service.get_realm_by_id(player["realm_id"])

        current_level = player_realm.level if player_realm and hasattr(player_realm, 'level') else player.get("realm_level", 1)
        current_exp = player["experience"]
        current_realm_name = player_realm.name if player_realm and hasattr(player_realm, 'name') else player.get("realm_name", "未知")

        next_realm = None
        next_realm_dict = None
        if self.cultivation_service:
            next_realm = await self.cultivation_service.get_next_realm(current_level)
            if next_realm and hasattr(next_realm, 'to_dict'):
                next_realm_dict = next_realm.to_dict()
            elif next_realm:
                next_realm_dict = next_realm

        if not next_realm or not next_realm_dict:
            return {
                "can_breakthrough": False,
                "message": "你已达到最高境界",
            }

        # 查询突破条件
        condition = await self.get_breakthrough_condition(next_realm_dict["id"])

        result = {
            "current_realm": current_realm_name,
            "next_realm": next_realm_dict["name"],
            "current_exp": current_exp,
            "required_exp": next_realm_dict["experience_required"],
            "exp_enough": current_exp >= next_realm_dict["experience_required"],
            "condition": condition,
        }

        if condition:
            item_requirements = condition.get("item_requirements", [])
            if item_requirements:
                item_check = await self.check_breakthrough_items(
                    player_id, item_requirements
                )
                result["items_ready"] = item_check["can_breakthrough"]
                result["item_details"] = item_check
            else:
                result["items_ready"] = True
        else:
            result["items_ready"] = True

        result["can_breakthrough"] = result["exp_enough"] and result.get(
            "items_ready", True
        )

        return result
