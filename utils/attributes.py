"""
战斗属性计算工具
根据设计大纲中的公式，由后天属性 + 境界等级动态计算战斗属性
"""

from typing import Any

BASE_RATE = 2.0
SMALL_RATE = 1.06
HP_COEFF = 100
MP_COEFF = 50
STAMINA_COEFF = 50
ATK_COEFF = 5
DEF_COEFF = 2
DODGE_CAP = 0.60


def parse_realm_level(level: int) -> tuple[int, int]:
    """
    将境界等级解析为（大境界序号, 小境界序号）

    境界编码对照:
        凡人(1): 大境界=0, 小境界=0
        炼气(2~5): 大境界=1, 小境界=0~3
        筑基(6~9): 大境界=2, 小境界=0~3
        金丹(10~13): 大境界=3, 小境界=0~3
        ...
        渡劫(34~37): 大境界=9, 小境界=0~3
        真仙(38): 大境界=10, 小境界=0
        金仙(39): 大境界=11, 小境界=0
        太乙金仙(40): 大境界=12, 小境界=0
        大罗金仙(41): 大境界=13, 小境界=0
        仙王(42): 大境界=14, 小境界=0
        仙帝(43): 大境界=15, 小境界=0

    Args:
        level: 境界等级（1~43）

    Returns:
        Tuple[int, int]: (大境界序号, 小境界序号)
    """
    if level <= 1:
        return (0, 0)
    if level <= 37:
        return ((level - 2) // 4 + 1, (level - 2) % 4)
    return (level - 28, 0)


def calc_realm_multiplier(level: int) -> float:
    """
    计算境界乘数系数 = BASE_RATE ^ 大境界 × SMALL_RATE ^ 小境界

    Args:
        level: 境界等级

    Returns:
        float: 境界乘数
    """
    major, minor = parse_realm_level(level)
    return (BASE_RATE**major) * (SMALL_RATE**minor)


def calc_battle_attrs(
    level: int,
    bone: int,
    spirit: int,
    intel: int,
    str_: int,
    percep: int,
    luck: int,
) -> dict[str, Any]:
    """
    根据后天属性和境界等级计算战斗属性（衍生属性）

    公式来源: 设计大纲 - 战斗属性（衍生属性）
    <N × 2^大境界 × 1.06^小境界> 表示境界贡献部分

    Args:
        level: 境界等级（1~43）
        bone: 根骨
        spirit: 神识
        intel: 悟性（不影响战斗属性，但参与修炼速度等计算）
        str_: 体魄
        percep: 灵觉
        luck: 机缘（不影响战斗属性，但影响掉落/奇遇）

    Returns:
        Dict[str, Any]: 战斗属性字典，键与设计大纲中的ID一致
    """
    mult = calc_realm_multiplier(level)

    max_health = int(HP_COEFF * mult + bone * 20 + str_ * 10)
    max_mp = int(MP_COEFF * mult + spirit * 15 + bone * 5)
    max_stamina = int(STAMINA_COEFF * mult + str_ * 20)
    attack = int(ATK_COEFF * mult + str_ * 3 + bone * 1)
    magic_attack = int(ATK_COEFF * mult + spirit * 4)
    defense = int(DEF_COEFF * mult + bone * 2 + str_ * 1)
    magic_defense = int(DEF_COEFF * mult + spirit * 2 + bone * 1)
    speed = int(10 + percep * 1.5 + (level - 1) * 5)
    dodge = min(percep * 0.015 + level * 0.02, DODGE_CAP)

    return {
        "max_health": max_health,
        "health": max_health,
        "max_mp": max_mp,
        "mp": max_mp,
        "max_stamina": max_stamina,
        "stamina": max_stamina,
        "attack": attack,
        "magic_attack": magic_attack,
        "defense": defense,
        "magic_defense": magic_defense,
        "speed": speed,
        "dodge": round(dodge, 4),
    }
