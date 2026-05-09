"""
效果注册器
管理所有效果类型的注册与查找，采用单例模式
新增效果类型时仅需在此注册即可，无需修改触发逻辑
"""

from typing import Any

from astrbot.api import logger

from .base_effect import BaseEffect


class EffectRegistry:
    """
    效果注册器
    维护 effect_type -> BaseEffect 实现类的映射关系
    """

    _instance: "EffectRegistry | None" = None
    _effects: dict[str, BaseEffect] = {}

    def __new__(cls) -> "EffectRegistry":
        """单例模式，确保全局唯一注册器"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._effects = {}
        return cls._instance

    def register(self, effect: BaseEffect) -> None:
        """
        注册效果实现类

        Args:
            effect: 效果实现类实例
        """
        self._effects[effect.effect_type] = effect
        logger.debug(f"已注册效果类型: {effect.effect_type}")

    def get(self, effect_type: str) -> BaseEffect | None:
        """
        根据效果类型获取实现类

        Args:
            effect_type: 效果类型标识

        Returns:
            Optional[BaseEffect]: 效果实现类实例，未找到返回 None
        """
        return self._effects.get(effect_type)

    def get_all_types(self) -> list[str]:
        """
        获取所有已注册的效果类型

        Returns:
            List[str]: 效果类型列表
        """
        return list(self._effects.keys())

    def is_registered(self, effect_type: str) -> bool:
        """
        检查效果类型是否已注册

        Args:
            effect_type: 效果类型标识

        Returns:
            bool: 是否已注册
        """
        return effect_type in self._effects

    def clear(self) -> None:
        """清空所有注册（用于测试）"""
        self._effects.clear()


def register_all_effects() -> EffectRegistry:
    """
    注册所有内置效果实现类
    在插件初始化时调用一次即可

    Returns:
        EffectRegistry: 注册完成的效果注册器
    """
    from .implementations import (
        AddBreakthroughRateEffect,
        AddCultivationEffect,
        AddSpiritStoneEffect,
        AddTempAttributeEffect,
        DetoxEffect,
        HealEffect,
    )

    registry = EffectRegistry()
    registry.register(AddCultivationEffect())
    registry.register(HealEffect())
    registry.register(AddSpiritStoneEffect())
    registry.register(DetoxEffect())
    registry.register(AddBreakthroughRateEffect())
    registry.register(AddTempAttributeEffect())
    logger.info(f"效果系统初始化完成，已注册 {len(registry.get_all_types())} 种效果类型")
    return registry
