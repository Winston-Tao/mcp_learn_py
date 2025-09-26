"""内置工具提供者实现"""

from typing import Dict, List, Any
import json

from .tool_registry import BaseToolProvider, ToolSchema
from ..tools.calculator import CalculatorTool
from ..tools.xiaohongshu_tool import XiaohongshuTool
from ..tools.xiaohongshu_models import (
    PublishContentRequest,
    SearchFeedsRequest,
    FeedDetailRequest,
    PostCommentRequest,
    UserProfileRequest
)
from ..utils.logger import get_logger


class CalculatorToolProvider(BaseToolProvider):
    """计算器工具提供者"""

    def __init__(self, server):
        self.server = server
        self.calculator_tool = CalculatorTool(server)
        self.logger = get_logger(__name__)

    def get_tools(self) -> List[ToolSchema]:
        """获取计算器工具列表"""
        return [
            ToolSchema(
                name="calculate",
                description="Perform mathematical calculations",
                input_schema={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate"
                        }
                    },
                    "required": ["expression"]
                },
                category="calculator"
            ),
            ToolSchema(
                name="solve_quadratic",
                description="Solve quadratic equation ax² + bx + c = 0",
                input_schema={
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "Coefficient of x²"},
                        "b": {"type": "number", "description": "Coefficient of x"},
                        "c": {"type": "number", "description": "Constant term"}
                    },
                    "required": ["a", "b", "c"]
                },
                category="calculator"
            ),
            ToolSchema(
                name="unit_converter",
                description="Convert between different units",
                input_schema={
                    "type": "object",
                    "properties": {
                        "value": {"type": "number", "description": "Value to convert"},
                        "from_unit": {"type": "string", "description": "Source unit"},
                        "to_unit": {"type": "string", "description": "Target unit"},
                        "unit_type": {
                            "type": "string",
                            "description": "Type of unit",
                            "default": "length"
                        }
                    },
                    "required": ["value", "from_unit", "to_unit"]
                },
                category="calculator"
            ),
            ToolSchema(
                name="statistics_calculator",
                description="Calculate statistical measures for a list of numbers",
                input_schema={
                    "type": "object",
                    "properties": {
                        "numbers": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "List of numbers"
                        },
                        "operation": {
                            "type": "string",
                            "description": "Statistic to calculate",
                            "default": "all"
                        }
                    },
                    "required": ["numbers"]
                },
                category="calculator"
            )
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用计算器工具"""
        try:
            if tool_name == "calculate":
                result = await self.calculator_tool._calculate(arguments.get("expression", ""))
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Result: {result.formatted_result}\n\nExpression: {result.expression}\nResult Type: {result.result_type}"
                    }]
                }

            elif tool_name == "solve_quadratic":
                a = arguments.get("a", 0)
                b = arguments.get("b", 0)
                c = arguments.get("c", 0)
                result = await self.calculator_tool._solve_quadratic(a, b, c)
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Equation: {result['equation']}\nType: {result['type']}\nSolutions: {result['solutions']}\nMessage: {result['message']}"
                    }]
                }

            elif tool_name == "unit_converter":
                value = arguments.get("value", 0)
                from_unit = arguments.get("from_unit", "")
                to_unit = arguments.get("to_unit", "")
                unit_type = arguments.get("unit_type", "length")
                result = await self.calculator_tool._unit_converter(value, from_unit, to_unit, unit_type)
                return {
                    "content": [{
                        "type": "text",
                        "text": result["formatted_result"]
                    }]
                }

            elif tool_name == "statistics_calculator":
                numbers = arguments.get("numbers", [])
                operation = arguments.get("operation", "all")
                result = await self.calculator_tool._statistics_calculator(numbers, operation)
                stats_text = f"Numbers: {result['numbers']}\nOperation: {result['operation']}\n\nStatistics:\n"
                for key, value in result['statistics'].items():
                    stats_text += f"{key}: {value}\n"
                return {
                    "content": [{
                        "type": "text",
                        "text": stats_text
                    }]
                }

            else:
                raise ValueError(f"Unknown calculator tool: {tool_name}")

        except Exception as e:
            self.logger.error(f"Calculator tool '{tool_name}' error: {e}")
            raise


class XiaohongshuToolProvider(BaseToolProvider):
    """小红书工具提供者"""

    def __init__(self, server):
        self.server = server
        self.xiaohongshu_tool = XiaohongshuTool(server)
        self.logger = get_logger(__name__)

    def get_tools(self) -> List[ToolSchema]:
        """获取小红书工具列表"""
        return [
            ToolSchema(
                name="check_login_status",
                description="检查小红书登录状态（无参数）",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                category="xiaohongshu"
            ),
            ToolSchema(
                name="publish_content",
                description="发布图文内容到小红书",
                input_schema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the post (max 20 characters)"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content of the post"
                        },
                        "images": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of image URLs or local file paths (optional)",
                            "default": []
                        }
                    },
                    "required": ["title", "content"]
                },
                category="xiaohongshu"
            ),
            ToolSchema(
                name="list_feeds",
                description="获取小红书首页推荐列表（无参数）",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                category="xiaohongshu"
            ),
            ToolSchema(
                name="search_feeds",
                description="搜索小红书内容",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "Search keyword"},
                        "page": {"type": "integer", "description": "Page number", "default": 1},
                        "limit": {"type": "integer", "description": "Number of results per page", "default": 20}
                    },
                    "required": ["keyword"]
                },
                category="xiaohongshu"
            ),
            ToolSchema(
                name="get_feed_detail",
                description="获取帖子详情",
                input_schema={
                    "type": "object",
                    "properties": {
                        "feed_id": {"type": "string", "description": "Feed ID"},
                        "xsec_token": {"type": "string", "description": "Security token for the feed"}
                    },
                    "required": ["feed_id", "xsec_token"]
                },
                category="xiaohongshu"
            ),
            ToolSchema(
                name="post_comment_to_feed",
                description="发表评论到小红书帖子",
                input_schema={
                    "type": "object",
                    "properties": {
                        "feed_id": {"type": "string", "description": "Feed ID to comment on"},
                        "xsec_token": {"type": "string", "description": "Security token for the feed"},
                        "content": {"type": "string", "description": "Comment content"}
                    },
                    "required": ["feed_id", "xsec_token", "content"]
                },
                category="xiaohongshu"
            ),
            ToolSchema(
                name="user_profile",
                description="获取用户个人主页信息",
                input_schema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID"},
                        "xsec_token": {"type": "string", "description": "Security token"}
                    },
                    "required": ["user_id", "xsec_token"]
                },
                category="xiaohongshu"
            )
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用小红书工具"""
        try:
            if tool_name == "check_login_status":
                result = await self.xiaohongshu_tool.service.check_login_status()
                response_text = f"""登录状态检查结果：
状态: {'已登录' if result.is_logged_in else '未登录'}
消息: {result.message}"""
                if result.user_info:
                    response_text += f"\n用户信息: {json.dumps(result.user_info, ensure_ascii=False, indent=2)}"

                return {
                    "content": [{
                        "type": "text",
                        "text": response_text
                    }]
                }

            elif tool_name == "publish_content":
                title = arguments.get("title", "")
                content = arguments.get("content", "")
                images = arguments.get("images", [])

                request = PublishContentRequest(
                    title=title,
                    content=content,
                    images=images
                )

                result = await self.xiaohongshu_tool.service.publish_content(request)
                response_text = f"""发布结果：
成功: {'是' if result.success else '否'}
消息: {result.message}"""
                if result.feed_id:
                    response_text += f"\n帖子ID: {result.feed_id}"
                if result.url:
                    response_text += f"\n链接: {result.url}"

                return {
                    "content": [{
                        "type": "text",
                        "text": response_text
                    }]
                }

            elif tool_name == "list_feeds":
                result = await self.xiaohongshu_tool.service.list_feeds()
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

                return {
                    "content": [{
                        "type": "text",
                        "text": response_text
                    }]
                }

            elif tool_name == "search_feeds":
                keyword = arguments.get("keyword", "")
                page = arguments.get("page", 1)
                limit = arguments.get("limit", 20)

                request = SearchFeedsRequest(
                    keyword=keyword,
                    page=page,
                    limit=limit
                )

                result = await self.xiaohongshu_tool.service.search_feeds(request)
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

                return {
                    "content": [{
                        "type": "text",
                        "text": response_text
                    }]
                }

            elif tool_name == "get_feed_detail":
                feed_id = arguments.get("feed_id", "")
                xsec_token = arguments.get("xsec_token", "")

                request = FeedDetailRequest(
                    feed_id=feed_id,
                    xsec_token=xsec_token
                )

                result = await self.xiaohongshu_tool.service.get_feed_detail(request)
                feed = result.feed
                response_text = f"""帖子详情：
标题: {feed.title}
作者: {feed.author} (ID: {feed.author_id})
内容: {feed.content}
数据: 点赞 {feed.like_count} | 评论 {feed.comment_count} | 分享 {feed.share_count}"""

                if feed.images:
                    response_text += f"\n图片数量: {len(feed.images)}"
                if feed.create_time:
                    response_text += f"\n发布时间: {feed.create_time}"

                if result.comments:
                    response_text += f"\n\n评论 (共{result.total_comments}条):\n"
                    for i, comment in enumerate(result.comments[:10], 1):
                        response_text += f"  {i}. {comment.author}: {comment.content}\n"
                        if comment.like_count > 0:
                            response_text += f"     点赞: {comment.like_count}\n"
                        for reply in comment.replies[:3]:
                            response_text += f"       └ {reply.author}: {reply.content}\n"

                return {
                    "content": [{
                        "type": "text",
                        "text": response_text
                    }]
                }

            elif tool_name == "post_comment_to_feed":
                feed_id = arguments.get("feed_id", "")
                xsec_token = arguments.get("xsec_token", "")
                content = arguments.get("content", "")

                request = PostCommentRequest(
                    feed_id=feed_id,
                    xsec_token=xsec_token,
                    content=content
                )

                result = await self.xiaohongshu_tool.service.post_comment_to_feed(request)
                response_text = f"""评论结果：
成功: {'是' if result.success else '否'}
消息: {result.message}"""
                if result.comment_id:
                    response_text += f"\n评论ID: {result.comment_id}"

                return {
                    "content": [{
                        "type": "text",
                        "text": response_text
                    }]
                }

            elif tool_name == "user_profile":
                user_id = arguments.get("user_id", "")
                xsec_token = arguments.get("xsec_token", "")

                request = UserProfileRequest(
                    user_id=user_id,
                    xsec_token=xsec_token
                )

                result = await self.xiaohongshu_tool.service.user_profile(request)
                user = result.user
                response_text = f"""用户资料：
用户名: {user.username}
昵称: {user.nickname}
ID: {user.user_id}
描述: {user.description or '无'}
认证: {'是' if user.is_verified else '否'}"""

                if user.verification_info:
                    response_text += f"\n认证信息: {user.verification_info}"

                response_text += f"""

统计数据:
  关注者: {user.followers_count}
  关注中: {user.following_count}
  帖子: {user.posts_count}
  获赞: {user.likes_count}"""

                if result.recent_posts:
                    response_text += f"\n\n最近帖子 ({len(result.recent_posts)}条):\n"
                    for i, post in enumerate(result.recent_posts[:5], 1):
                        response_text += f"  {i}. {post.title}\n"
                        response_text += f"     ID: {post.feed_id} | 点赞: {post.like_count}\n"

                return {
                    "content": [{
                        "type": "text",
                        "text": response_text
                    }]
                }

            else:
                raise ValueError(f"Unknown xiaohongshu tool: {tool_name}")

        except Exception as e:
            self.logger.error(f"Xiaohongshu tool '{tool_name}' error: {e}")
            raise