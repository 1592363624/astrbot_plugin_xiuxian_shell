"""
工具函数模块
提供通用的工具函数和辅助方法
"""

import uuid
from datetime import datetime, timedelta, timezone

BEIJING_TZ = timezone(timedelta(hours=8))


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


def bj_now() -> datetime:
    """
    获取当前北京时间

    项目内部统一使用北京时间存储和计算，
    所有数据库写入、业务逻辑中的时间判断均使用此函数。

    Returns:
        datetime: 当前北京时间（带时区信息）
    """
    return datetime.now(BEIJING_TZ)


def bj_now_iso() -> str:
    """
    获取当前北京时间的ISO格式字符串（不含时区后缀）

    数据库中存储的时间统一使用此格式。
    SQLite 使用字符串比较 ISO 时间，若格式不一致会导致比较错误，
    因此统一去除时区后缀，确保数据格式一致。

    Returns:
        str: 格式为 'YYYY-MM-DDTHH:MM:SS.ffffff' 的北京时间字符串
    """
    return datetime.now(BEIJING_TZ).replace(tzinfo=None).isoformat()


def ensure_bj(dt: datetime) -> datetime:
    """
    确保datetime对象为北京时区感知（aware）

    数据库中存储的数据可能是 naive datetime（无时区信息），
    而 bj_now() 返回的是 aware datetime。直接比较会抛出
    "can't compare offset-naive and offset-aware datetimes" 异常。

    此函数将 naive datetime 视为北京时间并补上时区信息，
    aware datetime 则原样返回。

    Args:
        dt: 待检查的datetime对象

    Returns:
        datetime: 带北京时区信息的datetime对象
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=BEIJING_TZ)
    return dt


def to_db_iso(dt: datetime) -> str:
    """
    将datetime转换为数据库存储用的ISO格式字符串（不含时区后缀）

    项目数据库使用 SQLite，时间比较依赖字符串序。
    若数据带 +08:00 后缀会导致字符串比较结果错误。

    此函数统一去除时区后缀，确保数据格式一致。

    Args:
        dt: datetime对象（naive或aware均可）

    Returns:
        str: 不含时区后缀的ISO格式时间字符串
    """
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt.isoformat()


def now_bj() -> datetime:
    """
    获取当前北京时间（bj_now的别名，语义更清晰）

    Returns:
        datetime: 当前北京时间（带时区信息）
    """
    return bj_now()


def bj_today_str() -> str:
    """
    获取北京时区的今日日期字符串

    用于每日重置等场景，确保"每日"边界对齐北京时间的自然日，
    而非UTC的0点切换。

    Returns:
        str: 格式为 'YYYY-MM-DD' 的北京日期字符串
    """
    return bj_now().strftime("%Y-%m-%d")


def utc_to_local(utc_dt: datetime) -> datetime:
    """
    将UTC时间转换为北京时间

    旧数据由UTC时间存储，迁移后此函数用于兼容性转换。
    新代码应直接使用 bj_now() 获取北京时间。

    Args:
        utc_dt: UTC时间的datetime对象（naive或aware均可）

    Returns:
        datetime: 北京时间的datetime对象（带时区信息）
    """
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(BEIJING_TZ)


def utc_now() -> datetime:
    """
    获取当前UTC时间（已弃用，保留向后兼容）

    新代码请使用 bj_now() 代替。

    Returns:
        datetime: 当前UTC时间（带时区信息）
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """
    获取当前UTC时间的ISO格式字符串（已弃用，保留向后兼容）

    新代码请使用 bj_now_iso() 代替。

    Returns:
        str: UTC时间的ISO格式字符串
    """
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def ensure_utc(dt: datetime) -> datetime:
    """
    确保datetime对象为UTC时区感知（已弃用，保留向后兼容）

    新代码请使用 ensure_bj() 代替。

    Args:
        dt: 待检查的datetime对象

    Returns:
        datetime: 带UTC时区信息的datetime对象
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def now_local() -> datetime:
    """
    获取当前本地时间（已弃用，保留向后兼容）

    新代码请使用 now_bj() 或 bj_now() 代替。

    Returns:
        datetime: 当前北京时间（带时区信息）
    """
    return bj_now()


def local_today_str() -> str:
    """
    获取本地时区的今日日期字符串（已弃用，保留向后兼容）

    新代码请使用 bj_today_str() 代替。

    Returns:
        str: 格式为 'YYYY-MM-DD' 的北京日期字符串
    """
    return bj_today_str()
