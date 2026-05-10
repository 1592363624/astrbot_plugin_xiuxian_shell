"""
深度闭关服务
处理深度闭关、避世入世、死亡惩罚等业务逻辑
"""

import asyncio
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from astrbot.api import logger

from ..database import DatabaseManager
from ..utils import utc_to_local

if TYPE_CHECKING:
    from ..config import ConfigManager
    from .cultivation_service import CultivationService


class DeepSeclusionService:
    """深度闭关服务类"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        config_manager: "ConfigManager" = None,
        cultivation_service: "CultivationService" = None,
    ):
        """
        初始化深度闭关服务

        Args:
            db_manager: 数据库管理器实例
            config_manager: 配置管理器实例
            cultivation_service: 修炼服务实例(用于获取境界信息)
        """
        self.db = db_manager
        self.config_manager = config_manager
        self.cultivation_service = cultivation_service
        # 避世/入世操作冷却时间戳缓存 {player_id: timestamp}
        self._peace_mode_cooldowns: dict[str, float] = {}

    async def restore_ongoing_seclusion_tasks(self):
        """
        恢复所有进行中的深度闭关定时任务

        Bot重启时调用，扫描数据库中status='ongoing'的记录，
        根据剩余时间重新创建定时任务。
        """
        ongoing_records = await self.db.fetch_all(
            "SELECT * FROM deep_seclusion_records WHERE status = 'ongoing'"
        )
        if not ongoing_records:
            logger.info("没有进行中的深度闭关记录需要恢复")
            return

        for record in ongoing_records:
            record_id = record["id"]
            player_id = record["player_id"]
            duration_hours = record["planned_duration_hours"]
            ended_at = datetime.fromisoformat(record["ended_at"])

            # 检查是否已过期（Bot离线期间闭关已结束）
            now = datetime.utcnow()
            if now >= ended_at:
                logger.info(f"深度闭关记录 {record_id} 在离线期间已到期，立即执行模拟")
                dao_heart = await self._check_dao_heart_broken(player_id)
                asyncio.create_task(
                    self._simulate_deep_seclusion(
                        record_id, player_id, duration_hours, dao_heart
                    )
                )
            else:
                remaining_seconds = (ended_at - now).total_seconds()
                logger.info(
                    f"恢复深度闭关定时任务，记录ID: {record_id}，剩余{remaining_seconds:.0f}秒"
                )
                dao_heart = await self._check_dao_heart_broken(player_id)
                asyncio.create_task(
                    self._schedule_deep_seclusion_simulation(
                        record_id, player_id, duration_hours, dao_heart, ended_at
                    )
                )

        logger.info(f"已恢复 {len(ongoing_records)} 个深度闭关定时任务")

    async def _get_death_penalty_config(self, key: str, default: str = None) -> str:
        """
        获取死亡惩罚配置值

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            str: 配置值
        """
        row = await self.db.fetch_one(
            "SELECT config_value FROM death_penalty_configs WHERE config_key = ?",
            (key,),
        )
        return row["config_value"] if row else default

    async def _get_death_penalty_config_float(
        self, key: str, default: float = 0.0
    ) -> float:
        """
        获取浮点型死亡惩罚配置

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            float: 配置值
        """
        value = await self._get_death_penalty_config(key)
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    async def _get_death_penalty_config_int(self, key: str, default: int = 0) -> int:
        """
        获取整型死亡惩罚配置

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            int: 配置值
        """
        value = await self._get_death_penalty_config(key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    # ==================== 深度闭关 ====================

    async def start_deep_seclusion(self, player_id: str) -> dict[str, Any]:
        """
        开启深度闭关

        开启一次长达8小时的自动挂机修炼，期间模拟多次普通闭关。
        每日仅可进行一次，冷却22小时。

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

        # 检查是否已有进行中的深度闭关
        ongoing = await self.db.fetch_one(
            "SELECT * FROM deep_seclusion_records WHERE player_id = ? AND status = 'ongoing'",
            (player_id,),
        )
        if ongoing:
            return {
                "success": False,
                "message": "你已在深度闭关中，请先完成当前闭关。",
            }

        # 检查冷却时间
        cooldown_hours = await self._get_death_penalty_config_int(
            "deep_seclusion_cooldown_hours", 22
        )
        last_record = await self.db.fetch_one(
            "SELECT ended_at FROM deep_seclusion_records WHERE player_id = ? AND status IN ('completed', 'early_ended') ORDER BY ended_at DESC LIMIT 1",
            (player_id,),
        )
        if last_record and last_record["ended_at"]:
            ended_at = datetime.fromisoformat(last_record["ended_at"])
            cooldown_until = ended_at + timedelta(hours=cooldown_hours)
            now = datetime.utcnow()
            if now < cooldown_until:
                remaining = cooldown_until - now
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                return {
                    "success": False,
                    "message": f"深度闭关尚在冷却中，还需{hours}小时{minutes}分钟方可再次开启。",
                }

        # 检查道心破碎状态（收益减半但不阻止闭关）
        dao_heart_penalty = await self._check_dao_heart_broken(player_id)

        # 创建深度闭关记录
        duration_hours = await self._get_death_penalty_config_int(
            "deep_seclusion_duration_hours", 8
        )
        now = datetime.utcnow()
        ended_at = now + timedelta(hours=duration_hours)
        record_id = str(uuid.uuid4())
        await self.db.execute(
            """INSERT INTO deep_seclusion_records
            (id, player_id, status, started_at, ended_at, planned_duration_hours, total_cycles, success_count, failure_count, possession_count, total_exp_change, is_settled)
            VALUES (?, ?, 'ongoing', ?, ?, ?, 0, 0, 0, 0, 0, 0)""",
            (
                record_id,
                player_id,
                now.isoformat(),
                ended_at.isoformat(),
                duration_hours,
            ),
        )
        await self.db.commit()

        # 启动定时任务，在ended_at到达时自动模拟闭关
        asyncio.create_task(
            self._schedule_deep_seclusion_simulation(
                record_id, player_id, duration_hours, dao_heart_penalty, ended_at
            )
        )

        ended_at_local = utc_to_local(ended_at)
        message_lines = [
            "【深度闭关】",
            f"你进入洞府，开启了一次长达{duration_hours}小时的深度闭关。",
            f"预计出关时间：{ended_at_local.strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        if dao_heart_penalty:
            message_lines.append("【状态影响】道心破碎，本次闭关收益减半。")
        message_lines.append("闭关结束后，下次发言时将自动结算。")

        logger.info(f"玩家 {player_id} 开启深度闭关，记录ID: {record_id}")

        return {
            "success": True,
            "record_id": record_id,
            "planned_duration": duration_hours,
            "dao_heart_penalty": dao_heart_penalty,
            "message": "\n".join(message_lines),
        }

    async def _schedule_deep_seclusion_simulation(
        self,
        record_id: str,
        player_id: str,
        duration_hours: int,
        dao_heart_penalty: bool,
        ended_at: datetime,
    ):
        """
        定时任务：在深度闭关结束时执行模拟

        Args:
            record_id: 深度闭关记录ID
            player_id: 玩家ID
            duration_hours: 闭关时长（小时）
            dao_heart_penalty: 是否有道心破碎惩罚
            ended_at: 预计结束时间
        """
        now = datetime.utcnow()
        wait_seconds = (ended_at - now).total_seconds()
        if wait_seconds > 0:
            logger.info(
                f"深度闭关定时任务启动，记录ID: {record_id}，等待{wait_seconds:.0f}秒后执行模拟"
            )
            await asyncio.sleep(wait_seconds)

        # 检查记录是否仍为ongoing（可能被强行出关中断了）
        record = await self.db.fetch_one(
            "SELECT status FROM deep_seclusion_records WHERE id = ?",
            (record_id,),
        )
        if not record or record["status"] != "ongoing":
            logger.info(f"深度闭关记录 {record_id} 状态已变更，跳过模拟")
            return

        # 执行模拟
        await self._simulate_deep_seclusion(
            record_id, player_id, duration_hours, dao_heart_penalty
        )
        logger.info(f"深度闭关记录 {record_id} 模拟完成，等待玩家发言结算")

    async def _simulate_deep_seclusion(
        self,
        record_id: str,
        player_id: str,
        duration_hours: int,
        dao_heart_penalty: bool,
    ) -> dict[str, Any]:
        """
        模拟深度闭关过程

        模拟每小时2-6次普通闭关，计算总收益。

        Args:
            record_id: 深度闭关记录ID
            player_id: 玩家ID
            duration_hours: 闭关时长（小时）
            dao_heart_penalty: 是否有道心破碎惩罚

        Returns:
            Dict[str, Any]: 模拟结果
        """
        # 获取玩家当前境界用于计算修为
        player = await self.db.fetch_one(
            "SELECT realm_id FROM players WHERE id = ?",
            (player_id,),
        )
        if not player:
            return {"success": False, "message": "玩家不存在"}

        base_exp = 0
        if self.cultivation_service:
            exp_cap = await self.cultivation_service.get_exp_cap_for_realm(player["realm_id"])
            base_exp = exp_cap if exp_cap > 0 else 0
            if base_exp == 0:
                realm = await self.cultivation_service.get_realm_by_id(player["realm_id"])
                if realm:
                    base_exp = realm.experience_required

        # 获取闭关配置
        seclusion_cfg = {}
        if self.config_manager:
            seclusion_cfg = self.config_manager.get("seclusion", {})

        success_prob = seclusion_cfg.get("success_probability", 0.60)
        failure_prob = seclusion_cfg.get("failure_probability", 0.25)
        exp_ratio_min = seclusion_cfg.get("exp_ratio_min", 0.001)
        exp_ratio_max = seclusion_cfg.get("exp_ratio_max", 0.001)
        possession_exp_ratio = seclusion_cfg.get("possession_exp_ratio", 0.001)

        total_cycles = 0
        success_count = 0
        failure_count = 0
        possession_count = 0
        total_exp_change = 0

        # 模拟每小时2-6次闭关
        for _ in range(duration_hours):
            cycles_this_hour = random.randint(2, 6)
            for _ in range(cycles_this_hour):
                total_cycles += 1
                roll = random.random()
                if roll < success_prob:
                    success_count += 1
                    ratio = random.uniform(exp_ratio_min, exp_ratio_max)
                    exp_change = max(1, int(base_exp * ratio))
                elif roll < success_prob + failure_prob:
                    failure_count += 1
                    ratio = random.uniform(exp_ratio_min, exp_ratio_max)
                    exp_change = -max(1, int(base_exp * ratio))
                else:
                    possession_count += 1
                    exp_change = -max(1, int(base_exp * possession_exp_ratio))

                total_exp_change += exp_change

        # 应用道心破碎惩罚
        if dao_heart_penalty:
            penalty_rate = await self._get_death_penalty_config_float(
                "dao_heart_exp_penalty_rate", 0.5
            )
            total_exp_change = int(total_exp_change * penalty_rate)

        # 更新记录为已完成（但不结算）
        now = datetime.utcnow()
        await self.db.execute(
            """UPDATE deep_seclusion_records
            SET total_cycles = ?,
                success_count = ?,
                failure_count = ?,
                possession_count = ?,
                total_exp_change = ?,
                status = 'completed',
                ended_at = ?
            WHERE id = ?""",
            (
                total_cycles,
                success_count,
                failure_count,
                possession_count,
                total_exp_change,
                now.isoformat(),
                record_id,
            ),
        )
        await self.db.commit()

        return {
            "success": True,
            "total_cycles": total_cycles,
            "success_count": success_count,
            "failure_count": failure_count,
            "possession_count": possession_count,
            "total_exp_change": total_exp_change,
        }

    async def get_deep_seclusion_status(self, player_id: str) -> dict[str, Any]:
        """
        查看深度闭关状态

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 闭关状态
        """
        ongoing = await self.db.fetch_one(
            "SELECT * FROM deep_seclusion_records WHERE player_id = ? AND status = 'ongoing'",
            (player_id,),
        )
        if ongoing:
            started_at = datetime.fromisoformat(ongoing["started_at"])
            now = datetime.utcnow()
            elapsed = now - started_at
            elapsed_hours = elapsed.total_seconds() / 3600
            planned = ongoing["planned_duration_hours"]
            remaining = max(0, planned - elapsed_hours)

            return {
                "in_seclusion": True,
                "status": "ongoing",
                "elapsed_hours": round(elapsed_hours, 1),
                "remaining_hours": round(remaining, 1),
                "planned_duration": planned,
                "message": f"你正在深度闭关中，已进行{round(elapsed_hours, 1)}小时，剩余约{round(remaining, 1)}小时。",
            }

        # 检查是否有未结算的已完成闭关
        unsettled = await self.db.fetch_one(
            "SELECT * FROM deep_seclusion_records WHERE player_id = ? AND status = 'completed' AND is_settled = 0 ORDER BY ended_at DESC LIMIT 1",
            (player_id,),
        )
        if unsettled:
            return {
                "in_seclusion": False,
                "status": "completed_unsettled",
                "record": dict(unsettled),
                "message": "你的深度闭关已结束，下次发言时将自动结算。",
            }

        # 检查冷却
        cooldown_hours = await self._get_death_penalty_config_int(
            "deep_seclusion_cooldown_hours", 22
        )
        last_record = await self.db.fetch_one(
            "SELECT ended_at FROM deep_seclusion_records WHERE player_id = ? AND status IN ('completed', 'early_ended') ORDER BY ended_at DESC LIMIT 1",
            (player_id,),
        )
        if last_record and last_record["ended_at"]:
            ended_at = datetime.fromisoformat(last_record["ended_at"])
            cooldown_until = ended_at + timedelta(hours=cooldown_hours)
            now = datetime.utcnow()
            if now < cooldown_until:
                remaining = cooldown_until - now
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                return {
                    "in_seclusion": False,
                    "status": "cooldown",
                    "remaining_hours": hours,
                    "remaining_minutes": minutes,
                    "message": f"深度闭关冷却中，还需{hours}小时{minutes}分钟。",
                }

        return {
            "in_seclusion": False,
            "status": "ready",
            "message": "你目前可以进行深度闭关。",
        }

    async def force_end_deep_seclusion(self, player_id: str) -> dict[str, Any]:
        """
        强行出关

        提前结束深度闭关，但收益大打折扣（50%）。

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 出关结果
        """
        ongoing = await self.db.fetch_one(
            "SELECT * FROM deep_seclusion_records WHERE player_id = ? AND status = 'ongoing'",
            (player_id,),
        )
        if not ongoing:
            return {
                "success": False,
                "message": "你当前不在深度闭关中。",
            }

        # 应用强行出关惩罚
        penalty_rate = await self._get_death_penalty_config_float(
            "deep_seclusion_early_end_penalty_rate", 0.5
        )

        # 重新计算实际收益（基于已过时间的比例）
        started_at = datetime.fromisoformat(ongoing["started_at"])
        now = datetime.utcnow()
        elapsed_hours = (now - started_at).total_seconds() / 3600
        planned_hours = ongoing["planned_duration_hours"]
        progress_ratio = (
            min(1.0, elapsed_hours / planned_hours) if planned_hours > 0 else 0
        )

        # 获取已模拟的结果（如果已经模拟完成）
        total_exp = ongoing["total_exp_change"]
        if total_exp == 0:
            # 如果还没模拟，先模拟
            dao_heart = await self._check_dao_heart_broken(player_id)
            sim_result = await self._simulate_deep_seclusion(
                ongoing["id"], player_id, planned_hours, dao_heart
            )
            total_exp = sim_result["total_exp_change"]

        # 应用进度比例和强行出关惩罚
        actual_exp = int(total_exp * progress_ratio * penalty_rate)

        # 更新记录为强行出关
        await self.db.execute(
            """UPDATE deep_seclusion_records
            SET status = 'early_ended',
                ended_at = ?,
                total_exp_change = ?,
                is_settled = 1
            WHERE id = ?""",
            (now.isoformat(), actual_exp, ongoing["id"]),
        )

        # 应用修为变化
        await self.db.execute(
            "UPDATE players SET experience = MAX(0, experience + ?), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (actual_exp, player_id),
        )
        await self.db.commit()

        message_lines = [
            "【强行出关】",
            "你强行中断了深度闭关，收益大打折扣！",
            f"本次闭关进行了约{round(elapsed_hours, 1)}小时（计划{planned_hours}小时）",
            f"由于强行出关，仅获得{int(penalty_rate * 100)}%收益。",
        ]
        if actual_exp >= 0:
            message_lines.append(f"你的修为最终增加了{actual_exp}点。")
        else:
            message_lines.append(f"你的修为最终减少了{abs(actual_exp)}点。")

        logger.info(f"玩家 {player_id} 强行出关，获得修为: {actual_exp}")

        return {
            "success": True,
            "actual_exp_change": actual_exp,
            "message": "\n".join(message_lines),
        }

    async def settle_deep_seclusion(self, player_id: str) -> dict[str, Any] | None:
        """
        结算深度闭关

        在玩家下次发言时自动调用，应用修为变化。

        Args:
            player_id: 玩家ID

        Returns:
            Optional[Dict[str, Any]]: 结算结果，无未结算记录返回None
        """
        record = await self.db.fetch_one(
            "SELECT * FROM deep_seclusion_records WHERE player_id = ? AND status = 'completed' AND is_settled = 0 ORDER BY ended_at DESC LIMIT 1",
            (player_id,),
        )
        if not record:
            return None

        total_exp = record["total_exp_change"]

        # 应用修为变化
        await self.db.execute(
            "UPDATE players SET experience = MAX(0, experience + ?), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (total_exp, player_id),
        )

        # 标记为已结算
        await self.db.execute(
            "UPDATE deep_seclusion_records SET is_settled = 1 WHERE id = ?",
            (record["id"],),
        )
        await self.db.commit()

        # 构建结算消息
        duration_hours = record["planned_duration_hours"]
        total_cycles = record["total_cycles"]
        success_count = record["success_count"]
        failure_count = record["failure_count"]
        possession_count = record["possession_count"]

        message_lines = [
            "【深度闭关总结】",
            f"本次结算时长：{duration_hours}小时（基础上限{duration_hours}小时）",
            f"神魂吐纳次数：{total_cycles}周天",
            f"-修行有成：{success_count}次",
            f"-心神不宁：{failure_count}次",
            f"-走火入魔：{possession_count}次",
        ]
        if total_exp >= 0:
            message_lines.append(f"本次深度闭关，你的修为最终增加了{total_exp}点！")
        else:
            message_lines.append(
                f"本次深度闭关，你的修为最终减少了{abs(total_exp)}点！"
            )

        logger.info(f"玩家 {player_id} 深度闭关结算，修为变化: {total_exp}")

        return {
            "success": True,
            "total_exp_change": total_exp,
            "message": "\n".join(message_lines),
        }

    # ==================== 避世/入世 ====================

    async def enter_peace_mode(self, player_id: str) -> dict[str, Any]:
        """
        开启避世模式（和平模式）

        仅限炼气期修士。在此状态下无法被攻击，也无法攻击他人。

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 操作结果
        """
        # 检查避世/入世操作冷却
        cooldown_check = self._check_peace_mode_cooldown(player_id)
        if cooldown_check:
            return cooldown_check

        player = await self.db.fetch_one(
            "SELECT * FROM players WHERE id = ?",
            (player_id,),
        )
        if not player:
            raise ValueError("玩家不存在")

        realm = None
        if self.cultivation_service:
            realm = await self.cultivation_service.get_realm_by_id(player["realm_id"])

        realm_level = realm.level if realm and hasattr(realm, 'level') else player.get("realm_level", 1)
        realm_name = realm.name if realm and hasattr(realm, 'name') else player.get("realm_name", "未知")

        # 检查是否为炼气期（realm_001 凡人/炼气）
        if realm_level > 1:
            return {
                "success": False,
                "message": f"你已达到【{realm_name}】，红尘历练才是正道，无法避世。",
            }

        # 检查是否已在避世状态
        existing = await self._get_active_state(player_id, "peace_mode")
        if existing:
            return {
                "success": False,
                "message": "你已在避世状态中，无需重复开启。",
            }

        # 记录操作时间戳（用于冷却）
        self._peace_mode_cooldowns[player_id] = time.time()

        # 创建避世状态记录
        now = datetime.utcnow()
        state_id = str(uuid.uuid4())
        await self.db.execute(
            """INSERT INTO player_states
            (id, player_id, state_type, started_at, is_active)
            VALUES (?, ?, 'peace_mode', ?, 1)""",
            (state_id, player_id, now.isoformat()),
        )
        await self.db.commit()

        logger.info(f"玩家 {player_id} 开启避世模式")

        return {
            "success": True,
            "message": (
                "【避世】\n"
                "你寻得一处清幽洞府，开启了避世模式。\n"
                "在此期间，你无法被他人攻击，自己也无法攻击他人。\n"
                "待你想重返红尘时，可使用<入世>指令。"
            ),
        }

    async def exit_peace_mode(self, player_id: str) -> dict[str, Any]:
        """
        关闭避世模式（入世）

        重返红尘纷争。

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 操作结果
        """
        # 检查避世/入世操作冷却
        cooldown_check = self._check_peace_mode_cooldown(player_id)
        if cooldown_check:
            return cooldown_check

        player = await self.db.fetch_one(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        )
        if not player:
            raise ValueError("玩家不存在")

        # 查找并关闭避世状态
        existing = await self._get_active_state(player_id, "peace_mode")
        if not existing:
            return {
                "success": False,
                "message": "你当前不在避世状态中。",
            }

        # 记录操作时间戳（用于冷却）
        self._peace_mode_cooldowns[player_id] = time.time()

        now = datetime.utcnow()
        await self.db.execute(
            """UPDATE player_states
            SET is_active = 0, expires_at = ?
            WHERE id = ?""",
            (now.isoformat(), existing["id"]),
        )
        await self.db.commit()

        logger.info(f"玩家 {player_id} 关闭避世模式")

        return {
            "success": True,
            "message": (
                "【入世】\n"
                "你收起洞府禁制，重返红尘纷争。\n"
                "修仙之路本就逆天而行，该来的终究会来。"
            ),
        }

    def _check_peace_mode_cooldown(self, player_id: str) -> dict[str, Any] | None:
        """
        检查避世/入世操作冷却

        Args:
            player_id: 玩家ID

        Returns:
            Optional[Dict[str, Any]]: 如果在冷却中返回错误信息，否则返回None
        """
        last_time = self._peace_mode_cooldowns.get(player_id)
        if last_time is not None:
            cooldown_seconds = 60  # 1分钟冷却
            elapsed = time.time() - last_time
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                return {
                    "success": False,
                    "message": f"操作太频繁，请 {remaining} 秒后再试。",
                }
        return None

    async def is_in_peace_mode(self, player_id: str) -> bool:
        """
        检查玩家是否在避世模式中

        Args:
            player_id: 玩家ID

        Returns:
            bool: 是否在避世模式
        """
        state = await self._get_active_state(player_id, "peace_mode")
        return state is not None

    # ==================== 死亡惩罚（败者之殇） ====================

    async def apply_death_penalty(self, loser_id: str) -> dict[str, Any]:
        """
        对败者应用死亡惩罚

        惩罚内容：
        1. 境界跌落：大境界直接跌落一重
        2. 宝物遗失：50%材料掉落 + 随机装备掉落
        3. 道心破碎：24小时状态，闭关收益减半，无法主动斗法

        Args:
            loser_id: 败者玩家ID

        Returns:
            Dict[str, Any]: 惩罚结果
        """
        player = await self.db.fetch_one(
            "SELECT * FROM players WHERE id = ?",
            (loser_id,),
        )
        if not player:
            raise ValueError("玩家不存在")

        message_lines = ["【败者之殇】"]
        penalty_details = []

        # 1. 境界跌落
        realm_dropped = await self._drop_realm(loser_id)
        if realm_dropped:
            message_lines.append(
                f"境界跌落：从【{realm_dropped['old_realm']}】跌回【{realm_dropped['new_realm']}】"
            )
            penalty_details.append({"type": "realm_drop", "data": realm_dropped})
        else:
            message_lines.append("境界跌落：你已在最低境界，无法再跌。")

        # 2. 宝物遗失
        item_loss = await self._drop_items(loser_id)
        if item_loss:
            drop_msg = item_loss.get("message", "")
            if drop_msg:
                message_lines.append(drop_msg)
            penalty_details.append({"type": "item_loss", "data": item_loss})

        # 3. 道心破碎
        dao_heart = await self._apply_dao_heart_broken(loser_id)
        message_lines.append(
            f"道心破碎：获得持续{dao_heart['duration_hours']}小时的【道心破碎】状态"
        )
        message_lines.append("期间所有闭关收益减半，且无法主动向他人发起斗法。")
        penalty_details.append({"type": "dao_heart_broken", "data": dao_heart})

        logger.info(f"玩家 {loser_id} 受到死亡惩罚")

        return {
            "success": True,
            "penalty_details": penalty_details,
            "message": "\n".join(message_lines),
        }

    async def _drop_realm(self, player_id: str) -> dict[str, Any] | None:
        """
        境界跌落一重

        最低跌至炼气一层（realm_001）。

        Args:
            player_id: 玩家ID

        Returns:
            Optional[Dict[str, Any]]: 跌落结果，已在最低境界返回None
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
        if current_level <= 1:
            return None

        # 获取前一个境界
        prev_realm = None
        prev_realm_dict = None
        if self.cultivation_service:
            all_realms = await self.cultivation_service.get_all_realms()
            for realm in all_realms:
                if realm.level < current_level:
                    if prev_realm is None or realm.level > prev_realm.level:
                        prev_realm = realm
                        prev_realm_dict = realm.to_dict() if hasattr(realm, 'to_dict') else realm

        if not prev_realm_dict:
            return None

        from ..utils.attributes import calc_battle_attrs

        new_attrs = calc_battle_attrs(
            level=prev_realm_dict["level"],
            bone=player["bone"],
            spirit=player["spirit"],
            intel=player["intel"],
            str_=player["str"],
            percep=player["percep"],
            luck=player["luck"],
        )

        await self.db.execute(
            """UPDATE players
            SET realm_id = ?,
                experience = 0,
                health = ?,
                mp = ?,
                stamina = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?""",
            (
                prev_realm_dict["id"],
                new_attrs["max_health"],
                new_attrs["max_mp"],
                new_attrs["max_stamina"],
                player_id,
            ),
        )
        await self.db.commit()

        return {
            "old_realm": player["realm_name"],
            "new_realm": prev_realm_dict["name"],
            "old_level": current_level,
            "new_level": prev_realm_dict["level"],
        }

    async def _drop_items(self, player_id: str) -> dict[str, Any]:
        """
        掉落物品

        掉落50%的材料和指定数量的随机装备。

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 掉落结果
        """
        material_drop_rate = await self._get_death_penalty_config_float(
            "material_drop_rate", 0.5
        )
        equipment_drop_count = await self._get_death_penalty_config_int(
            "equipment_drop_count", 1
        )

        dropped_items = []

        # 获取材料类物品
        materials = await self.db.fetch_all(
            """SELECT pi.*, i.name, i.item_type
            FROM player_inventory pi
            JOIN items i ON pi.item_id = i.id
            WHERE pi.player_id = ? AND i.item_type = 'material'""",
            (player_id,),
        )

        for mat in materials:
            drop_qty = max(1, int(mat["quantity"] * material_drop_rate))
            if drop_qty >= mat["quantity"]:
                # 全部删除
                await self.db.execute(
                    "DELETE FROM player_inventory WHERE id = ?", (mat["id"],)
                )
            else:
                await self.db.execute(
                    "UPDATE player_inventory SET quantity = quantity - ? WHERE id = ?",
                    (drop_qty, mat["id"]),
                )
            dropped_items.append(
                {"name": mat["name"], "quantity": drop_qty, "type": "material"}
            )

        # 获取装备类物品（排除已绑定的本命法宝，假设绑定标记为特定字段或名称）
        equipments = await self.db.fetch_all(
            """SELECT pi.*, i.name, i.item_type
            FROM player_inventory pi
            JOIN items i ON pi.item_id = i.id
            WHERE pi.player_id = ? AND i.item_type = 'equipment'
            AND i.name NOT LIKE '%本命%'""",
            (player_id,),
        )

        if equipments:
            # 随机选择指定数量的装备
            drop_count = min(equipment_drop_count, len(equipments))
            selected = random.sample(equipments, drop_count)
            for eq in selected:
                await self.db.execute(
                    "DELETE FROM player_inventory WHERE id = ?", (eq["id"],)
                )
                dropped_items.append(
                    {"name": eq["name"], "quantity": 1, "type": "equipment"}
                )

        await self.db.commit()

        # 构建消息
        if dropped_items:
            material_drops = [
                f"【{d['name']}】x{d['quantity']}"
                for d in dropped_items
                if d["type"] == "material"
            ]
            equip_drops = [
                f"【{d['name']}】" for d in dropped_items if d["type"] == "equipment"
            ]

            msg_parts = []
            if material_drops:
                msg_parts.append(f"储物袋中50%的材料遗失：{', '.join(material_drops)}")
            if equip_drops:
                msg_parts.append(f"随机法宝掉落：{', '.join(equip_drops)}")

            return {
                "dropped_items": dropped_items,
                "message": "宝物遗失：" + "；".join(msg_parts),
            }

        return {
            "dropped_items": [],
            "message": "宝物遗失：你储物袋中空空如也，并无宝物可遗失。",
        }

    async def _apply_dao_heart_broken(self, player_id: str) -> dict[str, Any]:
        """
        应用道心破碎状态

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 状态信息
        """
        duration_hours = await self._get_death_penalty_config_int(
            "dao_heart_broken_duration_hours", 24
        )

        now = datetime.utcnow()
        expires_at = now + timedelta(hours=duration_hours)

        # 先清除旧的道心破碎状态
        await self.db.execute(
            "UPDATE player_states SET is_active = 0 WHERE player_id = ? AND state_type = 'dao_heart_broken'",
            (player_id,),
        )

        state_id = str(uuid.uuid4())
        await self.db.execute(
            """INSERT INTO player_states
            (id, player_id, state_type, started_at, expires_at, is_active)
            VALUES (?, ?, 'dao_heart_broken', ?, ?, 1)""",
            (state_id, player_id, now.isoformat(), expires_at.isoformat()),
        )
        await self.db.commit()

        return {
            "state_id": state_id,
            "duration_hours": duration_hours,
            "expires_at": expires_at.isoformat(),
        }

    async def _check_dao_heart_broken(self, player_id: str) -> bool:
        """
        检查玩家是否有道心破碎状态

        Args:
            player_id: 玩家ID

        Returns:
            bool: 是否有道心破碎状态
        """
        state = await self._get_active_state(player_id, "dao_heart_broken")
        return state is not None

    async def _get_active_state(
        self, player_id: str, state_type: str
    ) -> dict[str, Any] | None:
        """
        获取玩家的生效状态

        Args:
            player_id: 玩家ID
            state_type: 状态类型

        Returns:
            Optional[Dict[str, Any]]: 状态记录，不存在返回None
        """
        now = datetime.utcnow()
        row = await self.db.fetch_one(
            """SELECT * FROM player_states
            WHERE player_id = ? AND state_type = ? AND is_active = 1
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC LIMIT 1""",
            (player_id, state_type, now.isoformat()),
        )
        return dict(row) if row else None

    async def can_initiate_combat(self, player_id: str) -> dict[str, Any]:
        """
        检查玩家是否可以主动发起斗法

        道心破碎状态下无法主动发起斗法。

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 检查结果
        """
        if await self._check_dao_heart_broken(player_id):
            return {
                "can_initiate": False,
                "reason": "你正处于【道心破碎】状态，无法主动向他人发起斗法。",
            }

        if await self.is_in_peace_mode(player_id):
            return {
                "can_initiate": False,
                "reason": "你正处于【避世】状态，无法向他人发起斗法。",
            }

        return {"can_initiate": True}

    async def can_be_attacked(self, player_id: str) -> bool:
        """
        检查玩家是否可以被攻击

        避世状态下无法被攻击。

        Args:
            player_id: 玩家ID

        Returns:
            bool: 是否可以被攻击
        """
        return not await self.is_in_peace_mode(player_id)

    async def get_player_states(self, player_id: str) -> list[dict[str, Any]]:
        """
        获取玩家所有生效状态

        Args:
            player_id: 玩家ID

        Returns:
            List[Dict[str, Any]]: 状态列表
        """
        now = datetime.utcnow()
        rows = await self.db.fetch_all(
            """SELECT * FROM player_states
            WHERE player_id = ? AND is_active = 1
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC""",
            (player_id, now.isoformat()),
        )
        return [dict(r) for r in rows]

    async def cleanup_expired_states(self):
        """
        清理过期的玩家状态
        """
        now = datetime.utcnow()
        await self.db.execute(
            """UPDATE player_states
            SET is_active = 0
            WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?""",
            (now.isoformat(),),
        )
        await self.db.commit()
