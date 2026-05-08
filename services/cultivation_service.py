"""
修炼服务
处理修炼、功法、境界突破等业务逻辑
"""
import uuid
from typing import Optional, List, Dict, Any
from astrbot.api import logger
from ..database import DatabaseManager
from ..models import Skill, PlayerSkill, Realm


class CultivationService:
    """修炼服务类"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化修炼服务
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager

    async def cultivate(self, player_id: str, skill_id: Optional[str] = None) -> Dict[str, Any]:
        """
        进行修炼
        
        Args:
            player_id: 玩家ID
            skill_id: 功法ID（可选，默认使用基础功法）
            
        Returns:
            Dict[str, Any]: 修炼结果
        """
        # 获取玩家当前境界
        player = await self.db.fetch_one(
            "SELECT realm_id, experience FROM players WHERE id = ?",
            (player_id,)
        )
        if not player:
            raise ValueError("玩家不存在")
        
        # 获取功法信息
        if skill_id:
            skill = await self.get_skill_by_id(skill_id)
        else:
            # 默认使用基础吐纳术
            skill = await self.get_skill_by_id("skill_001")
        
        if not skill:
            raise ValueError("功法不存在")
        
        # 计算修炼获得的修为
        exp_gain = skill.experience_gain
        
        # 更新玩家修为
        await self.db.execute(
            "UPDATE players SET experience = experience + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (exp_gain, player_id)
        )
        await self.db.commit()
        
        logger.info(f"玩家 {player_id} 修炼获得 {exp_gain} 修为")
        
        return {
            "success": True,
            "skill_name": skill.name,
            "exp_gain": exp_gain,
            "message": f"你修炼了【{skill.name}】，获得 {exp_gain} 点修为",
        }

    async def breakthrough(self, player_id: str) -> Dict[str, Any]:
        """
        尝试境界突破
        
        Args:
            player_id: 玩家ID
            
        Returns:
            Dict[str, Any]: 突破结果
        """
        # 获取玩家信息
        player = await self.db.fetch_one(
            "SELECT * FROM players WHERE id = ?",
            (player_id,)
        )
        if not player:
            raise ValueError("玩家不存在")
        
        # 获取当前境界
        current_realm = await self.get_realm_by_id(player["realm_id"])
        if not current_realm:
            raise ValueError("当前境界数据异常")
        
        # 获取下一个境界
        next_realm = await self.get_next_realm(current_realm.level)
        if not next_realm:
            return {
                "success": False,
                "message": "你已达到最高境界，无法继续突破",
            }
        
        # 检查修为是否足够
        if player["experience"] < next_realm.experience_required:
            return {
                "success": False,
                "current_exp": player["experience"],
                "required_exp": next_realm.experience_required,
                "message": f"修为不足，需要 {next_realm.experience_required} 点修为，当前仅有 {player['experience']} 点",
            }
        
        # 使用数据库中配置的突破概率
        success_rate = next_realm.breakthrough_probability / 100.0
        
        # 执行突破
        import random
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
                )
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
            # 突破失败，损失部分修为
            exp_loss = int(next_realm.experience_required * 0.1)
            await self.db.execute(
                "UPDATE players SET experience = MAX(0, experience - ?), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (exp_loss, player_id)
            )
            await self.db.commit()
            
            return {
                "success": False,
                "exp_loss": exp_loss,
                "breakthrough_probability": next_realm.breakthrough_probability,
                "message": f"突破失败！损失了 {exp_loss} 点修为，继续努力吧",
            }

    # ==================== 功法管理 ====================

    async def get_skill_by_id(self, skill_id: str) -> Optional[Skill]:
        """根据ID获取功法"""
        sql = "SELECT * FROM skills WHERE id = ?"
        row = await self.db.fetch_one(sql, (skill_id,))
        if row:
            return Skill.from_dict(row)
        return None

    async def get_all_skills(self) -> List[Skill]:
        """获取所有功法"""
        sql = "SELECT * FROM skills ORDER BY id"
        rows = await self.db.fetch_all(sql)
        return [Skill.from_dict(row) for row in rows]

    async def create_skill(self, skill_data: Dict[str, Any]) -> Skill:
        """创建功法"""
        skill_id = skill_data.get("id", str(uuid.uuid4()))
        sql = """
            INSERT INTO skills (id, name, description, skill_type, realm_requirement, experience_gain, damage, cooldown)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(sql, (
            skill_id,
            skill_data["name"],
            skill_data.get("description"),
            skill_data["skill_type"],
            skill_data.get("realm_requirement"),
            skill_data.get("experience_gain", 10),
            skill_data.get("damage", 0),
            skill_data.get("cooldown", 0),
        ))
        await self.db.commit()
        return await self.get_skill_by_id(skill_id)

    async def update_skill(self, skill_id: str, **kwargs) -> Optional[Skill]:
        """更新功法"""
        allowed_fields = ["name", "description", "skill_type", "realm_requirement", "experience_gain", "damage", "cooldown"]
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

    async def get_realm_by_id(self, realm_id: str) -> Optional[Realm]:
        """根据ID获取境界"""
        sql = "SELECT * FROM realms WHERE id = ?"
        row = await self.db.fetch_one(sql, (realm_id,))
        if row:
            return Realm.from_dict(row)
        return None

    async def get_next_realm(self, current_level: int) -> Optional[Realm]:
        """获取下一个境界"""
        sql = "SELECT * FROM realms WHERE level > ? ORDER BY level ASC LIMIT 1"
        row = await self.db.fetch_one(sql, (current_level,))
        if row:
            return Realm.from_dict(row)
        return None

    async def get_all_realms(self) -> List[Realm]:
        """获取所有境界"""
        sql = "SELECT * FROM realms ORDER BY level"
        rows = await self.db.fetch_all(sql)
        return [Realm.from_dict(row) for row in rows]

    async def create_realm(self, realm_data: Dict[str, Any]) -> Realm:
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
        await self.db.execute(sql, (
            realm_id,
            realm_data["name"],
            realm_data.get("description"),
            realm_data["level"],
            realm_data["experience_required"],
            realm_data.get("breakthrough_probability", 50),
            realm_data.get("event_id", 1),
        ))
        await self.db.commit()
        return await self.get_realm_by_id(realm_id)

    async def update_realm(self, realm_id: str, **kwargs) -> Optional[Realm]:
        """
        更新境界
        
        Args:
            realm_id: 境界ID
            **kwargs: 要更新的字段
            
        Returns:
            Optional[Realm]: 更新后的境界对象
        """
        allowed_fields = [
            "name", "description", "level", "experience_required",
            "breakthrough_probability", "event_id"
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
