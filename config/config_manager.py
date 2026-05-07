"""
配置管理器
负责插件配置的加载、保存和管理
"""
from pathlib import Path
from typing import Any, Dict, Optional
from astrbot.api import logger
from astrbot.api.star import Context
from astrbot.core.star import StarTools


class ConfigManager:
    """插件配置管理器"""

    # 默认配置项
    DEFAULT_CONFIG = {
        "database": {
            "name": "xiuxian.db",
            "wal_mode": True,
        },
        "game": {
            "max_level": 100,
            "base_exp_multiplier": 1.5,
            "cultivation_cooldown": 300,
            "explore_cooldown": 600,
            "combat_cooldown": 180,
        },
        "player": {
            "initial_health": 100,
            "initial_attack": 10,
            "initial_defense": 5,
            "initial_spirit_stone": 100,
        },
        "realms": [
            {"id": "realm_001", "name": "练气期", "level": 1, "exp_required": 100},
            {"id": "realm_002", "name": "筑基期", "level": 2, "exp_required": 500},
            {"id": "realm_003", "name": "金丹期", "level": 3, "exp_required": 2000},
            {"id": "realm_004", "name": "元婴期", "level": 4, "exp_required": 8000},
            {"id": "realm_005", "name": "化神期", "level": 5, "exp_required": 30000},
            {"id": "realm_006", "name": "炼虚期", "level": 6, "exp_required": 100000},
            {"id": "realm_007", "name": "合体期", "level": 7, "exp_required": 500000},
            {"id": "realm_008", "name": "大乘期", "level": 8, "exp_required": 2000000},
            {"id": "realm_009", "name": "渡劫期", "level": 9, "exp_required": 10000000},
        ],
        "items": [
            {
                "id": "item_001",
                "name": "回春丹",
                "description": "恢复50点生命值",
                "item_type": "consumable",
                "rarity": "common",
                "effect_type": "heal",
                "effect_value": 50,
                "price": 50,
            },
            {
                "id": "item_002",
                "name": "聚灵丹",
                "description": "增加100点修为",
                "item_type": "consumable",
                "rarity": "uncommon",
                "effect_type": "exp",
                "effect_value": 100,
                "price": 200,
            },
            {
                "id": "item_003",
                "name": "灵石",
                "description": "修仙界通用货币",
                "item_type": "currency",
                "rarity": "common",
                "effect_type": "spirit_stone",
                "effect_value": 1,
                "price": 1,
            },
        ],
        "skills": [
            {
                "id": "skill_001",
                "name": "基础吐纳术",
                "description": "最基础的修炼功法",
                "skill_type": "cultivation",
                "realm_requirement": "realm_001",
                "experience_gain": 10,
            },
            {
                "id": "skill_002",
                "name": "劈空掌",
                "description": "基础攻击技能",
                "skill_type": "combat",
                "realm_requirement": "realm_001",
                "damage": 15,
                "cooldown": 3,
            },
        ],
        "events": [
            {
                "id": "event_001",
                "name": "灵草奇遇",
                "description": "你在山间发现了一株灵草",
                "event_type": "explore",
                "trigger_condition": "explore",
                "reward_type": "item",
                "reward_value": 1,
                "probability": 0.3,
            },
            {
                "id": "event_002",
                "name": "妖兽袭击",
                "description": "一只妖兽突然出现",
                "event_type": "combat",
                "trigger_condition": "explore",
                "reward_type": "spirit_stone",
                "reward_value": 50,
                "probability": 0.2,
            },
        ],
    }

    def __init__(self, context: Context, config: Optional[Dict[str, Any]] = None):
        """
        初始化配置管理器
        
        Args:
            context: AstrBot上下文
            config: 外部传入的配置
        """
        self.context = context
        self.plugin_name = "astrbot_plugin_xiuxian_shell"
        self._config: Dict[str, Any] = {}
        self._load_config(config)

    def _load_config(self, external_config: Optional[Dict[str, Any]] = None):
        """
        加载配置
        
        Args:
            external_config: 外部配置
        """
        # 从默认配置开始
        self._config = self.DEFAULT_CONFIG.copy()
        # 合并外部配置
        if external_config:
            self._merge_config(self._config, external_config)
        logger.info("配置加载完成")

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """
        深度合并配置
        
        Args:
            base: 基础配置
            override: 覆盖配置
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键，支持点号分隔的路径
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any):
        """
        设置配置项
        
        Args:
            key: 配置键，支持点号分隔的路径
            value: 配置值
        """
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def get_db_path(self) -> str:
        """
        获取数据库路径
        
        Returns:
            str: 数据库文件完整路径
        """
        db_name = self.get("database.name", "xiuxian.db")
        return str(
            Path(StarTools.get_data_dir(self.plugin_name)) / db_name
        )

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            Dict[str, Any]: 完整配置字典
        """
        return self._config.copy()

    def update(self, config: Dict[str, Any]):
        """
        更新配置
        
        Args:
            config: 新配置
        """
        self._merge_config(self._config, config)
        logger.info("配置已更新")
