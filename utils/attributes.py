"""
战斗属性计算与基础属性分配工具
根据设计大纲中的公式，由基础属性 + 境界等级动态计算战斗属性
"""
import random
from typing import Dict, Any, Tuple


# 境界基础倍率（每大境界基础属性翻倍）
BASE_RATE = 2.0
# 小境界递增倍率（初期→中期→后期→圆满递增）
SMALL_RATE = 1.06
# 基础生命系数
HP_COEFF = 100
# 基础法力系数
MP_COEFF = 50
# 基础体力系数
STAMINA_COEFF = 50
# 基础攻击系数（物理/法术共用基数）
ATK_COEFF = 5
# 基础防御系数（物理/法术共用基数）
DEF_COEFF = 2

# 基础属性分配总点数（不含机缘）
ATTR_TOTAL_POINTS = 35
# 基础属性最小值
ATTR_MIN = 3
# 基础属性最大值
ATTR_MAX = 15
# 机缘最小值
LUCK_MIN = 1
# 机缘最大值
LUCK_MAX = 10

# 闪避率上限
DODGE_CAP = 0.60


def parse_realm_level(level: int) -> Tuple[int, int]:
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
    # 真仙及以上，每个单独为一个大境界，无小境界
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
    return (BASE_RATE ** major) * (SMALL_RATE ** minor)


def calc_battle_attrs(
    level: int,
    bone: int,
    spirit: int,
    intel: int,
    str_: int,
    percep: int,
    luck: int,
) -> Dict[str, Any]:
    """
    根据基础属性和境界等级计算战斗属性（衍生属性）

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

    # 气血 = HP_COEFF × 2^大境界 × 1.06^小境界 + 根骨×20 + 体魄×10
    max_health = int(HP_COEFF * mult + bone * 20 + str_ * 10)
    # 法力 = MP_COEFF × 2^大境界 × 1.06^小境界 + 神识×15 + 根骨×5
    max_mp = int(MP_COEFF * mult + spirit * 15 + bone * 5)
    # 体力 = STAMINA_COEFF × 2^大境界 × 1.06^小境界 + 体魄×20
    max_stamina = int(STAMINA_COEFF * mult + str_ * 20)
    # 物理攻击 = ATK_COEFF × 2^大境界 × 1.06^小境界 + 体魄×3 + 根骨×1
    attack = int(ATK_COEFF * mult + str_ * 3 + bone * 1)
    # 法术攻击 = ATK_COEFF × 2^大境界 × 1.06^小境界 + 神识×4
    magic_attack = int(ATK_COEFF * mult + spirit * 4)
    # 物理防御 = DEF_COEFF × 2^大境界 × 1.06^小境界 + 根骨×2 + 体魄×1
    defense = int(DEF_COEFF * mult + bone * 2 + str_ * 1)
    # 法术防御 = DEF_COEFF × 2^大境界 × 1.06^小境界 + 神识×2 + 根骨×1
    magic_defense = int(DEF_COEFF * mult + spirit * 2 + bone * 1)
    # 速度 = 10 + 灵觉×1.5 + (境界-1)×5
    speed = int(10 + percep * 1.5 + (level - 1) * 5)
    # 闪避率 = min(灵觉×1.5% + 境界×2%, 60%)
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


def allocate_base_attrs(
    total_points: int = ATTR_TOTAL_POINTS,
    attr_min: int = ATTR_MIN,
    attr_max: int = ATTR_MAX,
) -> Dict[str, int]:
    """
    随机分配基础属性点数（用于角色创建）

    将total_points随机分配给5项基础属性（根骨/神识/悟性/体魄/灵觉），
    每项最低attr_min，最高attr_max。
    机缘独立生成，不在此分配。

    分配算法：
    1. 每项先给attr_min保底
    2. 剩余点数随机打散分配，不超过attr_max上限

    Args:
        total_points: 可分配总点数（默认35）
        attr_min: 单项最低值（默认3）
        attr_max: 单项最高值（默认15）

    Returns:
        Dict[str, int]: 包含5项基础属性的字典
    """
    attr_names = ["bone", "spirit", "intel", "str", "percep"]
    count = len(attr_names)

    # 每项先分配保底值
    base = attr_min
    remaining = total_points - base * count
    max_extra = attr_max - attr_min

    # 随机分配剩余点数，使用"切蛋糕"法
    cuts = sorted(random.sample(range(remaining + count - 1), count - 1))
    portions = []
    prev = -1
    for c in cuts:
        portions.append(c - prev - 1)
        prev = c
    portions.append(remaining + count - 2 - prev)

    # 将分配量限制在max_extra以内
    extras = [min(p, max_extra) for p in portions]

    # 处理溢出：将超出部分重新分配给未满的属性
    overflow = sum(portions) - sum(extras)
    while overflow > 0:
        for i in range(count):
            if overflow <= 0:
                break
            can_add = max_extra - extras[i]
            if can_add > 0:
                add = min(can_add, overflow)
                extras[i] += add
                overflow -= add

    # 打乱顺序以增加随机性
    random.shuffle(extras)

    result = {}
    for i, name in enumerate(attr_names):
        result[name] = base + extras[i]

    return result


def generate_luck() -> int:
    """
    随机生成机缘值（1~10），创建角色时独立生成

    Returns:
        int: 机缘值
    """
    return random.randint(LUCK_MIN, LUCK_MAX)
