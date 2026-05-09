"""
修炼服务
处理修炼、闭关、功法、境界突破等业务逻辑

数据存储规范:
- 境界模板数据(realms): 所有用户共享,存JSON文件
- 功法模板数据(skills): 所有用户共享,存JSON文件
- 玩家相关数据(player_skills): 每个用户独立,存数据库
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
    from ..data.json_data_manager import JsonDataManager
    from .event_service import EventService


DEFAULT_REALMS_DATA = [
    {"id": "realm_001", "name": "凡人", "description": "未踏入修仙之路的普通人", "level": 1, "experience_required": 0, "breakthrough_probability": 100, "event_id": 1},
    {"id": "realm_002", "name": "炼气初期", "description": "开始感应天地灵气，踏入修仙之门", "level": 2, "experience_required": 100, "breakthrough_probability": 90, "event_id": 1},
    {"id": "realm_003", "name": "炼气中期", "description": "灵气运转更加纯熟，实力稳步提升", "level": 3, "experience_required": 500, "breakthrough_probability": 80, "event_id": 1},
    {"id": "realm_004", "name": "炼气后期", "description": "灵气充沛，实力大增", "level": 4, "experience_required": 1000, "breakthrough_probability": 70, "event_id": 1},
    {"id": "realm_005", "name": "炼气圆满", "description": "炼气期巅峰，准备冲击筑基", "level": 5, "experience_required": 3000, "breakthrough_probability": 60, "event_id": 1},
    {"id": "realm_006", "name": "筑基初期", "description": "成功筑基，修仙之路正式开始", "level": 6, "experience_required": 4000, "breakthrough_probability": 50, "event_id": 1},
    {"id": "realm_007", "name": "筑基中期", "description": "根基稳固，实力显著提升", "level": 7, "experience_required": 6000, "breakthrough_probability": 40, "event_id": 1},
    {"id": "realm_008", "name": "筑基后期", "description": "筑基圆满在望", "level": 8, "experience_required": 8000, "breakthrough_probability": 30, "event_id": 1},
    {"id": "realm_009", "name": "筑基圆满", "description": "筑基期巅峰，准备凝聚金丹", "level": 9, "experience_required": 10000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_010", "name": "金丹初期", "description": "成功凝聚金丹，寿元大增", "level": 10, "experience_required": 12000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_011", "name": "金丹中期", "description": "金丹稳固，实力倍增", "level": 11, "experience_required": 14000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_012", "name": "金丹后期", "description": "金丹圆满在即", "level": 12, "experience_required": 16000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_013", "name": "金丹圆满", "description": "金丹期巅峰，准备化婴", "level": 13, "experience_required": 18000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_014", "name": "元婴初期", "description": "成功化婴，实力飞跃", "level": 14, "experience_required": 20000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_015", "name": "元婴中期", "description": "元婴稳固，神通初显", "level": 15, "experience_required": 22000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_016", "name": "元婴后期", "description": "元婴圆满在望", "level": 16, "experience_required": 24000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_017", "name": "元婴圆满", "description": "元婴期巅峰，准备化神", "level": 17, "experience_required": 26000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_018", "name": "化神初期", "description": "成功化神，掌握天地法则", "level": 18, "experience_required": 28000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_019", "name": "化神中期", "description": "化神稳固，法则初悟", "level": 19, "experience_required": 30000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_020", "name": "化神后期", "description": "化神圆满在即", "level": 20, "experience_required": 32000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_021", "name": "化神圆满", "description": "化神期巅峰，准备炼虚", "level": 21, "experience_required": 34000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_022", "name": "炼虚初期", "description": "开始炼虚合道", "level": 22, "experience_required": 36000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_023", "name": "炼虚中期", "description": "炼虚稳固", "level": 23, "experience_required": 38000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_024", "name": "炼虚后期", "description": "炼虚圆满在望", "level": 24, "experience_required": 40000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_025", "name": "炼虚圆满", "description": "炼虚期巅峰，准备合体", "level": 25, "experience_required": 42000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_026", "name": "合体初期", "description": "天人合一，实力大增", "level": 26, "experience_required": 44000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_027", "name": "合体中期", "description": "合体稳固", "level": 27, "experience_required": 46000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_028", "name": "合体后期", "description": "合体圆满在即", "level": 28, "experience_required": 48000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_029", "name": "合体圆满", "description": "合体期巅峰，准备大乘", "level": 29, "experience_required": 50000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_030", "name": "大乘初期", "description": "大乘之境，天地共鸣", "level": 30, "experience_required": 52000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_031", "name": "大乘中期", "description": "大乘稳固", "level": 31, "experience_required": 54000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_032", "name": "大乘后期", "description": "大乘圆满在望", "level": 32, "experience_required": 56000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_033", "name": "大乘圆满", "description": "大乘期巅峰，准备渡劫", "level": 33, "experience_required": 58000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_034", "name": "渡劫初期", "description": "天劫降临，渡劫飞升", "level": 34, "experience_required": 60000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_035", "name": "渡劫中期", "description": "渡劫稳固", "level": 35, "experience_required": 62000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_036", "name": "渡劫后期", "description": "渡劫圆满在即", "level": 36, "experience_required": 64000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_037", "name": "渡劫圆满", "description": "渡劫期巅峰，准备飞升成仙", "level": 37, "experience_required": 66000, "breakthrough_probability": 20, "event_id": 1},
    {"id": "realm_038", "name": "真仙", "description": "渡劫成功，成就真仙之体", "level": 38, "experience_required": 68000, "breakthrough_probability": 10, "event_id": 1},
    {"id": "realm_039", "name": "金仙", "description": "金身不坏，寿与天齐", "level": 39, "experience_required": 70000, "breakthrough_probability": 10, "event_id": 1},
    {"id": "realm_040", "name": "太乙金仙", "description": "太乙道果，神通广大", "level": 40, "experience_required": 72000, "breakthrough_probability": 10, "event_id": 1},
    {"id": "realm_041", "name": "大罗金仙", "description": "大罗道果，万法不侵", "level": 41, "experience_required": 74000, "breakthrough_probability": 10, "event_id": 1},
    {"id": "realm_042", "name": "仙王", "description": "仙界王者，执掌一方", "level": 42, "experience_required": 76000, "breakthrough_probability": 10, "event_id": 1},
    {"id": "realm_043", "name": "仙帝", "description": "仙界至尊，俯瞰众生", "level": 43, "experience_required": 78000, "breakthrough_probability": 10, "event_id": 1},
]


DEFAULT_SKILLS_DATA = [
    {"id": "skill_001", "name": "基础吐纳术", "description": "最基础的修炼功法", "skill_type": "cultivation", "realm_requirement": "realm_001", "experience_gain": 10, "damage": 0, "cooldown": 0},
    {"id": "skill_002", "name": "劈空掌", "description": "基础攻击技能", "skill_type": "combat", "realm_requirement": "realm_001", "experience_gain": 0, "damage": 15, "cooldown": 3},
    {"id": "skill_003", "name": "护体灵光", "description": "基础防御技能", "skill_type": "combat", "realm_requirement": "realm_001", "experience_gain": 0, "damage": 0, "cooldown": 5, "defense_bonus": 10},
    {"id": "skill_004", "name": "引气入体", "description": "引导灵气入体，加速修炼", "skill_type": "cultivation", "realm_requirement": "realm_002", "experience_gain": 20, "damage": 0, "cooldown": 0},
    {"id": "skill_005", "name": "灵气斩", "description": "凝聚灵气斩击敌人", "skill_type": "combat", "realm_requirement": "realm_003", "experience_gain": 0, "damage": 30, "cooldown": 4},
    {"id": "skill_006", "name": "聚灵诀", "description": "聚集灵气，提升修炼效率", "skill_type": "cultivation", "realm_requirement": "realm_005", "experience_gain": 50, "damage": 0, "cooldown": 0},
    {"id": "skill_007", "name": "金身诀", "description": "锻造金身，提升防御", "skill_type": "passive", "realm_requirement": "realm_006", "experience_gain": 0, "damage": 0, "cooldown": 0, "defense_bonus": 20},
    {"id": "skill_008", "name": "金丹真火", "description": "金丹期才能施展的真火攻击", "skill_type": "combat", "realm_requirement": "realm_010", "experience_gain": 0, "damage": 80, "cooldown": 6},
    {"id": "skill_009", "name": "元婴出窍", "description": "元婴期神通，神识攻击", "skill_type": "combat", "realm_requirement": "realm_014", "experience_gain": 0, "damage": 120, "cooldown": 8},
    {"id": "skill_010", "name": "化神诀", "description": "化神期修炼功法", "skill_type": "cultivation", "realm_requirement": "realm_018", "experience_gain": 200, "damage": 0, "cooldown": 0},
]


class CultivationService:
    """修炼服务类"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        config_manager: "ConfigManager" = None,
        json_data_manager: "JsonDataManager" = None,
        event_service: "EventService" = None,
    ):
        """
        初始化修炼服务

        Args:
            db_manager: 数据库管理器实例
            config_manager: 配置管理器实例
            json_data_manager: JSON数据管理器实例
            event_service: 事件服务实例(用于闭关奇遇)
        """
        self.db = db_manager
        self.config_manager = config_manager
        self.json_data_manager = json_data_manager
        self.event_service = event_service
        self._realms_cache: dict[str, Realm] = {}
        self._skills_cache: dict[str, Skill] = {}
        self._realms_loaded = False
        self._skills_loaded = False

    async def _ensure_realms_loaded(self):
        """确保境界数据已加载"""
        if not self._realms_loaded and self.json_data_manager:
            await self.json_data_manager.load_data("realms", DEFAULT_REALMS_DATA)
            all_realms = await self.json_data_manager.get_all("realms")
            self._realms_cache = {realm["id"]: Realm.from_dict(realm) for realm in all_realms}
            self._realms_loaded = True

    async def _ensure_skills_loaded(self):
        """确保功法数据已加载"""
        if not self._skills_loaded and self.json_data_manager:
            await self.json_data_manager.load_data("skills", DEFAULT_SKILLS_DATA)
            all_skills = await self.json_data_manager.get_all("skills")
            self._skills_cache = {skill["id"]: Skill.from_dict(skill) for skill in all_skills}
            self._skills_loaded = True

    async def _reload_realms_cache(self):
        """重新加载境界缓存"""
        if self.json_data_manager:
            await self.json_data_manager.reload("realms")
            all_realms = await self.json_data_manager.get_all("realms")
            self._realms_cache = {realm["id"]: Realm.from_dict(realm) for realm in all_realms}
        self._realms_loaded = True

    async def _reload_skills_cache(self):
        """重新加载功法缓存"""
        if self.json_data_manager:
            await self.json_data_manager.reload("skills")
            all_skills = await self.json_data_manager.get_all("skills")
            self._skills_cache = {skill["id"]: Skill.from_dict(skill) for skill in all_skills}
        self._skills_loaded = True

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
        if self.event_service:
            events_data = await self.event_service.get_active_events_by_trigger("seclusion")
            if not events_data:
                return None

            for event in events_data:
                if random.random() < event.probability:
                    event_id = event.id
                    event_name = event.name
                    event_desc = event.description
                    event_reward_type = event.reward_type
                    event_reward_value = event.reward_value

                    reward_message = ""
                    if event_reward_type == "item" and event_reward_value:
                        from ..services import InventoryService

                        inventory_svc = InventoryService(self.db, self.config_manager, self.json_data_manager)
                        item = await inventory_svc.get_item_by_id(str(event_reward_value))
                        if item:
                            await inventory_svc.add_item(player_id, item.id, 1)
                            reward_message = f"一道流光砸在你的洞府门前，竟是{event_desc}，你从中提炼出了【{item.name}】x1！"
                        else:
                            reward_message = f"{event_desc}"
                    elif event_reward_type == "spirit_stone":
                        value = event_reward_value
                        await self.db.execute(
                            "UPDATE players SET spirit_stone = spirit_stone + ? WHERE id = ?",
                            (value, player_id),
                        )
                        reward_message = f"{event_desc}，获得{value}灵石！"
                    elif event_reward_type == "experience":
                        value = event_reward_value
                        await self.db.execute(
                            "UPDATE players SET experience = experience + ? WHERE id = ?",
                            (value, player_id),
                        )
                        reward_message = f"{event_desc}，额外获得{value}点修为！"

                    return {
                        "event_id": event_id,
                        "event_name": event_name,
                        "message": reward_message,
                    }
        else:
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

                        inventory_svc = InventoryService(self.db, self.config_manager, self.json_data_manager)
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

    # ==================== 功法管理(使用JSON存储) ====================

    async def get_skill_by_id(self, skill_id: str) -> Skill | None:
        """根据ID获取功法"""
        await self._ensure_skills_loaded()
        return self._skills_cache.get(skill_id)

    async def get_all_skills(self) -> list[Skill]:
        """获取所有功法"""
        await self._ensure_skills_loaded()
        return list(self._skills_cache.values())

    async def create_skill(self, skill_data: dict[str, Any]) -> Skill:
        """创建功法"""
        await self._ensure_skills_loaded()
        new_skill = await self.json_data_manager.create("skills", skill_data)
        skill = Skill.from_dict(new_skill)
        self._skills_cache[skill.id] = skill
        return skill

    async def update_skill(self, skill_id: str, **kwargs) -> Skill | None:
        """更新功法"""
        await self._ensure_skills_loaded()
        updated = await self.json_data_manager.update("skills", skill_id, kwargs)
        if updated:
            skill = Skill.from_dict(updated)
            self._skills_cache[skill.id] = skill
            return skill
        return None

    async def delete_skill(self, skill_id: str) -> bool:
        """删除功法"""
        await self._ensure_skills_loaded()
        success = await self.json_data_manager.delete("skills", skill_id)
        if success and skill_id in self._skills_cache:
            del self._skills_cache[skill_id]
        return success

    # ==================== 境界管理(使用JSON存储) ====================

    async def get_realm_by_id(self, realm_id: str) -> Realm | None:
        """根据ID获取境界"""
        await self._ensure_realms_loaded()
        return self._realms_cache.get(realm_id)

    async def get_next_realm(self, current_level: int) -> Realm | None:
        """获取下一个境界"""
        await self._ensure_realms_loaded()
        for realm in self._realms_cache.values():
            if realm.level > current_level:
                return realm
        return None

    async def get_all_realms(self) -> list[Realm]:
        """获取所有境界"""
        await self._ensure_realms_loaded()
        return sorted(list(self._realms_cache.values()), key=lambda r: r.level)

    async def create_realm(self, realm_data: dict[str, Any]) -> Realm:
        """创建境界"""
        await self._ensure_realms_loaded()
        new_realm = await self.json_data_manager.create("realms", realm_data)
        realm = Realm.from_dict(new_realm)
        self._realms_cache[realm.id] = realm
        return realm

    async def update_realm(self, realm_id: str, **kwargs) -> Realm | None:
        """更新境界"""
        await self._ensure_realms_loaded()
        updated = await self.json_data_manager.update("realms", realm_id, kwargs)
        if updated:
            realm = Realm.from_dict(updated)
            self._realms_cache[realm.id] = realm
            return realm
        return None

    async def delete_realm(self, realm_id: str) -> bool:
        """删除境界"""
        await self._ensure_realms_loaded()
        success = await self.json_data_manager.delete("realms", realm_id)
        if success and realm_id in self._realms_cache:
            del self._realms_cache[realm_id]
        return success
