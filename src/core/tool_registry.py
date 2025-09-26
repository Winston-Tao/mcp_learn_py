"""动态工具注册管理器"""

import importlib
from typing import Dict, List, Type, Any, Optional, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from ..utils.logger import get_logger


@dataclass
class ToolSchema:
    """工具Schema定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    category: str = "general"
    enabled: bool = True


@dataclass
class ToolRegistryEntry:
    """工具注册条目"""
    schema: ToolSchema
    handler: Callable
    tool_class: Optional[Type] = None
    instance: Optional[Any] = None


class BaseToolProvider(ABC):
    """工具提供者基类"""

    @abstractmethod
    def get_tools(self) -> List[ToolSchema]:
        """获取工具列表"""
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        pass


class ToolRegistry:
    """工具注册管理器"""

    def __init__(self):
        """初始化工具注册管理器"""
        self.logger = get_logger(__name__)
        self._tools: Dict[str, ToolRegistryEntry] = {}
        self._providers: Dict[str, BaseToolProvider] = {}
        self._categories: Dict[str, List[str]] = {}

    def register_provider(self, name: str, provider: BaseToolProvider):
        """注册工具提供者"""
        self.logger.info(f"Registering tool provider: {name}")
        self._providers[name] = provider

        # 注册提供者的所有工具
        tools = provider.get_tools()
        for tool_schema in tools:
            self._register_tool_from_provider(tool_schema, provider, name)

    def _register_tool_from_provider(self, tool_schema: ToolSchema, provider: BaseToolProvider, provider_name: str):
        """从提供者注册工具"""
        if not tool_schema.enabled:
            return

        async def tool_handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
            return await provider.call_tool(tool_schema.name, arguments)

        entry = ToolRegistryEntry(
            schema=tool_schema,
            handler=tool_handler,
            tool_class=None,
            instance=provider
        )

        self._tools[tool_schema.name] = entry

        # 按类别组织
        category = tool_schema.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool_schema.name)

        self.logger.info(f"Registered tool '{tool_schema.name}' from provider '{provider_name}'")

    def register_tool(self, tool_schema: ToolSchema, handler: Callable, tool_class: Optional[Type] = None, instance: Optional[Any] = None):
        """直接注册工具"""
        if not tool_schema.enabled:
            return

        entry = ToolRegistryEntry(
            schema=tool_schema,
            handler=handler,
            tool_class=tool_class,
            instance=instance
        )

        self._tools[tool_schema.name] = entry

        # 按类别组织
        category = tool_schema.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool_schema.name)

        self.logger.info(f"Registered tool '{tool_schema.name}' in category '{category}'")

    def get_tool_schemas(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取工具Schema列表，用于MCP tools/list响应"""
        tools = []

        tool_names = self._categories.get(category, []) if category else list(self._tools.keys())

        for tool_name in tool_names:
            entry = self._tools.get(tool_name)
            if entry and entry.schema.enabled:
                tools.append({
                    "name": entry.schema.name,
                    "description": entry.schema.description,
                    "inputSchema": entry.schema.input_schema
                })

        return tools

    def get_categories(self) -> List[str]:
        """获取所有类别"""
        return list(self._categories.keys())

    def get_tools_by_category(self, category: str) -> List[str]:
        """按类别获取工具名称"""
        return self._categories.get(category, [])

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found")

        entry = self._tools[tool_name]
        if not entry.schema.enabled:
            raise ValueError(f"Tool '{tool_name}' is disabled")

        self.logger.info(f"Calling tool '{tool_name}' with arguments: {arguments}")

        try:
            result = await entry.handler(arguments)
            return result
        except Exception as e:
            self.logger.error(f"Tool '{tool_name}' execution failed: {e}")
            raise

    def is_tool_registered(self, tool_name: str) -> bool:
        """检查工具是否已注册"""
        return tool_name in self._tools and self._tools[tool_name].schema.enabled

    def get_tool_count(self) -> int:
        """获取已注册工具数量"""
        return len([tool for tool in self._tools.values() if tool.schema.enabled])

    def get_tool_info(self, tool_name: str) -> Optional[ToolSchema]:
        """获取工具信息"""
        entry = self._tools.get(tool_name)
        return entry.schema if entry else None


# 全局工具注册管理器实例
_tool_registry = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册管理器实例"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry