"""
配置管理器
负责插件配置的加载、保存和管理
"""

import json
from pathlib import Path
from typing import Any

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
            "register_cooldown": 60,
        },
        "checkin": {
            "base_reward_rate": 1,
            "three_day_reward_rate": 2,
            "seven_day_reward_rate": 3,
        },
        "player": {},
        "seclusion": {
            "success_probability": 0.60,
            "failure_probability": 0.25,
            "possession_probability": 0.15,
            "exp_ratio_min": 0.001,
            "exp_ratio_max": 0.001,
            "possession_exp_ratio": 0.001,
            "cooldown_min_minutes": 10,
            "cooldown_max_minutes": 30,
            "encounter_probability": 0.10,
        },
        "pill": {
            "toxicity_duration_hours": 24,
            "same_pill_toxicity": 1,
            "toxicity_penalty_rate": 0.1,
            "detox_item_id": "item_detox",
        },
        "notification": {
            "templates": [
                {
                    "id": "breakthrough_success",
                    "name": "突破成功通知",
                    "title_template": "突破成功",
                    "content_template": "恭喜{username}突破至{realm}！修仙之路更进一步。",
                },
                {
                    "id": "tribulation_coming",
                    "name": "渡劫预警",
                    "title_template": "天劫预警",
                    "content_template": "{username}，你的修为已至{realm}巅峰，天劫将至，请做好准备！",
                },
                {
                    "id": "system_maintenance",
                    "name": "系统维护公告",
                    "title_template": "系统维护通知",
                    "content_template": "修仙界将于{time}进行维护，预计持续{duration}，届时将暂时无法修炼，请各位道友提前做好准备。",
                },
                {
                    "id": "event_announcement",
                    "name": "活动公告",
                    "title_template": "修仙活动：{event_name}",
                    "content_template": "{event_description}\n活动时间：{start_time} 至 {end_time}\n参与即可获得丰厚奖励！",
                },
            ],
        },
    }

    def __init__(self, context: Context, config: dict[str, Any] | None = None):
        """
        初始化配置管理器

        Args:
            context: AstrBot上下文
            config: 外部传入的配置
        """
        self.context = context
        self.plugin_name = "astrbot_plugin_xiuxian_shell"
        self._config: dict[str, Any] = {}
        self._config_file = (
            Path(StarTools.get_data_dir(self.plugin_name)) / "config.json"
        )
        self._load_config(config)

    def _deep_copy(self, obj: Any) -> Any:
        """深拷贝对象"""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj

    def _load_config(self, external_config: dict[str, Any] | None = None):
        """
        加载配置

        Args:
            external_config: 外部配置
        """
        # 从默认配置开始（使用深拷贝避免污染 DEFAULT_CONFIG）
        self._config = self._deep_copy(self.DEFAULT_CONFIG)
        # 从文件加载持久化配置
        if self._config_file.exists():
            try:
                with open(self._config_file, encoding="utf-8") as f:
                    file_config = json.load(f)
                self._merge_config(self._config, file_config)
                logger.info(f"已从文件加载配置: {self._config_file}")
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}")
        # 合并外部配置（优先级最高）
        if external_config:
            self._merge_config(self._config, external_config)
        logger.info("配置加载完成")

    def _save_config(self):
        """保存配置到文件"""
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            logger.info(f"配置已保存到: {self._config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")

    def _merge_config(self, base: dict[str, Any], override: dict[str, Any]):
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
        设置配置项并持久化到文件

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
        self._save_config()

    def get_db_path(self) -> str:
        """
        获取数据库路径

        Returns:
            str: 数据库文件完整路径
        """
        db_name = self.get("database.name", "xiuxian.db")
        return str(Path(StarTools.get_data_dir(self.plugin_name)) / db_name)

    def get_all(self) -> dict[str, Any]:
        """
        获取所有有效配置

        只返回 DEFAULT_CONFIG 中定义的配置项，过滤已删除的旧配置

        Returns:
            Dict[str, Any]: 有效配置字典
        """
        result = {}
        for section_key, section_value in self.DEFAULT_CONFIG.items():
            if section_key in self._config:
                if isinstance(section_value, dict):
                    # 只保留 DEFAULT_CONFIG 中定义的子键
                    result[section_key] = {}
                    for field_key in section_value.keys():
                        if field_key in self._config[section_key]:
                            result[section_key][field_key] = self._config[section_key][
                                field_key
                            ]
                else:
                    result[section_key] = self._config[section_key]
        return result

    def update(self, config: dict[str, Any]):
        """
        更新配置并持久化到文件

        Args:
            config: 新配置
        """
        self._merge_config(self._config, config)
        self._save_config()
        logger.info("配置已更新并持久化")
