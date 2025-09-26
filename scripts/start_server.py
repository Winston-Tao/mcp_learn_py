#!/usr/bin/env python3
"""启动MCP学习服务器"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.http_server import start_http_server
from src.utils.logger import get_logger
from src.utils.config import get_config
from src.config.tools_config import get_tools_config_manager

logger = get_logger(__name__)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP Learning Server with Dynamic Tool Registry")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport protocol to use (default: stdio)"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind HTTP server (default: from config)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind HTTP server (default: from config)"
    )
    parser.add_argument(
        "--config",
        help="Path to tools configuration file"
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tools and exit"
    )
    parser.add_argument(
        "--reload-config",
        action="store_true",
        help="Reload tools configuration and exit"
    )

    args = parser.parse_args()

    # 获取配置
    config = get_config()
    tools_config = get_tools_config_manager()

    # 如果指定了配置文件
    if args.config:
        tools_config.config_file = args.config
        tools_config.reload_config()

    # 处理工具列表请求
    if args.list_tools:
        print("Available Tools:")
        print("=" * 50)

        providers = tools_config.get_enabled_providers()
        for provider in providers:
            print(f"\nProvider: {provider.name} ({provider.provider_class})")
            provider_tools = tools_config.get_enabled_tools(provider.name)
            for tool in provider_tools:
                status = "✓" if tool.enabled else "✗"
                print(f"  {status} {tool.name} ({tool.category})")

        print(f"\nTotal: {len(tools_config.get_enabled_tools())} enabled tools")
        return

    # 处理配置重载请求
    if args.reload_config:
        print("Reloading tools configuration...")
        tools_config.reload_config()
        print("Configuration reloaded successfully!")
        return

    # 启动服务器
    if args.transport == "stdio":
        logger.info("STDIO transport is not implemented, using HTTP transport")
        args.transport = "http"

    if args.transport == "http":
        logger.info("Starting MCP Learning Server with HTTP transport")
        try:
            await start_http_server(host=args.host, port=args.port)
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)