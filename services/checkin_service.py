"""
签到服务
处理每日签到、连续签到天数计算、修为奖励发放等业务逻辑
"""

import uuid
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from astrbot.api import logger

from ..database import DatabaseManager
from ..utils import bj_now_iso, bj_today_str

if TYPE_CHECKING:
    from ..config import ConfigManager
    from .cultivation_service import CultivationService


class CheckinService:
    """签到服务类"""

    def __init__(self, db_manager: DatabaseManager, config_manager: "ConfigManager", cultivation_service: "CultivationService" = None):
        """
        初始化签到服务

        Args:
            db_manager: 数据库管理器实例
            config_manager: 配置管理器实例
            cultivation_service: 修炼服务实例(用于获取境界信息)
        """
        self.db = db_manager
        self.config_manager = config_manager
        self.cultivation_service = cultivation_service

    def _get_reward_rate(self, consecutive_days: int) -> int:
        """
        根据连续签到天数获取奖励百分比

        Args:
            consecutive_days: 连续签到天数

        Returns:
            int: 奖励百分比（如 1 表示 1%）
        """
        checkin_cfg = self.config_manager.get("checkin", {})
        seven_day_rate = checkin_cfg.get("seven_day_reward_rate", 3)
        three_day_rate = checkin_cfg.get("three_day_reward_rate", 2)
        base_rate = checkin_cfg.get("base_reward_rate", 1)

        if consecutive_days >= 7:
            return seven_day_rate
        elif consecutive_days >= 3:
            return three_day_rate
        return base_rate

    async def _calculate_reward(self, player_id: str, consecutive_days: int) -> int:
        """
        计算签到奖励修为值
        奖励 = 当前境界升级所需修为(下一境界experience_required) × 奖励百分比

        Args:
            player_id: 玩家ID
            consecutive_days: 连续签到天数

        Returns:
            int: 奖励修为值（至少为1）
        """
        # 获取玩家当前境界
        player = await self.db.fetch_one(
            "SELECT realm_id FROM players WHERE id = ?", (player_id,)
        )
        if not player:
            return 0

        # 获取当前境界等级
        current_realm_level = 1
        current_exp_required = 100
        if self.cultivation_service:
            realm = await self.cultivation_service.get_realm_by_id(player["realm_id"])
            if realm:
                current_realm_level = realm.level
                current_exp_required = realm.experience_required

        # 获取下一境界的 experience_required（即升级所需修为）
        next_exp = 0
        if self.cultivation_service:
            next_realm = await self.cultivation_service.get_next_realm(current_realm_level)
            if next_realm:
                next_exp = next_realm.experience_required

        # 已达最高境界时，使用当前境界自身 experience_required 作为基准
        base_exp = next_exp if next_exp > 0 else current_exp_required

        # 按百分比计算奖励，至少为1
        rate = self._get_reward_rate(consecutive_days)
        reward = max(1, int(base_exp * rate / 100))
        return reward

    async def _get_last_checkin(self, player_id: str) -> dict[str, Any] | None:
        """
        获取玩家最近一次签到记录

        Args:
            player_id: 玩家ID

        Returns:
            Optional[Dict]: 最近一次签到记录或 None
        """
        return await self.db.fetch_one(
            "SELECT * FROM checkin_records WHERE player_id = ? ORDER BY checkin_date DESC LIMIT 1",
            (player_id,),
        )

    async def _calc_consecutive_days(self, player_id: str) -> int:
        """
        计算当前应累加的连续签到天数
        如果最后签到日期是昨天，则连续天数 +1；否则重置为 1

        Args:
            player_id: 玩家ID

        Returns:
            int: 连续签到天数
        """
        last_record = await self._get_last_checkin(player_id)
        if not last_record:
            return 1

        today = date.fromisoformat(bj_today_str())
        last_date = date.fromisoformat(last_record["checkin_date"])
        yesterday = today - timedelta(days=1)

        # 上次签到是昨天，连续天数累加
        if last_date == yesterday:
            return last_record["consecutive_days"] + 1
        # 上次签到是今天（理论上不会走到这，因为外层已判断）
        elif last_date == today:
            return last_record["consecutive_days"]
        # 断签，重置为1
        return 1

    async def checkin(self, player_id: str) -> dict[str, Any]:
        """
        执行每日签到

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 签到结果，包含 success、message、exp_reward、consecutive_days 等
        """
        today_str = bj_today_str()

        # 检查今天是否已签到
        existing = await self.db.fetch_one(
            "SELECT id FROM checkin_records WHERE player_id = ? AND checkin_date = ?",
            (player_id, today_str),
        )
        if existing:
            return {
                "success": False,
                "message": "你今天已经签到过了，明天再来吧",
            }

        # 计算连续签到天数
        consecutive_days = await self._calc_consecutive_days(player_id)

        # 计算奖励修为
        exp_reward = await self._calculate_reward(player_id, consecutive_days)

        # 写入签到记录
        record_id = str(uuid.uuid4())
        await self.db.execute(
            """INSERT INTO checkin_records (id, player_id, checkin_date, consecutive_days, exp_reward)
            VALUES (?, ?, ?, ?, ?)""",
            (record_id, player_id, today_str, consecutive_days, exp_reward),
        )

        # 发放修为奖励，通过统一入口处理截断和溢出
        if self.cultivation_service:
            await self.cultivation_service.add_experience(player_id, exp_reward)
        else:
            await self.db.execute(
                "UPDATE players SET experience = experience + ?, updated_at = ? WHERE id = ?",
                (exp_reward, bj_now_iso(), player_id),
            )
            await self.db.commit()

        logger.info(
            f"玩家 {player_id} 签到成功，连续 {consecutive_days} 天，获得 {exp_reward} 修为"
        )

        # 确定奖励等级描述
        rate = self._get_reward_rate(consecutive_days)
        if consecutive_days >= 7:
            tier_desc = "连续7天"
        elif consecutive_days >= 3:
            tier_desc = "连续3天"
        else:
            tier_desc = "每日"

        return {
            "success": True,
            "consecutive_days": consecutive_days,
            "exp_reward": exp_reward,
            "reward_rate": rate,
            "tier_desc": tier_desc,
            "message": (
                f"签到成功！\n"
                f"连续签到：{consecutive_days} 天\n"
                f"奖励等级：{tier_desc}（{rate}%）\n"
                f"获得修为：+{exp_reward}"
            ),
        }

    async def get_checkin_status(self, player_id: str) -> dict[str, Any]:
        """
        查询玩家签到状态（今日是否签到、连续天数等）

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: 签到状态信息
        """
        today_str = bj_today_str()

        # 查询今日签到记录
        today_record = await self.db.fetch_one(
            "SELECT * FROM checkin_records WHERE player_id = ? AND checkin_date = ?",
            (player_id, today_str),
        )

        # 查询最近一条记录获取连续天数
        last_record = await self._get_last_checkin(player_id)

        checked_in_today = today_record is not None
        consecutive_days = last_record["consecutive_days"] if last_record else 0

        # 获取各档奖励百分比
        checkin_cfg = self.config_manager.get("checkin", {})

        return {
            "checked_in_today": checked_in_today,
            "consecutive_days": consecutive_days,
            "last_checkin_date": last_record["checkin_date"] if last_record else None,
            "last_exp_reward": last_record["exp_reward"] if last_record else 0,
            "reward_tiers": {
                "base": checkin_cfg.get("base_reward_rate", 1),
                "three_day": checkin_cfg.get("three_day_reward_rate", 2),
                "seven_day": checkin_cfg.get("seven_day_reward_rate", 3),
            },
        }

    async def get_player_checkin_records(
        self, player_id: str, limit: int = 30
    ) -> list[dict[str, Any]]:
        """
        获取玩家近期签到记录

        Args:
            player_id: 玩家ID
            limit: 返回记录数量上限

        Returns:
            List[Dict]: 签到记录列表
        """
        rows = await self.db.fetch_all(
            "SELECT * FROM checkin_records WHERE player_id = ? ORDER BY checkin_date DESC LIMIT ?",
            (player_id, limit),
        )
        return rows

    async def get_checkin_ranking(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        获取签到排行（按连续签到天数排序）

        Args:
            limit: 返回数量上限

        Returns:
            List[Dict]: 排行数据
        """
        rows = await self.db.fetch_all(
            """SELECT cr.player_id, p.username, cr.consecutive_days, cr.checkin_date, cr.exp_reward
            FROM checkin_records cr
            JOIN players p ON cr.player_id = p.id
            WHERE cr.checkin_date = (SELECT MAX(checkin_date) FROM checkin_records WHERE player_id = cr.player_id)
            ORDER BY cr.consecutive_days DESC
            LIMIT ?""",
            (limit,),
        )
        return rows

    async def get_all_checkin_records(
        self, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        """
        获取所有签到记录（分页，后台管理用）

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            Dict[str, Any]: 包含记录列表和分页信息
        """
        offset = (page - 1) * page_size
        count_result = await self.db.fetch_one(
            "SELECT COUNT(*) as total FROM checkin_records"
        )
        total = count_result["total"] if count_result else 0

        rows = await self.db.fetch_all(
            """SELECT cr.*, p.username
            FROM checkin_records cr
            JOIN players p ON cr.player_id = p.id
            ORDER BY cr.created_at DESC
            LIMIT ? OFFSET ?""",
            (page_size, offset),
        )

        return {
            "records": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
