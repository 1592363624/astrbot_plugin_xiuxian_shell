"""
战斗服务
处理战斗相关的业务逻辑
战斗属性（衍生属性）由基础属性+境界等级动态计算，不存入数据库
"""

import random
from typing import TYPE_CHECKING, Any

from ..database import DatabaseManager
from ..utils.attributes import calc_battle_attrs

if TYPE_CHECKING:
    from .cultivation_service import CultivationService


class CombatService:
    """战斗服务类"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        cultivation_service: "CultivationService" = None,
    ):
        self.db = db_manager
        self.cultivation_service = cultivation_service

    async def _get_player_with_battle_attrs(
        self, player_id: str
    ) -> dict[str, Any] | None:
        """
        获取玩家数据并附加动态计算的战斗属性

        Args:
            player_id: 玩家ID

        Returns:
            Optional[Dict]: 玩家数据（含战斗属性），不存在返回None
        """
        player = await self.db.fetch_one(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        )
        if not player:
            return None

        realm_level = 1
        if self.cultivation_service:
            realm = await self.cultivation_service.get_realm_by_id(player["realm_id"])
            if realm:
                realm_level = realm.level

        battle_attrs = calc_battle_attrs(
            level=realm_level,
            bone=player["bone"],
            spirit=player["spirit"],
            intel=player["intel"],
            str_=player["str"],
            percep=player["percep"],
            luck=player["luck"],
        )

        result = dict(player)
        result.update(battle_attrs)
        return result

    async def battle(
        self, attacker_id: str, defender_id: str | None = None
    ) -> dict[str, Any]:
        attacker = await self._get_player_with_battle_attrs(attacker_id)
        if not attacker:
            raise ValueError("攻击者不存在")

        if defender_id:
            defender = await self._get_player_with_battle_attrs(defender_id)
            if not defender:
                raise ValueError("防御者不存在")
            result = await self._pvp_battle(attacker, defender)
        else:
            result = await self._pve_battle(attacker)

        return result

    async def _pvp_battle(self, attacker: dict, defender: dict) -> dict[str, Any]:
        attacker_power = attacker["attack"] + random.randint(1, 10)
        defender_power = defender["defense"] + random.randint(1, 10)

        if attacker_power > defender_power:
            damage = attacker_power - defender_power
            reward = random.randint(10, 50)

            new_health = max(0, defender["health"] - damage)
            await self.db.execute(
                "UPDATE players SET health = ? WHERE id = ?",
                (new_health, defender["id"]),
            )

            await self.db.execute(
                "UPDATE players SET spirit_stone = spirit_stone + ? WHERE id = ?",
                (reward, attacker["id"]),
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
            damage = defender_power - attacker_power
            new_health = max(0, attacker["health"] - damage)
            await self.db.execute(
                "UPDATE players SET health = ? WHERE id = ?",
                (new_health, attacker["id"]),
            )
            await self.db.commit()

            return {
                "success": False,
                "winner": defender["username"],
                "loser": attacker["username"],
                "damage": damage,
                "message": f"【{attacker['username']}】挑战【{defender['username']}】失败，受到 {damage} 点伤害",
            }

    async def _pve_battle(self, player: dict) -> dict[str, Any]:
        monster_level = max(1, player["attack"] // 10)
        monster = {
            "name": f"妖兽Lv.{monster_level}",
            "health": 50 + monster_level * 20,
            "attack": 5 + monster_level * 5,
            "defense": 3 + monster_level * 3,
        }

        player_hp = player["health"]
        monster_hp = monster["health"]

        while player_hp > 0 and monster_hp > 0:
            player_damage = max(
                1, player["attack"] - monster["defense"] + random.randint(-3, 5)
            )
            monster_hp -= player_damage

            if monster_hp <= 0:
                break

            monster_damage = max(
                1, monster["attack"] - player["defense"] + random.randint(-3, 3)
            )
            player_hp -= monster_damage

        if player_hp > 0:
            exp_reward = random.randint(20, 50) * monster_level
            stone_reward = random.randint(10, 30) * monster_level

            await self.db.execute(
                """UPDATE players
                SET health = ?,
                    experience = experience + ?,
                    spirit_stone = spirit_stone + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?""",
                (player_hp, exp_reward, stone_reward, player["id"]),
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
            await self.db.execute(
                "UPDATE players SET health = 1 WHERE id = ?", (player["id"],)
            )
            await self.db.commit()

            return {
                "success": False,
                "monster_name": monster["name"],
                "message": f"你不敌【{monster['name']}】，重伤昏迷，被路人救回",
            }
