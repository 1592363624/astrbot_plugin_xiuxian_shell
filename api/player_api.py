"""
玩家API
提供玩家相关的接口，供命令层和后台管理调用
"""

from ..services import DeepSeclusionService, PlayerService
from ..utils.attributes import calc_battle_attrs


class PlayerAPI:
    """玩家API类"""

    def __init__(
        self,
        player_service: PlayerService,
        deep_seclusion_service: DeepSeclusionService = None,
    ):
        self.player_service = player_service
        self.deep_seclusion_service = deep_seclusion_service

    async def create_player(self, user_id: str, username: str) -> str:
        try:
            player = await self.player_service.create_player(user_id, username)
            realm = await self.player_service.db.fetch_one(
                "SELECT name FROM realms WHERE id = ?",
                (player.realm_id,),
            )
            realm_name = realm["name"] if realm else "未知"
            return (
                f"注册成功！欢迎 {username} 进入修仙世界！\n"
                f"当前境界：{realm_name}\n"
                f"初始灵石：{player.spirit_stone}\n"
                f"———后天属性———\n"
                f"根骨:{player.bone} 神识:{player.spirit} 悟性:{player.intel}\n"
                f"体魄:{player.str_} 灵觉:{player.percep} 机缘:{player.luck}"
            )
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"注册失败：{str(e)}"

    async def get_player_status(self, user_id: str) -> str:
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        realm = await self.player_service.db.fetch_one(
            "SELECT name, level FROM realms WHERE id = ?",
            (player_dict["realm_id"],),
        )
        realm_name = realm["name"] if realm else "未知"
        realm_level = realm["level"] if realm else 1

        # 获取下一境界所需修为作为显示分母
        next_realm = await self.player_service.db.fetch_one(
            "SELECT experience_required FROM realms WHERE level > ? ORDER BY level ASC LIMIT 1",
            (realm_level,),
        )
        exp_required = next_realm["experience_required"] if next_realm else 0

        battle_attrs = calc_battle_attrs(
            level=realm_level,
            bone=player_dict["bone"],
            spirit=player_dict["spirit"],
            intel=player_dict["intel"],
            str_=player_dict["str"],
            percep=player_dict["percep"],
            luck=player_dict["luck"],
        )

        # 查询玩家生效状态
        state_lines = []
        if self.deep_seclusion_service:
            states = await self.deep_seclusion_service.get_player_states(
                player_dict["id"]
            )
            if states:
                state_names = []
                for s in states:
                    state_type = s["state_type"]
                    if state_type == "dao_heart_broken":
                        state_names.append("【道心破碎】")
                    elif state_type == "peace_mode":
                        state_names.append("【避世】")
                    else:
                        state_names.append(f"【{state_type}】")
                state_lines.append("———当前状态———")
                state_lines.append(" ".join(state_names))

        status_parts = [
            "【修仙状态】",
            f"道号：{player_dict['username']}",
            f"境界：{realm_name}",
            f"修为：{player_dict['experience']}/{exp_required}",
            f"灵石：{player_dict['spirit_stone']}",
            "",
            "———战斗属性———",
            f"气血：{player_dict['health']}/{battle_attrs['max_health']}",
            f"法力：{player_dict['mp']}/{battle_attrs['max_mp']}",
            f"体力：{player_dict['stamina']}/{battle_attrs['max_stamina']}",
            f"物攻：{battle_attrs['attack']} 法攻：{battle_attrs['magic_attack']}",
            f"物防：{battle_attrs['defense']} 法防：{battle_attrs['magic_defense']}",
            f"速度：{battle_attrs['speed']} 闪避：{battle_attrs['dodge']:.1%}",
            "———后天属性———",
            f"根骨:{player_dict['bone']} 神识:{player_dict['spirit']} 悟性:{player_dict['intel']}",
            f"体魄:{player_dict['str']} 灵觉:{player_dict['percep']} 机缘:{player_dict['luck']}",
        ]
        if state_lines:
            status_parts.extend([""] + state_lines)

        return "\n".join(status_parts)

    async def change_username(self, user_id: str, new_username: str) -> str:
        result, error = await self.player_service.change_username(user_id, new_username)
        if error:
            return f"修改失败：{error}"
        return f"道号修改成功！你的新道号为：{result}"
