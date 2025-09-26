"""工具配置管理"""

from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass
import json
import os

from ..utils.logger import get_logger
from ..core.tool_registry import BaseToolProvider


@dataclass
class ToolProviderConfig:
    """工具提供者配置"""
    name: str
    provider_class: str
    enabled: bool = True
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


@dataclass
class ToolConfig:
    """工具配置"""
    name: str
    enabled: bool = True
    category: str = "general"
    provider: Optional[str] = None
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class ToolsConfigManager:
    """工具配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """初始化工具配置管理器"""
        self.logger = get_logger(__name__)
        self.config_file = config_file or self._get_default_config_path()
        self.providers: Dict[str, ToolProviderConfig] = {}
        self.tools: Dict[str, ToolConfig] = {}

        # 加载配置
        self._load_config()

    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        current_dir = os.path.dirname(__file__)
        return os.path.join(current_dir, "tools.json")

    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self._parse_config(config_data)
            else:
                self.logger.warning(f"Config file not found: {self.config_file}, using default configuration")
                self._load_default_config()
        except Exception as e:
            self.logger.error(f"Failed to load config file {self.config_file}: {e}")
            self.logger.info("Using default configuration")
            self._load_default_config()

    def _parse_config(self, config_data: Dict[str, Any]):
        """解析配置数据"""
        # 加载工具提供者配置
        providers_config = config_data.get("providers", {})
        for provider_name, provider_data in providers_config.items():
            self.providers[provider_name] = ToolProviderConfig(
                name=provider_name,
                provider_class=provider_data.get("class"),
                enabled=provider_data.get("enabled", True),
                config=provider_data.get("config", {})
            )

        # 加载工具配置
        tools_config = config_data.get("tools", {})
        for tool_name, tool_data in tools_config.items():
            self.tools[tool_name] = ToolConfig(
                name=tool_name,
                enabled=tool_data.get("enabled", True),
                category=tool_data.get("category", "general"),
                provider=tool_data.get("provider"),
                config=tool_data.get("config", {})
            )

        self.logger.info(f"Loaded config: {len(self.providers)} providers, {len(self.tools)} tools")

    def _load_default_config(self):
        """加载默认配置"""
        # 默认的工具提供者配置
        default_providers = {
            "calculator": {
                "class": "src.core.tool_providers.CalculatorToolProvider",
                "enabled": True,
                "config": {}
            },
            "xiaohongshu": {
                "class": "src.core.tool_providers.XiaohongshuToolProvider",
                "enabled": True,
                "config": {
                    "headless": True,
                    "timeout": 30
                }
            }
        }

        # 默认的工具配置
        default_tools = {
            "calculate": {
                "enabled": True,
                "category": "calculator",
                "provider": "calculator"
            },
            "solve_quadratic": {
                "enabled": True,
                "category": "calculator",
                "provider": "calculator"
            },
            "unit_converter": {
                "enabled": True,
                "category": "calculator",
                "provider": "calculator"
            },
            "statistics_calculator": {
                "enabled": True,
                "category": "calculator",
                "provider": "calculator"
            },
            "check_login_status": {
                "enabled": True,
                "category": "xiaohongshu",
                "provider": "xiaohongshu"
            },
            "publish_content": {
                "enabled": True,
                "category": "xiaohongshu",
                "provider": "xiaohongshu"
            },
            "list_feeds": {
                "enabled": True,
                "category": "xiaohongshu",
                "provider": "xiaohongshu"
            },
            "search_feeds": {
                "enabled": True,
                "category": "xiaohongshu",
                "provider": "xiaohongshu"
            },
            "get_feed_detail": {
                "enabled": True,
                "category": "xiaohongshu",
                "provider": "xiaohongshu"
            },
            "post_comment_to_feed": {
                "enabled": True,
                "category": "xiaohongshu",
                "provider": "xiaohongshu"
            },
            "user_profile": {
                "enabled": True,
                "category": "xiaohongshu",
                "provider": "xiaohongshu"
            }
        }

        # 解析默认配置
        self._parse_config({
            "providers": default_providers,
            "tools": default_tools
        })

    def get_enabled_providers(self) -> List[ToolProviderConfig]:
        """获取启用的工具提供者配置"""
        return [provider for provider in self.providers.values() if provider.enabled]

    def get_enabled_tools(self, provider: Optional[str] = None) -> List[ToolConfig]:
        """获取启用的工具配置"""
        tools = [tool for tool in self.tools.values() if tool.enabled]
        if provider:
            tools = [tool for tool in tools if tool.provider == provider]
        return tools

    def is_tool_enabled(self, tool_name: str) -> bool:
        """检查工具是否启用"""
        tool = self.tools.get(tool_name)
        return tool is not None and tool.enabled

    def is_provider_enabled(self, provider_name: str) -> bool:
        """检查提供者是否启用"""
        provider = self.providers.get(provider_name)
        return provider is not None and provider.enabled

    def get_tool_config(self, tool_name: str) -> Optional[ToolConfig]:
        """获取工具配置"""
        return self.tools.get(tool_name)

    def get_provider_config(self, provider_name: str) -> Optional[ToolProviderConfig]:
        """获取提供者配置"""
        return self.providers.get(provider_name)

    def save_config(self, config_file: Optional[str] = None):
        """保存配置到文件"""
        config_file = config_file or self.config_file

        config_data = {
            "providers": {
                name: {
                    "class": provider.provider_class,
                    "enabled": provider.enabled,
                    "config": provider.config
                }
                for name, provider in self.providers.items()
            },
            "tools": {
                name: {
                    "enabled": tool.enabled,
                    "category": tool.category,
                    "provider": tool.provider,
                    "config": tool.config
                }
                for name, tool in self.tools.items()
            }
        }

        try:
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Configuration saved to: {config_file}")
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise

    def reload_config(self):
        """重新加载配置"""
        self.providers.clear()
        self.tools.clear()
        self._load_config()

    def add_provider(self, provider_config: ToolProviderConfig):
        """添加工具提供者配置"""
        self.providers[provider_config.name] = provider_config
        self.logger.info(f"Added provider config: {provider_config.name}")

    def add_tool(self, tool_config: ToolConfig):
        """添加工具配置"""
        self.tools[tool_config.name] = tool_config
        self.logger.info(f"Added tool config: {tool_config.name}")

    def remove_provider(self, provider_name: str):
        """移除工具提供者配置"""
        if provider_name in self.providers:
            del self.providers[provider_name]
            self.logger.info(f"Removed provider config: {provider_name}")

    def remove_tool(self, tool_name: str):
        """移除工具配置"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            self.logger.info(f"Removed tool config: {tool_name}")

    def enable_tool(self, tool_name: str):
        """启用工具"""
        if tool_name in self.tools:
            self.tools[tool_name].enabled = True
            self.logger.info(f"Enabled tool: {tool_name}")

    def disable_tool(self, tool_name: str):
        """禁用工具"""
        if tool_name in self.tools:
            self.tools[tool_name].enabled = False
            self.logger.info(f"Disabled tool: {tool_name}")

    def enable_provider(self, provider_name: str):
        """启用工具提供者"""
        if provider_name in self.providers:
            self.providers[provider_name].enabled = True
            self.logger.info(f"Enabled provider: {provider_name}")

    def disable_provider(self, provider_name: str):
        """禁用工具提供者"""
        if provider_name in self.providers:
            self.providers[provider_name].enabled = False
            self.logger.info(f"Disabled provider: {provider_name}")


# 全局工具配置管理器实例
_tools_config_manager = None


def get_tools_config_manager() -> ToolsConfigManager:
    """获取全局工具配置管理器实例"""
    global _tools_config_manager
    if _tools_config_manager is None:
        _tools_config_manager = ToolsConfigManager()
    return _tools_config_manager