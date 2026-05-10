"""
物品效果服务
负责物品使用时的条件校验、效果触发、提示生成等核心业务逻辑
是物品与效果系统架构的核心枢纽

架构分层:
- 基础支撑层: 配置加载、数量校验、条件匹配
- 配置定义层: 物品配置、效果配置、提示文案配置（JSON文件）
- 核心业务层: 条件校验、效果触发、物品管理
- 交互提示层: 提示生成与展示
"""

from typing import TYPE_CHECKING, Any

from astrbot.api import logger

from ..database import DatabaseManager
from ..models import Item
from ..utils import bj_now, to_db_iso
from .effects import EffectRegistry, register_all_effects

if TYPE_CHECKING:
    from ..config import ConfigManager
    from ..data.json_data_manager import JsonDataManager
    from .cultivation_service import CultivationService
    from .inventory_service import InventoryService


class ItemEffectService:
    """
    物品效果服务类
    承接配置层定义，实现物品使用、效果触发、条件校验等核心逻辑
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        config_manager: "ConfigManager" = None,
        json_data_manager: "JsonDataManager" = None,
        cultivation_service: "CultivationService" = None,
        inventory_service: "InventoryService" = None,
    ):
        """
        初始化物品效果服务

        Args:
            db_manager: 数据库管理器实例
            config_manager: 配置管理器实例
            json_data_manager: JSON数据管理器实例
            cultivation_service: 修炼服务实例
            inventory_service: 背包服务实例
        """
        self.db = db_manager
        self.config_manager = config_manager
        self.json_data_manager = json_data_manager
        self.cultivation_service = cultivation_service
        self.inventory_service = inventory_service
        # 初始化效果注册器，注册所有内置效果
        self.effect_registry = register_all_effects()
        # 效果配置缓存
        self._effects_cache: dict[str, dict[str, Any]] = {}
        self._effects_loaded = False
        # 提示文案配置缓存
        self._prompts_cache: dict[str, str] = {}
        self._prompts_loaded = False

    # ==================== 配置加载 ====================

    async def _ensure_effects_loaded(self) -> None:
        """确保效果配置已加载"""
        if not self._effects_loaded and self.json_data_manager:
            await self.json_data_manager.load_data("effects", [])
            all_effects = await self.json_data_manager.get_all("effects")
            self._effects_cache = {e["effect_id"]: e for e in all_effects}
            self._effects_loaded = True

    async def _ensure_prompts_loaded(self) -> None:
        """确保提示文案配置已加载"""
        if not self._prompts_loaded:
            import json
            from pathlib import Path

            prompts_file = (
                Path(self.json_data_manager.data_dir) / "prompts.json"
                if self.json_data_manager
                else None
            )
            if prompts_file and prompts_file.exists():
                try:
                    import aiofiles

                    async with aiofiles.open(prompts_file, "r", encoding="utf-8") as f:
                        content = await f.read()
                        self._prompts_cache = json.loads(content)
                except Exception as e:
                    logger.error(f"加载提示文案配置失败: {e}")
            self._prompts_loaded = True

    async def reload_effects(self) -> None:
        """热重载效果配置"""
        if self.json_data_manager:
            await self.json_data_manager.reload("effects")
            all_effects = await self.json_data_manager.get_all("effects")
            self._effects_cache = {e["effect_id"]: e for e in all_effects}
        logger.info("效果配置已热重载")

    async def reload_prompts(self) -> None:
        """热重载提示文案配置"""
        self._prompts_loaded = False
        await self._ensure_prompts_loaded()
        logger.info("提示文案配置已热重载")

    # ==================== 提示生成（交互提示层） ====================

    async def get_prompt(self, prompt_key: str, **kwargs: Any) -> str:
        """
        获取提示文案并替换动态参数

        Args:
            prompt_key: 提示文案键名
            **kwargs: 动态替换参数

        Returns:
            str: 替换后的提示文案，未找到则返回通用提示
        """
        await self._ensure_prompts_loaded()
        template = self._prompts_cache.get(prompt_key, "")
        if not template:
            return kwargs.get("fallback", f"未知提示: {prompt_key}")
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"提示文案参数缺失: {e}, key={prompt_key}")
            return template

    # ==================== 条件校验（核心业务层） ====================

    async def check_conditions(
        self,
        player_id: str,
        item: Item,
        player_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        校验物品使用条件

        逐一对物品配置的 use_conditions 进行校验
        若所有条件满足返回 success=True，否则返回失败原因和提示信息

        Args:
            player_id: 玩家ID
            item: 物品对象
            player_data: 玩家数据（可选，避免重复查询）

        Returns:
            Dict[str, Any]: 校验结果，包含 success、message 字段
        """
        conditions = item.use_conditions if hasattr(item, "use_conditions") else []
        if not conditions:
            return {"success": True}

        # 获取玩家数据
        if player_data is None:
            player_data = await self.db.fetch_one(
                "SELECT * FROM players WHERE id = ?", (player_id,)
            )
        if not player_data:
            return {"success": False, "message": "玩家数据不存在"}

        for condition in conditions:
            condition_type = condition.get("condition_type", "")
            condition_value = condition.get("condition_value", "")
            prompt_key = condition.get("prompt_key", "no_use_permission")

            result = await self._check_single_condition(
                player_id, player_data, item, condition_type, condition_value
            )
            if not result["passed"]:
                # 条件不满足，生成对应提示
                message = await self.get_prompt(
                    prompt_key,
                    item_name=item.name,
                    required_realm=result.get("required_realm", condition_value),
                    current_realm=result.get("current_realm", "未知"),
                    required_cultivation=result.get("required_cultivation", 0),
                    current_cultivation=result.get("current_cultivation", 0),
                    lack_item_name=result.get("lack_item_name", ""),
                    lack_num=result.get("lack_num", 0),
                    current_num=result.get("current_num", 0),
                    fallback=f"不满足使用【{item.name}】的条件",
                )
                return {"success": False, "message": message}

        return {"success": True}

    async def _check_single_condition(
        self,
        player_id: str,
        player_data: dict[str, Any],
        item: Item,
        condition_type: str,
        condition_value: Any,
    ) -> dict[str, Any]:
        """
        校验单个条件

        Args:
            player_id: 玩家ID
            player_data: 玩家数据
            item: 物品对象
            condition_type: 条件类型（realm/cultivation/item）
            condition_value: 条件值

        Returns:
            Dict[str, Any]: 校验结果，包含 passed 字段
        """
        if condition_type == "realm":
            return await self._check_realm_condition(player_data, condition_value)
        elif condition_type == "cultivation":
            return await self._check_cultivation_condition(player_data, condition_value)
        elif condition_type == "item":
            condition_num = 1
            return await self._check_item_condition(
                player_id, condition_value, condition_num
            )
        else:
            logger.warning(f"未知的条件类型: {condition_type}")
            return {"passed": True}

    async def _check_realm_condition(
        self, player_data: dict[str, Any], required_realm_id: str
    ) -> dict[str, Any]:
        """
        校验境界条件

        Args:
            player_data: 玩家数据
            required_realm_id: 所需境界ID

        Returns:
            Dict[str, Any]: 校验结果
        """
        if not self.cultivation_service:
            return {"passed": True}

        required_realm = await self.cultivation_service.get_realm_by_id(required_realm_id)
        if not required_realm:
            return {"passed": True}

        player_realm = await self.cultivation_service.get_realm_by_id(
            player_data["realm_id"]
        )

        player_level = (
            player_realm.level
            if player_realm and hasattr(player_realm, "level")
            else player_data.get("realm_level", 1)
        )
        required_level = (
            required_realm.level
            if hasattr(required_realm, "level")
            else required_realm.get("level", 1)
        )
        required_name = (
            required_realm.name
            if hasattr(required_realm, "name")
            else required_realm.get("name", "未知")
        )
        player_realm_name = (
            player_realm.name
            if player_realm and hasattr(player_realm, "name")
            else "未知"
        )

        if player_level < required_level:
            return {
                "passed": False,
                "required_realm": required_name,
                "current_realm": player_realm_name,
            }
        return {"passed": True}

    async def _check_cultivation_condition(
        self, player_data: dict[str, Any], required_cultivation: int
    ) -> dict[str, Any]:
        """
        校验修为条件

        Args:
            player_data: 玩家数据
            required_cultivation: 所需修为值

        Returns:
            Dict[str, Any]: 校验结果
        """
        current = player_data.get("experience", 0)
        if current < int(required_cultivation):
            return {
                "passed": False,
                "required_cultivation": required_cultivation,
                "current_cultivation": current,
            }
        return {"passed": True}

    async def _check_item_condition(
        self, player_id: str, required_item_id: str, required_num: int
    ) -> dict[str, Any]:
        """
        校验所需物品条件

        Args:
            player_id: 玩家ID
            required_item_id: 所需物品ID
            required_num: 所需数量

        Returns:
            Dict[str, Any]: 校验结果
        """
        inventory_item = await self.db.fetch_one(
            "SELECT * FROM player_inventory WHERE player_id = ? AND item_id = ?",
            (player_id, required_item_id),
        )
        current_num = inventory_item["quantity"] if inventory_item else 0

        if current_num < required_num:
            # 获取所需物品名称
            lack_item_name = required_item_id
            if self.inventory_service:
                item_obj = await self.inventory_service.get_item_by_id(required_item_id)
                if item_obj:
                    lack_item_name = item_obj.name

            return {
                "passed": False,
                "lack_item_name": lack_item_name,
                "lack_num": required_num,
                "current_num": current_num,
            }
        return {"passed": True}

    # ==================== 数量校验（基础支撑层） ====================

    async def check_quantity(
        self, player_id: str, item_id: str, need_num: int = 1
    ) -> dict[str, Any]:
        """
        校验物品数量是否充足

        Args:
            player_id: 玩家ID
            item_id: 物品ID
            need_num: 需要数量

        Returns:
            Dict[str, Any]: 校验结果，包含 sufficient、current_num 字段
        """
        inventory_item = await self.db.fetch_one(
            "SELECT * FROM player_inventory WHERE player_id = ? AND item_id = ?",
            (player_id, item_id),
        )
        current_num = inventory_item["quantity"] if inventory_item else 0
        return {
            "sufficient": current_num >= need_num,
            "current_num": current_num,
            "need_num": need_num,
        }

    # ==================== 效果触发（核心业务层） ====================

    async def trigger_effects(
        self,
        player_id: str,
        item: Item,
        quantity: int = 1,
    ) -> dict[str, Any]:
        """
        触发物品关联的所有效果

        根据物品配置的 effect_ids，逐一对效果进行触发
        每个效果根据 effect_type 调用对应的实现类

        Args:
            player_id: 玩家ID
            item: 物品对象
            quantity: 使用数量（影响效果叠加）

        Returns:
            Dict[str, Any]: 触发结果，包含 success、effect_results、message 字段
        """
        await self._ensure_effects_loaded()

        effect_ids = item.effect_ids if hasattr(item, "effect_ids") else []
        if not effect_ids:
            return {
                "success": True,
                "effect_results": [],
                "message": f"使用了【{item.name}】",
            }

        effect_results = []
        all_success = True

        for effect_id in effect_ids:
            effect_config = self._effects_cache.get(effect_id)
            if not effect_config:
                logger.warning(f"效果配置不存在: {effect_id}")
                effect_results.append(
                    {"effect_id": effect_id, "success": False, "desc": "效果配置不存在"}
                )
                all_success = False
                continue

            effect_type = effect_config.get("effect_type", "")
            effect_params = dict(effect_config.get("effect_params", {}))

            # 根据使用数量叠加效果参数
            effect_params = self._scale_params_by_quantity(effect_params, quantity)

            # 通过注册器获取效果实现类
            effect_impl = self.effect_registry.get(effect_type)
            if not effect_impl:
                logger.warning(f"未注册的效果类型: {effect_type}")
                effect_results.append(
                    {
                        "effect_id": effect_id,
                        "success": False,
                        "desc": f"未注册的效果类型: {effect_type}",
                    }
                )
                all_success = False
                continue

            try:
                result = await effect_impl.trigger(
                    player_id=player_id,
                    params=effect_params,
                    db_manager=self.db,
                    cultivation_service=self.cultivation_service,
                )
                effect_results.append(
                    {
                        "effect_id": effect_id,
                        "success": result.success,
                        "desc": result.effect_desc,
                        "params": result.effect_params,
                        "error": result.error_msg if not result.success else "",
                    }
                )
                if not result.success:
                    all_success = False
            except Exception as e:
                logger.error(f"效果触发异常: effect_id={effect_id}, error={e}")
                effect_results.append(
                    {"effect_id": effect_id, "success": False, "desc": str(e)}
                )
                all_success = False

        # 生成汇总提示
        effect_descs = [r["desc"] for r in effect_results if r["success"]]
        message = self._build_effect_message(item, effect_descs)

        return {
            "success": all_success,
            "effect_results": effect_results,
            "message": message,
        }

    def _scale_params_by_quantity(
        self, params: dict[str, Any], quantity: int
    ) -> dict[str, Any]:
        """
        根据使用数量叠加效果参数
        数值型参数乘以数量，持续时间类参数保持不变

        Args:
            params: 原始效果参数
            quantity: 使用数量

        Returns:
            Dict[str, Any]: 叠加后的效果参数
        """
        if quantity <= 1:
            return params

        scaled = dict(params)
        # 需要叠加的数值参数键名
        scalable_keys = {
            "cultivation_value",
            "heal_value",
            "stone_value",
            "rate_value",
            "attribute_value",
        }
        for key in scalable_keys:
            if key in scaled and isinstance(scaled[key], (int, float)):
                scaled[key] = int(scaled[key] * quantity)
        return scaled

    def _build_effect_message(self, item: Item, effect_descs: list[str]) -> str:
        """
        构建效果触发后的汇总提示信息

        Args:
            item: 物品对象
            effect_descs: 各效果的描述列表

        Returns:
            str: 汇总提示信息
        """
        if not effect_descs:
            return f"使用了【{item.name}】"

        if len(effect_descs) == 1:
            return f"成功使用【{item.name}】，{effect_descs[0]}！"

        lines = [f"成功使用【{item.name}】："]
        for desc in effect_descs:
            lines.append(f"  · {desc}")
        return "\n".join(lines)

    # ==================== 物品使用主流程 ====================

    async def use_item(
        self,
        player_id: str,
        item: Item,
        quantity: int = 1,
    ) -> dict[str, Any]:
        """
        使用物品主流程

        完整流程:
        1. 数量校验 → 2. 条件校验 → 3. 消耗物品 → 4. 触发效果 → 5. 生成提示

        Args:
            player_id: 玩家ID
            item: 物品对象
            quantity: 使用数量

        Returns:
            Dict[str, Any]: 使用结果，包含 success、message 字段
        """
        # 1. 检查物品是否可使用
        if not item.is_usable:
            message = await self.get_prompt(
                "item_not_usable",
                item_name=item.name,
                fallback=f"【{item.name}】不可使用",
            )
            return {"success": False, "message": message}

        # 2. 数量校验
        consume_num = getattr(item, "consume_num", 1) or 1
        total_need = consume_num * quantity
        qty_check = await self.check_quantity(player_id, item.id, total_need)
        if not qty_check["sufficient"]:
            message = await self.get_prompt(
                "lack_num",
                item_name=item.name,
                need_num=total_need,
                current_num=qty_check["current_num"],
                fallback=f"【{item.name}】数量不足，需{total_need}个（当前拥有：{qty_check['current_num']}）",
            )
            return {"success": False, "message": message}

        # 3. 条件校验
        condition_result = await self.check_conditions(player_id, item)
        if not condition_result["success"]:
            return {"success": False, "message": condition_result["message"]}

        # 4. 消耗物品
        if total_need > 0:
            await self.inventory_service.remove_item(player_id, item.id, total_need)

        # 5. 触发效果
        effect_result = await self.trigger_effects(player_id, item, quantity)

        return {
            "success": effect_result["success"],
            "message": effect_result["message"],
            "effect_results": effect_result.get("effect_results", []),
        }

    # ==================== 效果配置管理 ====================

    async def get_all_effects(self) -> list[dict[str, Any]]:
        """
        获取所有效果配置

        Returns:
            List[Dict[str, Any]]: 效果配置列表
        """
        await self._ensure_effects_loaded()
        return list(self._effects_cache.values())

    async def get_effect_by_id(self, effect_id: str) -> dict[str, Any] | None:
        """
        根据ID获取效果配置

        Args:
            effect_id: 效果ID

        Returns:
            Optional[Dict[str, Any]]: 效果配置，不存在返回 None
        """
        await self._ensure_effects_loaded()
        return self._effects_cache.get(effect_id)

    async def create_effect(self, effect_data: dict[str, Any]) -> dict[str, Any]:
        """
        创建新效果配置

        Args:
            effect_data: 效果数据

        Returns:
            Dict[str, Any]: 创建的效果配置
        """
        await self._ensure_effects_loaded()
        new_effect = await self.json_data_manager.create("effects", effect_data)
        self._effects_cache[new_effect["effect_id"]] = new_effect
        return new_effect

    async def update_effect(
        self, effect_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        更新效果配置

        Args:
            effect_id: 效果ID
            updates: 更新字段

        Returns:
            Optional[Dict[str, Any]]: 更新后的效果配置
        """
        await self._ensure_effects_loaded()
        updated = await self.json_data_manager.update("effects", effect_id, updates)
        if updated:
            self._effects_cache[effect_id] = updated
        return updated

    async def delete_effect(self, effect_id: str) -> bool:
        """
        删除效果配置

        Args:
            effect_id: 效果ID

        Returns:
            bool: 是否删除成功
        """
        await self._ensure_effects_loaded()
        success = await self.json_data_manager.delete("effects", effect_id)
        if success and effect_id in self._effects_cache:
            del self._effects_cache[effect_id]
        return success

    # ==================== 提示文案管理 ====================

    async def get_all_prompts(self) -> dict[str, str]:
        """
        获取所有提示文案配置

        Returns:
            Dict[str, str]: 提示文案字典
        """
        await self._ensure_prompts_loaded()
        return dict(self._prompts_cache)

    async def update_prompt(self, key: str, value: str) -> None:
        """
        更新单条提示文案

        Args:
            key: 提示键名
            value: 提示文案模板
        """
        await self._ensure_prompts_loaded()
        self._prompts_cache[key] = value
        await self._save_prompts()

    async def _save_prompts(self) -> None:
        """保存提示文案配置到文件"""
        import json
        from pathlib import Path

        if not self.json_data_manager:
            return

        prompts_file = Path(self.json_data_manager.data_dir) / "prompts.json"
        try:
            import aiofiles

            async with aiofiles.open(prompts_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(self._prompts_cache, ensure_ascii=False, indent=2)
                )
            logger.info("提示文案配置已保存")
        except Exception as e:
            logger.error(f"保存提示文案配置失败: {e}")

    # ==================== 临时增益管理 ====================

    async def cleanup_expired_buffs(self, player_id: str) -> int:
        """
        清理指定玩家的过期临时增益

        Args:
            player_id: 玩家ID

        Returns:
            int: 清理的记录数
        """
        from datetime import datetime

        now = bj_now()
        cursor = await self.db.execute(
            "DELETE FROM temp_buffs WHERE player_id = ? AND expires_at <= ?",
            (player_id, to_db_iso(now)),
        )
        await self.db.commit()
        return cursor.rowcount if cursor and hasattr(cursor, "rowcount") else 0

    async def get_active_buffs(
        self, player_id: str, buff_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        获取玩家当前有效的临时增益

        Args:
            player_id: 玩家ID
            buff_type: 增益类型过滤（可选）

        Returns:
            List[Dict[str, Any]]: 有效增益列表
        """
        from datetime import datetime

        now = bj_now()
        # 清理过期增益
        await self.db.execute(
            "DELETE FROM temp_buffs WHERE player_id = ? AND expires_at <= ?",
            (player_id, to_db_iso(now)),
        )
        await self.db.commit()

        if buff_type:
            rows = await self.db.fetch_all(
                "SELECT * FROM temp_buffs WHERE player_id = ? AND buff_type = ? AND expires_at > ?",
                (player_id, buff_type, to_db_iso(now)),
            )
        else:
            rows = await self.db.fetch_all(
                "SELECT * FROM temp_buffs WHERE player_id = ? AND expires_at > ?",
                (player_id, to_db_iso(now)),
            )
        return [dict(r) for r in rows]

    async def get_buff_total_value(
        self, player_id: str, buff_type: str
    ) -> int:
        """
        获取玩家某类增益的总加成值

        Args:
            player_id: 玩家ID
            buff_type: 增益类型

        Returns:
            int: 总加成值
        """
        buffs = await self.get_active_buffs(player_id, buff_type)
        return sum(b.get("buff_value", 0) for b in buffs)
