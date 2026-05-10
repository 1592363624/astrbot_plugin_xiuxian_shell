"""
工具函数模块
提供通用的工具函数和辅助方法
"""

import uuid
from datetime import datetime, timezone


def generate_id() -> str:
    """
    生成唯一ID

    Returns:
        str: UUID字符串
    """
    return str(uuid.uuid4())


def format_number(num: int | float) -> str:
    """
    格式化数字显示
    大数字使用中文单位

    Args:
        num: 数字

    Returns:
        str: 格式化后的字符串
    """
    if num < 10000:
        return str(int(num))
    elif num < 100000000:
        return f"{num / 10000:.1f}万"
    else:
        return f"{num / 100000000:.1f}亿"


def calculate_level(
    experience: int, base_exp: int = 100, multiplier: float = 1.5
) -> int:
    """
    根据经验值计算等级

    Args:
        experience: 当前经验值
        base_exp: 基础升级经验
        multiplier: 经验倍率

    Returns:
        int: 等级
    """
    if experience <= 0:
        return 1

    level = 1
    required_exp = base_exp
    total_exp = 0

    while total_exp + required_exp <= experience:
        total_exp += required_exp
        level += 1
        required_exp = int(base_exp * (multiplier ** (level - 1)))

    return level


def calculate_exp_for_level(
    target_level: int, base_exp: int = 100, multiplier: float = 1.5
) -> int:
    """
    计算达到目标等级所需的经验值

    Args:
        target_level: 目标等级
        base_exp: 基础升级经验
        multiplier: 经验倍率

    Returns:
        int: 所需经验值
    """
    if target_level <= 1:
        return 0

    total_exp = 0
    for level in range(1, target_level):
        total_exp += int(base_exp * (multiplier ** (level - 1)))

    return total_exp


def clamp(
    value: int | float, min_val: int | float, max_val: int | float
) -> int | float:
    """
    将值限制在指定范围内

    Args:
        value: 原始值
        min_val: 最小值
        max_val: 最大值

    Returns:
        Union[int, float]: 限制后的值
    """
    return max(min_val, min(value, max_val))


def percentage(value: int | float, total: int | float) -> float:
    """
    计算百分比

    Args:
        value: 当前值
        total: 总值

    Returns:
        float: 百分比（0-100）
    """
    if total <= 0:
        return 0.0
    return round((value / total) * 100, 2)


def progress_bar(current: int, total: int, length: int = 10) -> str:
    """
    生成进度条

    Args:
        current: 当前值
        total: 总值
        length: 进度条长度

    Returns:
        str: 进度条字符串
    """
    if total <= 0:
        return "□" * length

    filled = int((current / total) * length)
    filled = min(filled, length)
    empty = length - filled

    return "■" * filled + "□" * empty


def rarity_text(rarity: str) -> str:
    """
    获取品质中文名称

    Args:
        rarity: 品质代码

    Returns:
        str: 中文名称
    """
    rarity_map = {
        "common": "普通",
        "uncommon": "优秀",
        "rare": "稀有",
        "epic": "史诗",
        "legendary": "传说",
    }
    return rarity_map.get(rarity, "未知")


def item_type_text(item_type: str) -> str:
    """
    获取物品类型中文名称

    Args:
        item_type: 类型代码

    Returns:
        str: 中文名称
    """
    type_map = {
        "consumable": "消耗品",
        "equipment": "装备",
        "material": "材料",
        "currency": "货币",
    }
    return type_map.get(item_type, "未知")


def utc_to_local(utc_dt: datetime) -> datetime:
    """
    将UTC时间转换为系统本地时间

    项目内部统一使用UTC时间存储和计算，
    仅在需要向用户展示时调用此函数转换为本地时间。

    Args:
        utc_dt: UTC时间的datetime对象（naive或aware均可）

    Returns:
        datetime: 本地时间的datetime对象（带时区信息）
    """
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone()


def now_local() -> datetime:
    """
    获取当前本地时间

    Returns:
        datetime: 当前本地时间（带时区信息）
    """
    return datetime.now(timezone.utc).astimezone()


def local_today_str() -> str:
    """
    获取本地时区的今日日期字符串

    用于每日重置等场景，确保"每日"边界对齐用户所在时区的自然日，
    而非UTC的0点切换。

    Returns:
        str: 格式为 'YYYY-MM-DD' 的本地日期字符串
    """
    return now_local().strftime("%Y-%m-%d")
