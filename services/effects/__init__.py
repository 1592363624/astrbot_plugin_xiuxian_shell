"""
效果系统模块
实现物品使用后的效果触发机制，采用接口+实现类模式，支持高扩展性
"""

from .base_effect import BaseEffect, EffectResult
from .effect_registry import EffectRegistry, register_all_effects
from .implementations import (
    AddBreakthroughRateEffect,
    AddCultivationEffect,
    AddSpiritStoneEffect,
    AddTempAttributeEffect,
    DetoxEffect,
    HealEffect,
)

__all__ = [
    "BaseEffect",
    "EffectResult",
    "EffectRegistry",
    "register_all_effects",
    "AddCultivationEffect",
    "HealEffect",
    "AddSpiritStoneEffect",
    "DetoxEffect",
    "AddBreakthroughRateEffect",
    "AddTempAttributeEffect",
]
