"""Xiaohongshu MCP tools implementation."""

import json
from typing import Any, Dict, List, Optional

from mcp.server.models import InitializationOptions
import mcp.types as types

from ..utils.logger import get_logger
from .xiaohongshu_service import XiaohongshuService
from .xiaohongshu_models import (
    XiaohongshuConfig,
    PublishContentRequest,
    SearchFeedsRequest,
    FeedDetailRequest,
    PostCommentRequest,
    UserProfileRequest,
    LoginQrcodeRequest,
)


class XiaohongshuTool:
    """MCP tool wrapper for Xiaohongshu functionality."""

    def __init__(self, server):
        """Initialize Xiaohongshu tool.

        Args:
            server: MCP server instance
        """
        self.server = server
        self.mcp = server.mcp
        self.logger = get_logger(__name__)

        # Initialize Xiaohongshu service with config from server settings
        from ..utils.config import get_config
        server_config = get_config()

        self.config = XiaohongshuConfig(
            headless=server_config.xiaohongshu_headless,
            browser_path=server_config.xiaohongshu_browser_path,
            timeout=server_config.xiaohongshu_timeout,
            max_images_per_post=server_config.xiaohongshu_max_images_per_post,
            max_title_length=server_config.xiaohongshu_max_title_length,
            max_content_length=server_config.xiaohongshu_max_content_length
        )
        self.service = XiaohongshuService(self.config)

        self.logger.info("Xiaohongshu MCP tool initialized")

    async def register(self):
        """Register Xiaohongshu tools with MCP server."""

        @self.mcp.tool()
        async def check_login_status() -> List[types.TextContent]:
            """Check Xiaohongshu login status.

            No parameters required.
            """
            try:
                result = await self.service.check_login_status()

                response_text = f"""登录状态检查结果：
状态: {'已登录' if result.is_logged_in else '未登录'}
消息: {result.message}
"""
                if result.user_info:
                    response_text += f"用户信息: {json.dumps(result.user_info, ensure_ascii=False, indent=2)}"

                return [types.TextContent(type="text", text=response_text)]

            except Exception as e:
                self.logger.error(f"Check login status failed: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"检查登录状态失败: {str(e)}"
                )]

        @self.mcp.tool()
        async def get_login_qrcode(
            timeout_seconds: int = 240
        ) -> List[types.TextContent | types.ImageContent]:
            """Get login QR code for Xiaohongshu authentication.

            Args:
                timeout_seconds: QR code timeout in seconds (default: 240)
            """
            try:
                request = LoginQrcodeRequest(timeout_seconds=timeout_seconds)
                result = await self.service.get_login_qrcode(request)

                if result.is_logged_in:
                    return [types.TextContent(
                        type="text",
                        text="您当前已处于登录状态，无需扫码"
                    )]

                if not result.img:
                    return [types.TextContent(
                        type="text",
                        text="无法获取登录二维码，请检查网络连接或稍后重试"
                    )]

                # Return both text and image
                content = [
                    types.TextContent(
                        type="text",
                        text=f"请使用小红书App扫描下方二维码登录\n超时时间: {result.timeout}"
                    ),
                    types.ImageContent(
                        type="image",
                        data=result.img,
                        mimeType="image/png"
                    )
                ]

                return content

            except Exception as e:
                self.logger.error(f"Get login QR code failed: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"获取登录二维码失败: {str(e)}"
                )]

        @self.mcp.tool()
        async def wait_for_login(
            timeout_seconds: int = 300
        ) -> List[types.TextContent]:
            """Wait for user to complete login process.

            Args:
                timeout_seconds: Maximum time to wait in seconds (default: 300)
            """
            try:
                success = await self.service.wait_for_login(timeout_seconds)

                if success:
                    return [types.TextContent(
                        type="text",
                        text="登录成功！登录状态已自动保存，下次使用时将自动恢复"
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"登录等待超时（{timeout_seconds}秒），请重试或检查是否已完成登录"
                    )]

            except Exception as e:
                self.logger.error(f"Wait for login failed: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"等待登录失败: {str(e)}"
                )]

        @self.mcp.tool()
        async def publish_content(
            title: str,
            content: str,
            images: Optional[List[str]] = None
        ) -> List[types.TextContent]:
            """Publish content to Xiaohongshu.

            Args:
                title: Title of the post (max 20 characters)
                content: Content of the post
                images: List of image URLs or local file paths (optional)
            """
            try:
                if images is None:
                    images = []

                request = PublishContentRequest(
                    title=title,
                    content=content,
                    images=images
                )

                result = await self.service.publish_content(request)

                response_text = f"""发布结果：
成功: {'是' if result.success else '否'}
消息: {result.message}
"""
                if result.feed_id:
                    response_text += f"帖子ID: {result.feed_id}\n"
                if result.url:
                    response_text += f"链接: {result.url}\n"

                return [types.TextContent(type="text", text=response_text)]

            except Exception as e:
                self.logger.error(f"Publish content failed: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"发布内容失败: {str(e)}"
                )]

        @self.mcp.tool()
        async def list_feeds() -> List[types.TextContent]:
            """Get list of recommended feeds from Xiaohongshu homepage.

            No parameters required.
            """
            try:
                result = await self.service.list_feeds()

                response_text = f"首页推荐列表 (共{result.total_count}条)：\n\n"

                for i, feed in enumerate(result.feeds, 1):
                    response_text += f"{i}. {feed.title}\n"
                    response_text += f"   作者: {feed.author}\n"
                    response_text += f"   ID: {feed.feed_id}\n"
                    if feed.xsec_token:
                        response_text += f"   Token: {feed.xsec_token}\n"
                    response_text += f"   点赞: {feed.like_count} | 评论: {feed.comment_count}\n\n"

                if result.has_more:
                    response_text += "注意: 还有更多内容可以获取\n"

                return [types.TextContent(type="text", text=response_text)]

            except Exception as e:
                self.logger.error(f"List feeds failed: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"获取推荐列表失败: {str(e)}"
                )]

        @self.mcp.tool()
        async def search_feeds(keyword: str, page: int = 1, limit: int = 20) -> List[types.TextContent]:
            """Search feeds by keyword.

            Args:
                keyword: Search keyword
                page: Page number (default: 1)
                limit: Number of results per page (default: 20)
            """
            try:
                request = SearchFeedsRequest(
                    keyword=keyword,
                    page=page,
                    limit=limit
                )

                result = await self.service.search_feeds(request)

                response_text = f"搜索结果 - 关键词: '{result.keyword}' (第{result.page}页，共{result.total_count}条)：\n\n"

                for i, feed in enumerate(result.feeds, 1):
                    response_text += f"{i}. {feed.title}\n"
                    response_text += f"   作者: {feed.author}\n"
                    response_text += f"   ID: {feed.feed_id}\n"
                    if feed.xsec_token:
                        response_text += f"   Token: {feed.xsec_token}\n"
                    response_text += f"   点赞: {feed.like_count} | 评论: {feed.comment_count}\n\n"

                if result.has_more:
                    response_text += "注意: 还有更多搜索结果\n"

                return [types.TextContent(type="text", text=response_text)]

            except Exception as e:
                self.logger.error(f"Search feeds failed: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"搜索失败: {str(e)}"
                )]

        @self.mcp.tool()
        async def get_feed_detail(feed_id: str, xsec_token: str) -> List[types.TextContent]:
            """Get detailed information about a specific feed.

            Args:
                feed_id: Feed ID
                xsec_token: Security token for the feed
            """
            try:
                request = FeedDetailRequest(
                    feed_id=feed_id,
                    xsec_token=xsec_token
                )

                result = await self.service.get_feed_detail(request)

                feed = result.feed
                response_text = f"""帖子详情：
标题: {feed.title}
作者: {feed.author} (ID: {feed.author_id})
内容: {feed.content}
数据: 点赞 {feed.like_count} | 评论 {feed.comment_count} | 分享 {feed.share_count}
"""

                if feed.images:
                    response_text += f"图片数量: {len(feed.images)}\n"

                if feed.create_time:
                    response_text += f"发布时间: {feed.create_time}\n"

                # Add comments section
                if result.comments:
                    response_text += f"\n评论 (共{result.total_comments}条):\n"
                    for i, comment in enumerate(result.comments[:10], 1):  # Show first 10 comments
                        response_text += f"  {i}. {comment.author}: {comment.content}\n"
                        if comment.like_count > 0:
                            response_text += f"     点赞: {comment.like_count}\n"

                        # Show first level replies
                        for reply in comment.replies[:3]:  # Show first 3 replies
                            response_text += f"       └ {reply.author}: {reply.content}\n"

                return [types.TextContent(type="text", text=response_text)]

            except Exception as e:
                self.logger.error(f"Get feed detail failed: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"获取帖子详情失败: {str(e)}"
                )]

        @self.mcp.tool()
        async def post_comment_to_feed(
            feed_id: str,
            xsec_token: str,
            content: str
        ) -> List[types.TextContent]:
            """Post a comment to a specific feed.

            Args:
                feed_id: Feed ID to comment on
                xsec_token: Security token for the feed
                content: Comment content
            """
            try:
                request = PostCommentRequest(
                    feed_id=feed_id,
                    xsec_token=xsec_token,
                    content=content
                )

                result = await self.service.post_comment_to_feed(request)

                response_text = f"""评论结果：
成功: {'是' if result.success else '否'}
消息: {result.message}
"""
                if result.comment_id:
                    response_text += f"评论ID: {result.comment_id}\n"

                return [types.TextContent(type="text", text=response_text)]

            except Exception as e:
                self.logger.error(f"Post comment failed: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"发表评论失败: {str(e)}"
                )]

        @self.mcp.tool()
        async def user_profile(user_id: str, xsec_token: str) -> List[types.TextContent]:
            """Get user profile information.

            Args:
                user_id: User ID
                xsec_token: Security token
            """
            try:
                request = UserProfileRequest(
                    user_id=user_id,
                    xsec_token=xsec_token
                )

                result = await self.service.user_profile(request)

                user = result.user
                response_text = f"""用户资料：
用户名: {user.username}
昵称: {user.nickname}
ID: {user.user_id}
描述: {user.description or '无'}
认证: {'是' if user.is_verified else '否'}
"""

                if user.verification_info:
                    response_text += f"认证信息: {user.verification_info}\n"

                response_text += f"""
统计数据:
  关注者: {user.followers_count}
  关注中: {user.following_count}
  帖子: {user.posts_count}
  获赞: {user.likes_count}
"""

                # Add recent posts
                if result.recent_posts:
                    response_text += f"\n最近帖子 ({len(result.recent_posts)}条):\n"
                    for i, post in enumerate(result.recent_posts[:5], 1):  # Show first 5 posts
                        response_text += f"  {i}. {post.title}\n"
                        response_text += f"     ID: {post.feed_id} | 点赞: {post.like_count}\n"

                return [types.TextContent(type="text", text=response_text)]

            except Exception as e:
                self.logger.error(f"Get user profile failed: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"获取用户资料失败: {str(e)}"
                )]

        self.logger.info("Xiaohongshu tools registered successfully")

    async def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, 'service') and self.service:
            await self.service.cleanup()