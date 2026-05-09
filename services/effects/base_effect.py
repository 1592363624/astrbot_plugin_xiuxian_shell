"""
效果基类与结果数据结构
定义所有效果实现类的统一接口规范
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EffectResult:
    """
    效果触发结果
    统一封装效果执行后的返回信息，供交互提示层使用
    """

    success: bool
    """是否触发成功"""

    effect_desc: str = ""
    """效果描述文本，用于生成提示信息"""

    effect_params: dict[str, Any] = field(default_factory=dict)
    """效果参数，用于提示文案中的动态替换"""

    error_msg: str = ""
    """错误信息，触发失败时填写"""


class BaseEffect(ABC):
    """
    效果基类（接口）
    所有效果类型均需继承此类并实现 trigger 方法
    新增效果类型时仅需新增实现类，无需修改触发核心逻辑
    """

    @property
    @abstractmethod
    def effect_type(self) -> str:
        """
        效果类型标识，与配置文件中的 effect_type 字段对应

        Returns:
            str: 效果类型字符串
        """
        ...

    @abstractmethod
    async def trigger(
        self,
        player_id: str,
        params: dict[str, Any],
        db_manager: Any,
        cultivation_service: Any = None,
    ) -> EffectResult:
        """
        触发效果

        Args:
            player_id: 玩家ID
            params: 效果参数（来自配置文件的 effect_params）
            db_manager: 数据库管理器实例
            cultivation_service: 修炼服务实例（部分效果需要）

        Returns:
            EffectResult: 效果触发结果
        """
        ...
