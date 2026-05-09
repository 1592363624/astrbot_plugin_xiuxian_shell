"""
修炼服务
处理修炼、闭关、功法、境界突破等业务逻辑
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from astrbot.api import logger

from ..database import DatabaseManager
from ..models import Realm, Skill

if TYPE_CHECKING:
    from ..config import ConfigManager


class CultivationService:
    """修炼服务类"""

    def __init__(
        self, db_manager: DatabaseManager, config_manager: "ConfigManager" = None
    ):
        """
        初始化修炼服务

        Args:
            db_manager: 数据库管理器实例
            config_manager: 配置管理器实例
        """
        self.db = db_manager
        self.config_manager = config_manager

    def _get_seclusion_config(self) -> dict[str, Any]:
        """获取闭关配置"""
        if self.config_manager:
            return self.config_manager.get("seclusion", {})
        return {}

    async def cultivate(
        self, player_id: str, skill_id: str | None = None
    ) -> dict[str, Any]:
        """
        进行修炼

        Args:
            player_id: 玩家ID
            skill_id: 功法ID（可选，默认使用基础功法）

        Returns:
            Dict[str, Any]: 修炼结果
        """
        player = await self.db.fetch_one(
            "SELECT realm_id, experience FROM players WHERE id = ?", (player_id,)
        )
        if not player:
            raise ValueError("玩家不存在")

        if skill_id:
            skill = await self.get_skill_by_id(skill_id)
        else:
            skill = await self.get_skill_by_id("skill_001")

        if not skill:
            raise ValueError("功法不存在")

        exp_gain = skill.experience_gain

        await self.db.execute(
            "UPDATE players SET experience = experience + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (exp_gain, player_id),
        )
        await self.db.commit()

        logger.info(f"玩家 {player_id} 修炼获得 {exp_gain} 修为")

        return {
            "success": True,
            "skill_name": skill.name,
            "exp_gain": exp_gain,
            "message": f"你修炼了【{skill.name}】，获得 {exp_gain} 点修为",
        }

    # ==================== 闭关修炼 ====================

    async def seclusion(self, player_id: str) -> dict[str, Any]:
        """
        闭关修炼
        主动进行修炼，获取大量修为点数。有成功、失败、走火入魔三种可能，
        且有随机时长的冷却。闭关时有几率触发奇遇。

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 闭关结果
        """
        player = await self.db.fetch_one(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        )
        if not player:
            raise ValueError("玩家不存在")

        cooldown_remaining = await self._check_seclusion_cooldown(player_id)
        if cooldown_remaining > 0:
            return {
                "success": False,
                "message": f"你感到一阵疲惫，需要打坐调息{cooldown_remaining}分钟方可再次闭关。",
            }

        current_realm = await self.get_realm_by_id(player["realm_id"])
        if not current_realm:
            raise ValueError("当前境界数据异常")

        next_realm = await self.get_next_realm(current_realm.level)
        base_exp = (
            next_realm.experience_required
            if next_realm
            else current_realm.experience_required
        )

        seclusion_cfg = self._get_seclusion_config()
        success_prob = seclusion_cfg.get("success_probability", 0.60)
        failure_prob = seclusion_cfg.get("failure_probability", 0.25)
        exp_ratio_min = seclusion_cfg.get("exp_ratio_min", 0.001)
        exp_ratio_max = seclusion_cfg.get("exp_ratio_max", 0.001)
        possession_exp_ratio = seclusion_cfg.get("possession_exp_ratio", 0.001)
        cooldown_min = seclusion_cfg.get("cooldown_min_minutes", 10)
        cooldown_max = seclusion_cfg.get("cooldown_max_minutes", 30)
        encounter_prob = seclusion_cfg.get("encounter_probability", 0.10)

        roll = random.random()
        if roll < success_prob:
            result_type = "success"
            ratio = random.uniform(exp_ratio_min, exp_ratio_max)
            exp_change = max(1, int(base_exp * ratio))
        elif roll < success_prob + failure_prob:
            result_type = "failure"
            ratio = random.uniform(exp_ratio_min, exp_ratio_max)
            exp_change = -max(1, int(base_exp * ratio))
        else:
            result_type = "possession"
            exp_change = -max(1, int(base_exp * possession_exp_ratio))

        cooldown_minutes = random.randint(cooldown_min, cooldown_max)

        await self.db.execute(
            "UPDATE players SET experience = MAX(0, experience + ?), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (exp_change, player_id),
        )

        encounter_result = None
        if random.random() < encounter_prob:
            encounter_result = await self._trigger_seclusion_encounter(player_id)

        now = datetime.utcnow()
        cooldown_until = now + timedelta(minutes=cooldown_minutes)

        record_id = str(uuid.uuid4())
        await self.db.execute(
            """INSERT INTO seclusion_records
            (id, player_id, result, exp_change, encounter_event_id, cooldown_minutes, started_at, cooldown_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record_id,
                player_id,
                result_type,
                exp_change,
                encounter_result.get("event_id") if encounter_result else None,
                cooldown_minutes,
                now.isoformat(),
                cooldown_until.isoformat(),
            ),
        )
        await self.db.commit()

        updated_player = await self.db.fetch_one(
            "SELECT experience FROM players WHERE id = ?", (player_id,)
        )
        current_exp = updated_player["experience"] if updated_player else 0

        result_map = {
            "success": "【闭关成功】",
            "failure": "【闭关失败】",
            "possession": "【走火入魔】",
        }
        result_header = result_map.get(result_type, "【闭关结束】")

        message_lines = []
        if result_type == "success":
            message_lines.append(f"{result_header}")
            message_lines.append(
                f"福至心灵，成功炼化灵气，基础修为增加了{exp_change}点。"
            )
            message_lines.append(f"本次闭关，你的修为最终增加了{exp_change}点。")
        elif result_type == "failure":
            message_lines.append(f"{result_header}")
            message_lines.append(f"心神不宁，灵气四散，修为减少了{abs(exp_change)}点。")
            message_lines.append(f"本次闭关，你的修为最终减少了{abs(exp_change)}点。")
        else:
            message_lines.append(f"{result_header}")
            message_lines.append(
                f"体内灵力暴走，经脉受损，修为减少了{abs(exp_change)}点！"
            )

        if encounter_result:
            message_lines.append(f"【奇遇】{encounter_result['message']}")

        # 获取下一境界所需修为作为显示分母，如果没有下一境界则显示当前境界要求
        next_realm_for_display = await self.get_next_realm(current_realm.level)
        exp_required = (
            next_realm_for_display.experience_required
            if next_realm_for_display
            else current_realm.experience_required
        )

        message_lines.append(f"当前境界：{current_realm.name}")
        message_lines.append(f"当前修为：{current_exp}/{exp_required}")
        message_lines.append(
            f"你感到一阵疲惫，需要打坐调息{cooldown_minutes}分钟方可再次闭关。"
        )

        logger.info(
            f"玩家 {player_id} 闭关结果: {result_type}, 修为变化: {exp_change}, 冷却: {cooldown_minutes}分钟"
        )

        return {
            "success": True,
            "result_type": result_type,
            "exp_change": exp_change,
            "current_exp": current_exp,
            "realm_name": current_realm.name,
            "cooldown_minutes": cooldown_minutes,
            "encounter": encounter_result,
            "message": "\n".join(message_lines),
        }

    async def _check_seclusion_cooldown(self, player_id: str) -> int:
        """
        检查闭关冷却时间

        Args:
            player_id: 玩家ID

        Returns:
            int: 剩余冷却分钟数，0表示可以闭关
        """
        record = await self.db.fetch_one(
            "SELECT cooldown_until FROM seclusion_records WHERE player_id = ? ORDER BY started_at DESC LIMIT 1",
            (player_id,),
        )
        if not record or not record["cooldown_until"]:
            return 0

        cooldown_until = datetime.fromisoformat(record["cooldown_until"])
        now = datetime.utcnow()
        if now >= cooldown_until:
            return 0

        remaining = (cooldown_until - now).total_seconds() / 60
        return max(1, int(remaining))

    async def _trigger_seclusion_encounter(
        self, player_id: str
    ) -> dict[str, Any] | None:
        """
        触发闭关奇遇事件

        Args:
            player_id: 玩家ID

        Returns:
            Optional[Dict[str, Any]]: 奇遇结果
        """
        events = await self.db.fetch_all(
            "SELECT * FROM game_events WHERE trigger_condition = 'seclusion' AND is_active = 1"
        )
        if not events:
            return None

        for event_data in events:
            if random.random() < event_data["probability"]:
                event_id = event_data["id"]
                event_name = event_data["name"]
                event_desc = event_data["description"]

                reward_message = ""
                if event_data["reward_type"] == "item" and event_data["reward_value"]:
                    from ..services import InventoryService

                    inventory_svc = InventoryService(self.db)
                    item = await inventory_svc.get_item_by_id(
                        str(event_data["reward_value"])
                    )
                    if item:
                        await inventory_svc.add_item(player_id, item.id, 1)
                        reward_message = f"一道流光砸在你的洞府门前，竟是{event_desc}，你从中提炼出了【{item.name}】x1！"
                    else:
                        reward_message = f"{event_desc}"
                elif event_data["reward_type"] == "spirit_stone":
                    value = event_data["reward_value"]
                    await self.db.execute(
                        "UPDATE players SET spirit_stone = spirit_stone + ? WHERE id = ?",
                        (value, player_id),
                    )
                    reward_message = f"{event_desc}，获得{value}灵石！"
                elif event_data["reward_type"] == "experience":
                    value = event_data["reward_value"]
                    await self.db.execute(
                        "UPDATE players SET experience = experience + ? WHERE id = ?",
                        (value, player_id),
                    )
                    reward_message = f"{event_desc}，额外获得{value}点修为！"
                else:
                    reward_message = f"{event_desc}"

                return {
                    "event_id": event_id,
                    "event_name": event_name,
                    "message": reward_message,
                }

        return None

    async def get_seclusion_status(self, player_id: str) -> dict[str, Any]:
        """
        获取玩家闭关状态

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 闭关状态信息
        """
        cooldown_remaining = await self._check_seclusion_cooldown(player_id)
        last_record = await self.db.fetch_one(
            "SELECT * FROM seclusion_records WHERE player_id = ? ORDER BY started_at DESC LIMIT 1",
            (player_id,),
        )

        return {
            "can_seclude": cooldown_remaining == 0,
            "cooldown_remaining_minutes": cooldown_remaining,
            "last_record": dict(last_record) if last_record else None,
        }

    async def get_seclusion_records(
        self, player_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        获取玩家闭关记录

        Args:
            player_id: 玩家ID
            limit: 返回记录数量上限

        Returns:
            List[Dict[str, Any]]: 闭关记录列表
        """
        rows = await self.db.fetch_all(
            "SELECT * FROM seclusion_records WHERE player_id = ? ORDER BY started_at DESC LIMIT ?",
            (player_id, limit),
        )
        return [dict(r) for r in rows]

    # ==================== 突破 ====================

    async def breakthrough(self, player_id: str) -> dict[str, Any]:
        """
        尝试境界突破

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 突破结果
        """
        player = await self.db.fetch_one(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        )
        if not player:
            raise ValueError("玩家不存在")

        current_realm = await self.get_realm_by_id(player["realm_id"])
        if not current_realm:
            raise ValueError("当前境界数据异常")

        next_realm = await self.get_next_realm(current_realm.level)
        if not next_realm:
            return {
                "success": False,
                "message": "你已达到最高境界，无法继续突破",
            }

        if player["experience"] < next_realm.experience_required:
            return {
                "success": False,
                "current_exp": player["experience"],
                "required_exp": next_realm.experience_required,
                "message": f"修为不足，需要 {next_realm.experience_required} 点修为，当前仅有 {player['experience']} 点",
            }

        success_rate = next_realm.breakthrough_probability / 100.0

        if random.random() < success_rate:
            from ..utils import calc_battle_attrs

            new_attrs = calc_battle_attrs(
                next_realm.level,
                player["bone"],
                player["spirit"],
                player["intel"],
                player["str"],
                player["percep"],
                player["luck"],
            )

            await self.db.execute(
                """UPDATE players
                SET realm_id = ?,
                    health = ?,
                    mp = ?,
                    stamina = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?""",
                (
                    next_realm.id,
                    new_attrs["max_health"],
                    new_attrs["max_mp"],
                    new_attrs["max_stamina"],
                    player_id,
                ),
            )
            await self.db.commit()

            logger.info(f"玩家 {player_id} 突破成功，晋升为 {next_realm.name}")

            return {
                "success": True,
                "old_realm": current_realm.name,
                "new_realm": next_realm.name,
                "breakthrough_probability": next_realm.breakthrough_probability,
                "message": f"恭喜！你成功突破到【{next_realm.name}】！",
            }
        else:
            exp_loss = int(next_realm.experience_required * 0.1)
            await self.db.execute(
                "UPDATE players SET experience = MAX(0, experience - ?), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (exp_loss, player_id),
            )
            await self.db.commit()

            return {
                "success": False,
                "exp_loss": exp_loss,
                "breakthrough_probability": next_realm.breakthrough_probability,
                "message": f"突破失败！损失了 {exp_loss} 点修为，继续努力吧",
            }

    # ==================== 功法管理 ====================

    async def get_skill_by_id(self, skill_id: str) -> Skill | None:
        """根据ID获取功法"""
        sql = "SELECT * FROM skills WHERE id = ?"
        row = await self.db.fetch_one(sql, (skill_id,))
        if row:
            return Skill.from_dict(row)
        return None

    async def get_all_skills(self) -> list[Skill]:
        """获取所有功法"""
        sql = "SELECT * FROM skills ORDER BY id"
        rows = await self.db.fetch_all(sql)
        return [Skill.from_dict(row) for row in rows]

    async def create_skill(self, skill_data: dict[str, Any]) -> Skill:
        """创建功法"""
        skill_id = skill_data.get("id", str(uuid.uuid4()))
        sql = """
            INSERT INTO skills (id, name, description, skill_type, realm_requirement, experience_gain, damage, cooldown)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(
            sql,
            (
                skill_id,
                skill_data["name"],
                skill_data.get("description"),
                skill_data["skill_type"],
                skill_data.get("realm_requirement"),
                skill_data.get("experience_gain", 10),
                skill_data.get("damage", 0),
                skill_data.get("cooldown", 0),
            ),
        )
        await self.db.commit()
        return await self.get_skill_by_id(skill_id)

    async def update_skill(self, skill_id: str, **kwargs) -> Skill | None:
        """更新功法"""
        allowed_fields = [
            "name",
            "description",
            "skill_type",
            "realm_requirement",
            "experience_gain",
            "damage",
            "cooldown",
        ]
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if not updates:
            return await self.get_skill_by_id(skill_id)

        values.append(skill_id)
        sql = f"UPDATE skills SET {', '.join(updates)} WHERE id = ?"
        await self.db.execute(sql, tuple(values))
        await self.db.commit()
        return await self.get_skill_by_id(skill_id)

    async def delete_skill(self, skill_id: str) -> bool:
        """删除功法"""
        sql = "DELETE FROM skills WHERE id = ?"
        cursor = await self.db.execute(sql, (skill_id,))
        await self.db.commit()
        return cursor.rowcount > 0

    # ==================== 境界管理 ====================

    async def get_realm_by_id(self, realm_id: str) -> Realm | None:
        """根据ID获取境界"""
        sql = "SELECT * FROM realms WHERE id = ?"
        row = await self.db.fetch_one(sql, (realm_id,))
        if row:
            return Realm.from_dict(row)
        return None

    async def get_next_realm(self, current_level: int) -> Realm | None:
        """获取下一个境界"""
        sql = "SELECT * FROM realms WHERE level > ? ORDER BY level ASC LIMIT 1"
        row = await self.db.fetch_one(sql, (current_level,))
        if row:
            return Realm.from_dict(row)
        return None

    async def get_all_realms(self) -> list[Realm]:
        """获取所有境界"""
        sql = "SELECT * FROM realms ORDER BY level"
        rows = await self.db.fetch_all(sql)
        return [Realm.from_dict(row) for row in rows]

    async def create_realm(self, realm_data: dict[str, Any]) -> Realm:
        """
        创建境界

        Args:
            realm_data: 境界数据字典

        Returns:
            Realm: 创建的境界对象
        """
        realm_id = realm_data.get("id", str(uuid.uuid4()))
        sql = """
            INSERT INTO realms (id, name, description, level, experience_required,
                              breakthrough_probability, event_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(
            sql,
            (
                realm_id,
                realm_data["name"],
                realm_data.get("description"),
                realm_data["level"],
                realm_data["experience_required"],
                realm_data.get("breakthrough_probability", 50),
                realm_data.get("event_id", 1),
            ),
        )
        await self.db.commit()
        return await self.get_realm_by_id(realm_id)

    async def update_realm(self, realm_id: str, **kwargs) -> Realm | None:
        """
        更新境界

        Args:
            realm_id: 境界ID
            **kwargs: 要更新的字段

        Returns:
            Optional[Realm]: 更新后的境界对象
        """
        allowed_fields = [
            "name",
            "description",
            "level",
            "experience_required",
            "breakthrough_probability",
            "event_id",
        ]
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if not updates:
            return await self.get_realm_by_id(realm_id)

        values.append(realm_id)
        sql = f"UPDATE realms SET {', '.join(updates)} WHERE id = ?"
        await self.db.execute(sql, tuple(values))
        await self.db.commit()
        return await self.get_realm_by_id(realm_id)

    async def delete_realm(self, realm_id: str) -> bool:
        """删除境界"""
        sql = "DELETE FROM realms WHERE id = ?"
        cursor = await self.db.execute(sql, (realm_id,))
        await self.db.commit()
        return cursor.rowcount > 0
