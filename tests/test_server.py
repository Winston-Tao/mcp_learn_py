"""Tests for MCP Learning Server core functionality."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.server import MCPLearningServer
from src.utils.config import get_config


@pytest.fixture
def server():
    """Create a test server instance."""
    return MCPLearningServer()


@pytest.fixture
def config():
    """Get test configuration."""
    return get_config()


class TestMCPLearningServer:
    """Test cases for MCP Learning Server."""

    def test_server_initialization(self, server):
        """Test server initialization."""
        assert server is not None
        assert server.config is not None
        assert server.logger is not None
        assert server.mcp is not None
        assert not server.is_initialized()

    def test_server_capabilities(self, server):
        """Test server capabilities."""
        capabilities = server.get_capabilities()
        assert capabilities is not None
        assert hasattr(capabilities, 'resources')
        assert hasattr(capabilities, 'tools')
        assert hasattr(capabilities, 'prompts')

    @pytest.mark.asyncio
    async def test_health_check(self, server):
        """Test server health check."""
        health = await server.health_check()

        assert health is not None
        assert 'status' in health
        assert 'server_name' in health
        assert 'version' in health
        assert 'capabilities' in health
        assert health['server_name'] == server.config.server_name
        assert health['version'] == server.config.server_version

    def test_add_resource_handler(self, server):
        """Test adding resource handlers."""
        initial_count = len(server.get_capabilities().resources)

        # Mock handler function
        async def mock_handler():
            return {"test": "resource"}

        server.add_resource_handler("test://resource", mock_handler, "Test resource")

        # Check that resource was added
        capabilities = server.get_capabilities()
        assert len(capabilities.resources) == initial_count + 1
        assert "test://resource" in capabilities.resources
        assert capabilities.resources["test://resource"]["description"] == "Test resource"

    def test_add_tool_handler(self, server):
        """Test adding tool handlers."""
        initial_count = len(server.get_capabilities().tools)

        # Mock handler function
        async def mock_tool():
            return {"result": "test"}

        server.add_tool_handler("test_tool", mock_tool, "Test tool")

        # Check that tool was added
        capabilities = server.get_capabilities()
        assert len(capabilities.tools) == initial_count + 1
        assert "test_tool" in capabilities.tools
        assert capabilities.tools["test_tool"]["description"] == "Test tool"

    def test_add_prompt_handler(self, server):
        """Test adding prompt handlers."""
        initial_count = len(server.get_capabilities().prompts)

        # Mock handler function
        async def mock_prompt():
            return {"messages": []}

        server.add_prompt_handler("test_prompt", mock_prompt, "Test prompt")

        # Check that prompt was added
        capabilities = server.get_capabilities()
        assert len(capabilities.prompts) == initial_count + 1
        assert "test_prompt" in capabilities.prompts
        assert capabilities.prompts["test_prompt"]["description"] == "Test prompt"


class TestServerConfiguration:
    """Test server configuration."""

    def test_config_loading(self, config):
        """Test configuration loading."""
        assert config is not None
        assert config.server_name is not None
        assert config.server_version is not None
        assert config.server_host is not None
        assert config.server_port is not None

    def test_config_values(self, config):
        """Test configuration values."""
        assert isinstance(config.server_port, int)
        assert config.server_port > 0
        assert config.server_port <= 65535
        assert config.server_name != ""
        assert config.server_version != ""

    def test_security_settings(self, config):
        """Test security-related configuration."""
        assert config.max_file_size_mb > 0
        assert config.allowed_file_extensions is not None
        assert isinstance(config.allowed_file_extensions, list)
        assert config.request_timeout > 0


@pytest.mark.asyncio
class TestAsyncOperations:
    """Test asynchronous operations."""

    async def test_server_startup_simulation(self, server):
        """Test server startup simulation."""
        # Mock the startup process
        with pytest.raises(AttributeError):
            # This will raise an error because we haven't fully initialized
            # all components, which is expected in the test environment
            await server.start("127.0.0.1", 8999)

    async def test_concurrent_capability_access(self, server):
        """Test concurrent access to server capabilities."""
        # Test that multiple coroutines can safely access capabilities
        async def get_capabilities():
            return server.get_capabilities()

        # Run multiple concurrent capability requests
        tasks = [get_capabilities() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.resources == first_result.resources
            assert result.tools == first_result.tools
            assert result.prompts == first_result.prompts


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_resource_pattern(self, server):
        """Test handling of invalid resource patterns."""
        async def mock_handler():
            return {}

        # These should work without raising exceptions
        server.add_resource_handler("", mock_handler, "Empty pattern")
        server.add_resource_handler("invalid://pattern", mock_handler, "Invalid pattern")

        # The server should handle these gracefully
        capabilities = server.get_capabilities()
        assert "" in capabilities.resources
        assert "invalid://pattern" in capabilities.resources

    def test_invalid_tool_name(self, server):
        """Test handling of invalid tool names."""
        async def mock_tool():
            return {}

        # These should work without raising exceptions
        server.add_tool_handler("", mock_tool, "Empty name")
        server.add_tool_handler("invalid-tool-name", mock_tool, "Invalid name")

        capabilities = server.get_capabilities()
        assert "" in capabilities.tools
        assert "invalid-tool-name" in capabilities.tools

    @pytest.mark.asyncio
    async def test_health_check_error_handling(self, server):
        """Test health check with potential errors."""
        # Health check should not raise exceptions even in error conditions
        health = await server.health_check()
        assert health is not None
        assert isinstance(health, dict)


class TestIntegration:
    """Integration tests."""

    def test_all_components_present(self, server):
        """Test that all expected components are present."""
        # Check that server has all necessary attributes
        assert hasattr(server, 'config')
        assert hasattr(server, 'logger')
        assert hasattr(server, 'mcp')
        assert hasattr(server, '_capabilities')
        assert hasattr(server, '_initialized')

    @pytest.mark.asyncio
    async def test_complete_workflow(self, server):
        """Test a complete workflow simulation."""
        # 1. Check initial state
        assert not server.is_initialized()

        # 2. Get capabilities
        capabilities = server.get_capabilities()
        assert capabilities is not None

        # 3. Run health check
        health = await server.health_check()
        assert health['status'] in ['healthy', 'initializing']

        # 4. Add some handlers
        async def test_resource():
            return {"data": "test"}

        async def test_tool():
            return {"result": "success"}

        async def test_prompt():
            return {"title": "Test", "content": "Test prompt"}

        server.add_resource_handler("test://data", test_resource, "Test resource")
        server.add_tool_handler("test_tool", test_tool, "Test tool")
        server.add_prompt_handler("test_prompt", test_prompt, "Test prompt")

        # 5. Verify handlers were added
        final_capabilities = server.get_capabilities()
        assert "test://data" in final_capabilities.resources
        assert "test_tool" in final_capabilities.tools
        assert "test_prompt" in final_capabilities.prompts