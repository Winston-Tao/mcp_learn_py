#!/usr/bin/env python3
"""Test client for MCP Learning Server."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx

# Add src directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.config import get_config
from src.utils.logger import configure_logging, get_logger


class MCPTestClient:
    """Test client for MCP Learning Server."""

    def __init__(self, base_url: str = None):
        """Initialize test client.

        Args:
            base_url: Base URL for HTTP transport
        """
        configure_logging()
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.base_url = base_url or f"http://{self.config.server_host}:{self.config.server_port}"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    async def test_server_health(self) -> Dict[str, Any]:
        """Test server health endpoint."""
        self.logger.info("Testing server health...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            result = response.json()
            self.logger.info("✓ Health check passed")
            return result
        except Exception as e:
            self.logger.error(f"✗ Health check failed: {e}")
            raise

    async def test_server_info(self) -> Dict[str, Any]:
        """Test server info endpoint."""
        self.logger.info("Testing server info...")
        try:
            response = await self.client.get(f"{self.base_url}/")
            response.raise_for_status()
            result = response.json()
            self.logger.info(f"✓ Server info: {result['name']} v{result['version']}")
            return result
        except Exception as e:
            self.logger.error(f"✗ Server info failed: {e}")
            raise

    async def test_mcp_initialize(self) -> Dict[str, Any]:
        """Test MCP initialization."""
        self.logger.info("Testing MCP initialization...")
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {}
                },
                "id": "test-init"
            }

            response = await self.client.post(f"{self.base_url}/mcp", json=payload)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise Exception(f"MCP error: {result['error']}")

            self.logger.info("✓ MCP initialization successful")
            return result["result"]
        except Exception as e:
            self.logger.error(f"✗ MCP initialization failed: {e}")
            raise

    async def test_list_resources(self) -> List[Dict[str, Any]]:
        """Test listing resources."""
        self.logger.info("Testing resource listing...")
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "resources/list",
                "params": {},
                "id": "test-resources"
            }

            response = await self.client.post(f"{self.base_url}/mcp", json=payload)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise Exception(f"MCP error: {result['error']}")

            resources = result["result"]["resources"]
            self.logger.info(f"✓ Found {len(resources)} resources")
            for resource in resources:
                self.logger.info(f"  - {resource['name']}: {resource['uri']}")

            return resources
        except Exception as e:
            self.logger.error(f"✗ Resource listing failed: {e}")
            raise

    async def test_list_tools(self) -> List[Dict[str, Any]]:
        """Test listing tools."""
        self.logger.info("Testing tool listing...")
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": "test-tools"
            }

            response = await self.client.post(f"{self.base_url}/mcp", json=payload)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise Exception(f"MCP error: {result['error']}")

            tools = result["result"]["tools"]
            self.logger.info(f"✓ Found {len(tools)} tools")
            for tool in tools:
                self.logger.info(f"  - {tool['name']}: {tool['description']}")

            return tools
        except Exception as e:
            self.logger.error(f"✗ Tool listing failed: {e}")
            raise

    async def test_list_prompts(self) -> List[Dict[str, Any]]:
        """Test listing prompts."""
        self.logger.info("Testing prompt listing...")
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "prompts/list",
                "params": {},
                "id": "test-prompts"
            }

            response = await self.client.post(f"{self.base_url}/mcp", json=payload)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise Exception(f"MCP error: {result['error']}")

            prompts = result["result"]["prompts"]
            self.logger.info(f"✓ Found {len(prompts)} prompts")
            for prompt in prompts:
                self.logger.info(f"  - {prompt['name']}: {prompt['description']}")

            return prompts
        except Exception as e:
            self.logger.error(f"✗ Prompt listing failed: {e}")
            raise

    async def test_call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Test calling a tool."""
        self.logger.info(f"Testing tool call: {tool_name}")
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                },
                "id": f"test-tool-{tool_name}"
            }

            response = await self.client.post(f"{self.base_url}/mcp", json=payload)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise Exception(f"MCP error: {result['error']}")

            tool_result = result["result"]
            is_error = tool_result.get("isError", False)
            status = "✗" if is_error else "✓"
            self.logger.info(f"{status} Tool call {tool_name}: {'error' if is_error else 'success'}")

            return tool_result
        except Exception as e:
            self.logger.error(f"✗ Tool call {tool_name} failed: {e}")
            raise

    async def test_get_prompt(self, prompt_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Test getting a prompt."""
        self.logger.info(f"Testing prompt: {prompt_name}")
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "prompts/get",
                "params": {
                    "name": prompt_name,
                    "arguments": arguments or {}
                },
                "id": f"test-prompt-{prompt_name}"
            }

            response = await self.client.post(f"{self.base_url}/mcp", json=payload)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise Exception(f"MCP error: {result['error']}")

            prompt_result = result["result"]
            self.logger.info(f"✓ Prompt {prompt_name}: {len(prompt_result['messages'])} messages")

            return prompt_result
        except Exception as e:
            self.logger.error(f"✗ Prompt {prompt_name} failed: {e}")
            raise

    async def run_basic_tests(self) -> Dict[str, Any]:
        """Run basic functionality tests."""
        self.logger.info("=" * 60)
        self.logger.info("Running MCP Learning Server Tests")
        self.logger.info("=" * 60)

        results = {}
        errors = []

        try:
            # Test server health
            results["health"] = await self.test_server_health()

            # Test server info
            results["info"] = await self.test_server_info()

            # Test MCP initialization
            results["initialize"] = await self.test_mcp_initialize()

            # Test listings
            results["resources"] = await self.test_list_resources()
            results["tools"] = await self.test_list_tools()
            results["prompts"] = await self.test_list_prompts()

        except Exception as e:
            errors.append(f"Basic tests failed: {e}")

        # Test tool calls if tools are available
        if "tools" in results and results["tools"]:
            try:
                # Test calculator
                calc_result = await self.test_call_tool("calculate", {"expression": "2 + 2"})
                results["tool_calculate"] = calc_result

            except Exception as e:
                errors.append(f"Tool testing failed: {e}")

        # Test prompts if prompts are available
        if "prompts" in results and results["prompts"]:
            try:
                # Test code review prompt
                prompt_result = await self.test_get_prompt("code_review", {
                    "code": "def hello(): return 'world'",
                    "language": "python"
                })
                results["prompt_code_review"] = prompt_result

            except Exception as e:
                errors.append(f"Prompt testing failed: {e}")

        # Summary
        self.logger.info("=" * 60)
        if errors:
            self.logger.error(f"Tests completed with {len(errors)} errors:")
            for error in errors:
                self.logger.error(f"  - {error}")
        else:
            self.logger.info("✓ All tests passed successfully!")
        self.logger.info("=" * 60)

        return {
            "success": len(errors) == 0,
            "error_count": len(errors),
            "errors": errors,
            "results": results
        }

    async def run_interactive_mode(self):
        """Run interactive testing mode."""
        self.logger.info("Starting interactive mode. Type 'help' for commands.")

        while True:
            try:
                command = input("mcp-test> ").strip()
                if not command:
                    continue

                if command in ["quit", "exit", "q"]:
                    break
                elif command == "help":
                    print("Available commands:")
                    print("  health        - Check server health")
                    print("  info          - Get server info")
                    print("  init          - Initialize MCP connection")
                    print("  resources     - List resources")
                    print("  tools         - List tools")
                    print("  prompts       - List prompts")
                    print("  call <tool>   - Call a tool")
                    print("  prompt <name> - Get a prompt")
                    print("  test          - Run all basic tests")
                    print("  help          - Show this help")
                    print("  quit/exit/q   - Exit")
                elif command == "health":
                    await self.test_server_health()
                elif command == "info":
                    await self.test_server_info()
                elif command == "init":
                    await self.test_mcp_initialize()
                elif command == "resources":
                    await self.test_list_resources()
                elif command == "tools":
                    await self.test_list_tools()
                elif command == "prompts":
                    await self.test_list_prompts()
                elif command == "test":
                    await self.run_basic_tests()
                elif command.startswith("call "):
                    tool_name = command[5:].strip()
                    await self.test_call_tool(tool_name)
                elif command.startswith("prompt "):
                    prompt_name = command[7:].strip()
                    await self.test_get_prompt(prompt_name)
                else:
                    print(f"Unknown command: {command}. Type 'help' for available commands.")

            except KeyboardInterrupt:
                print("\\nExiting...")
                break
            except Exception as e:
                self.logger.error(f"Command failed: {e}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MCP Learning Server Test Client")
    parser.add_argument(
        "--url",
        default=None,
        help="Base URL for the MCP server (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--test",
        "-t",
        default="basic",
        choices=["basic", "comprehensive"],
        help="Test suite to run (default: basic)"
    )

    args = parser.parse_args()

    # Determine base URL
    if args.url:
        base_url = args.url
    else:
        config = get_config()
        base_url = f"http://{config.server_host}:{config.server_port}"

    print(f"MCP Learning Server Test Client")
    print(f"Target URL: {base_url}")
    print("-" * 50)

    async with MCPTestClient(base_url) as client:
        try:
            if args.interactive:
                await client.run_interactive_mode()
            else:
                results = await client.run_basic_tests()
                if not results["success"]:
                    sys.exit(1)

        except Exception as e:
            print(f"Test client failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())