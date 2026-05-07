"""
战斗服务
处理战斗相关的业务逻辑
"""
import random
from typing import Dict, Any, Optional
from astrbot.api import logger
from ..database import DatabaseManager


class CombatService:
    """战斗服务类"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化战斗服务
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager

    async def battle(self, attacker_id: str, defender_id: Optional[str] = None) -> Dict[str, Any]:
        """
        执行战斗
        
        Args:
            attacker_id: 攻击者玩家ID
            defender_id: 防御者玩家ID（可选，为None时与怪物战斗）
            
        Returns:
            Dict[str, Any]: 战斗结果
        """
        # 获取攻击者信息
        attacker = await self.db.fetch_one(
            "SELECT * FROM players WHERE id = ?",
            (attacker_id,)
        )
        if not attacker:
            raise ValueError("攻击者不存在")
        
        if defender_id:
            # PvP战斗
            defender = await self.db.fetch_one(
                "SELECT * FROM players WHERE id = ?",
                (defender_id,)
            )
            if not defender:
                raise ValueError("防御者不存在")
            
            result = await self._pvp_battle(attacker, defender)
        else:
            # PvE战斗（与怪物战斗）
            result = await self._pve_battle(attacker)
        
        return result

    async def _pvp_battle(self, attacker: dict, defender: dict) -> Dict[str, Any]:
        """
        PvP战斗逻辑
        
        Args:
            attacker: 攻击者数据
            defender: 防御者数据
            
        Returns:
            Dict[str, Any]: 战斗结果
        """
        # 简单的战斗计算
        attacker_power = attacker["attack"] + random.randint(1, 10)
        defender_power = defender["defense"] + random.randint(1, 10)
        
        if attacker_power > defender_power:
            # 攻击者胜利
            damage = attacker_power - defender_power
            reward = random.randint(10, 50)
            
            # 更新防御者生命值
            new_health = max(0, defender["health"] - damage)
            await self.db.execute(
                "UPDATE players SET health = ? WHERE id = ?",
                (new_health, defender["id"])
            )
            
            # 奖励攻击者灵石
            await self.db.execute(
                "UPDATE players SET spirit_stone = spirit_stone + ? WHERE id = ?",
                (reward, attacker["id"])
            )
            await self.db.commit()
            
            return {
                "success": True,
                "winner": attacker["username"],
                "loser": defender["username"],
                "damage": damage,
                "reward": reward,
                "message": f"【{attacker['username']}】战胜了【{defender['username']}】，获得 {reward} 灵石",
            }
        else:
            # 防御者胜利
            damage = defender_power - attacker_power
            new_health = max(0, attacker["health"] - damage)
            await self.db.execute(
                "UPDATE players SET health = ? WHERE id = ?",
                (new_health, attacker["id"])
            )
            await self.db.commit()
            
            return {
                "success": False,
                "winner": defender["username"],
                "loser": attacker["username"],
                "damage": damage,
                "message": f"【{attacker['username']}】挑战【{defender['username']}】失败，受到 {damage} 点伤害",
            }

    async def _pve_battle(self, player: dict) -> Dict[str, Any]:
        """
        PvE战斗逻辑
        
        Args:
            player: 玩家数据
            
        Returns:
            Dict[str, Any]: 战斗结果
        """
        # 生成怪物属性
        monster_level = max(1, player["attack"] // 10)
        monster = {
            "name": f"妖兽Lv.{monster_level}",
            "health": 50 + monster_level * 20,
            "attack": 5 + monster_level * 5,
            "defense": 3 + monster_level * 3,
        }
        
        # 战斗模拟
        player_hp = player["health"]
        monster_hp = monster["health"]
        
        while player_hp > 0 and monster_hp > 0:
            # 玩家攻击
            player_damage = max(1, player["attack"] - monster["defense"] + random.randint(-3, 5))
            monster_hp -= player_damage
            
            if monster_hp <= 0:
                break
            
            # 怪物攻击
            monster_damage = max(1, monster["attack"] - player["defense"] + random.randint(-3, 3))
            player_hp -= monster_damage
        
        if player_hp > 0:
            # 玩家胜利
            exp_reward = random.randint(20, 50) * monster_level
            stone_reward = random.randint(10, 30) * monster_level
            
            await self.db.execute(
                """UPDATE players 
                SET health = ?, 
                    experience = experience + ?, 
                    spirit_stone = spirit_stone + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?""",
                (player_hp, exp_reward, stone_reward, player["id"])
            )
            await self.db.commit()
            
            return {
                "success": True,
                "monster_name": monster["name"],
                "damage_taken": player["health"] - player_hp,
                "exp_reward": exp_reward,
                "stone_reward": stone_reward,
                "message": f"你击败了【{monster['name']}】！获得 {exp_reward} 修为和 {stone_reward} 灵石",
            }
        else:
            # 玩家失败
            await self.db.execute(
                "UPDATE players SET health = 1 WHERE id = ?",
                (player["id"],)
            )
            await self.db.commit()
            
            return {
                "success": False,
                "monster_name": monster["name"],
                "message": f"你不敌【{monster['name']}】，重伤昏迷，被路人救回",
            }
