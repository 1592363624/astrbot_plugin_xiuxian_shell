"""
效果实现类模块
包含所有内置效果的具体实现
新增效果类型时，在此目录下新建实现文件并在本文件中导出即可
"""

from .add_breakthrough_rate import AddBreakthroughRateEffect
from .add_cultivation import AddCultivationEffect
from .add_spirit_stone import AddSpiritStoneEffect
from .add_temp_attribute import AddTempAttributeEffect
from .detox import DetoxEffect
from .heal import HealEffect

__all__ = [
    "AddCultivationEffect",
    "HealEffect",
    "AddSpiritStoneEffect",
    "DetoxEffect",
    "AddBreakthroughRateEffect",
    "AddTempAttributeEffect",
]
