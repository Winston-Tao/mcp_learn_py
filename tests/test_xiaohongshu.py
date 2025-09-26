"""Tests for Xiaohongshu MCP tools."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.tools.xiaohongshu_models import (
    XiaohongshuConfig,
    PublishContentRequest,
    SearchFeedsRequest,
    FeedDetailRequest,
    PostCommentRequest,
    UserProfileRequest,
)
from src.tools.xiaohongshu_service import XiaohongshuService
from src.tools.xiaohongshu_tool import XiaohongshuTool


class TestXiaohongshuModels:
    """Test Xiaohongshu data models."""

    def test_xiaohongshu_config(self):
        """Test XiaohongshuConfig creation."""
        config = XiaohongshuConfig()
        assert config.headless is True
        assert config.timeout == 30
        assert config.max_images_per_post == 9
        assert config.max_title_length == 20

    def test_publish_content_request(self):
        """Test PublishContentRequest validation."""
        request = PublishContentRequest(
            title="测试标题",
            content="这是测试内容",
            images=["image1.jpg", "image2.jpg"]
        )
        assert request.title == "测试标题"
        assert request.content == "这是测试内容"
        assert len(request.images) == 2
        assert request.validate_title_length() is True

        # Test title length validation
        long_title_request = PublishContentRequest(
            title="这是一个非常非常非常长的标题，超过了20个字符的限制",
            content="测试内容"
        )
        assert long_title_request.validate_title_length() is False

    def test_search_feeds_request(self):
        """Test SearchFeedsRequest creation."""
        request = SearchFeedsRequest(keyword="小红书")
        assert request.keyword == "小红书"
        assert request.page == 1
        assert request.limit == 20


class TestXiaohongshuService:
    """Test Xiaohongshu service functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return XiaohongshuConfig(
            headless=True,
            timeout=10,
            max_images_per_post=5
        )

    @pytest.fixture
    def service(self, config):
        """Create test service instance."""
        return XiaohongshuService(config)

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.config is not None
        assert service.logger is not None
        assert service.base_url == "https://www.xiaohongshu.com"
        assert service.driver is None

    @patch('src.tools.xiaohongshu_service.webdriver.Chrome')
    def test_setup_driver(self, mock_chrome, service):
        """Test driver setup."""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        driver = service._setup_driver()
        assert driver == mock_driver
        mock_chrome.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup(self, service):
        """Test service cleanup."""
        # Mock driver
        mock_driver = Mock()
        mock_driver.quit = Mock()
        service.driver = mock_driver

        await service.cleanup()

        mock_driver.quit.assert_called_once()
        assert service.driver is None


class TestXiaohongshuTool:
    """Test Xiaohongshu MCP tool wrapper."""

    @pytest.fixture
    def mock_server(self):
        """Create mock MCP server."""
        server = Mock()
        server.mcp = Mock()
        server.mcp.tool = Mock(return_value=lambda func: func)
        return server

    @pytest.fixture
    def tool(self, mock_server):
        """Create test tool instance."""
        with patch('src.tools.xiaohongshu_tool.get_config') as mock_config:
            # Mock server config
            mock_config.return_value = Mock(
                xiaohongshu_headless=True,
                xiaohongshu_browser_path=None,
                xiaohongshu_timeout=30,
                xiaohongshu_max_images_per_post=9,
                xiaohongshu_max_title_length=20,
                xiaohongshu_max_content_length=1000
            )
            return XiaohongshuTool(mock_server)

    def test_tool_initialization(self, tool):
        """Test tool initialization."""
        assert tool.server is not None
        assert tool.mcp is not None
        assert tool.logger is not None
        assert tool.config is not None
        assert tool.service is not None

    @pytest.mark.asyncio
    async def test_register_tools(self, tool):
        """Test tool registration."""
        # Mock the service methods to avoid actual browser operations
        tool.service.check_login_status = AsyncMock(return_value=Mock(
            is_logged_in=False,
            message="未登录",
            user_info=None
        ))

        await tool.register()

        # Verify that tool registration was called
        assert tool.mcp.tool.called

    @pytest.mark.asyncio
    async def test_cleanup(self, tool):
        """Test tool cleanup."""
        tool.service.cleanup = AsyncMock()

        await tool.cleanup()

        tool.service.cleanup.assert_called_once()


class TestIntegration:
    """Integration tests for Xiaohongshu functionality."""

    @pytest.mark.asyncio
    @patch('src.tools.xiaohongshu_service.webdriver.Chrome')
    async def test_check_login_status_integration(self, mock_chrome):
        """Test login status check integration."""
        # Setup mock driver
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_driver.get = Mock()
        mock_driver.find_element = Mock(side_effect=Exception("Element not found"))

        config = XiaohongshuConfig(headless=True)
        service = XiaohongshuService(config)

        try:
            # This will fail due to mocked browser, but tests the flow
            result = await service.check_login_status()

            # Should return not logged in due to exception
            assert result.is_logged_in is False
            assert "未登录" in result.message or "失败" in result.message

        finally:
            await service.cleanup()

    def test_models_integration(self):
        """Test that models work together properly."""
        # Test publish request
        publish_req = PublishContentRequest(
            title="测试",
            content="内容",
            images=["test.jpg"]
        )

        # Test search request
        search_req = SearchFeedsRequest(keyword="测试", page=1, limit=10)

        # Test feed detail request
        detail_req = FeedDetailRequest(feed_id="123", xsec_token="token")

        # Test comment request
        comment_req = PostCommentRequest(
            feed_id="123",
            xsec_token="token",
            content="评论内容"
        )

        # Test user profile request
        profile_req = UserProfileRequest(user_id="456", xsec_token="token")

        # All should be valid
        assert publish_req.validate_title_length() is True
        assert search_req.keyword == "测试"
        assert detail_req.feed_id == "123"
        assert comment_req.content == "评论内容"
        assert profile_req.user_id == "456"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])