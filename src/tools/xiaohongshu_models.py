"""Data models for Xiaohongshu MCP implementation."""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from pydantic import BaseModel, Field


class LoginStatusResponse(BaseModel):
    """Response for login status check."""
    is_logged_in: bool
    user_info: Optional[Dict[str, Any]] = None
    message: str


class LoginQrcodeResponse(BaseModel):
    """Response for login QR code request."""
    timeout: str = Field(..., description="Timeout duration as string (e.g., '4m0s')")
    is_logged_in: bool = Field(..., description="Whether user is already logged in")
    img: Optional[str] = Field(None, description="Base64 encoded QR code image")


class LoginQrcodeRequest(BaseModel):
    """Request for getting login QR code."""
    timeout_seconds: int = Field(default=240, description="QR code timeout in seconds")


class PublishContentRequest(BaseModel):
    """Request for publishing content."""
    title: str = Field(..., description="Title of the post (max 20 characters)")
    content: str = Field(..., description="Content of the post")
    images: List[str] = Field(default=[], description="List of image URLs or local paths")

    def validate_title_length(self) -> bool:
        """Validate title length according to Xiaohongshu requirements."""
        return len(self.title) <= 20


class PublishContentResponse(BaseModel):
    """Response for publish content operation."""
    success: bool
    feed_id: Optional[str] = None
    message: str
    url: Optional[str] = None


class Feed(BaseModel):
    """Represents a Xiaohongshu feed/post."""
    feed_id: str
    title: str
    content: str
    author: str
    author_id: str
    images: List[str] = Field(default=[])
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    create_time: Optional[str] = None
    xsec_token: Optional[str] = None


class ListFeedsResponse(BaseModel):
    """Response for listing feeds."""
    feeds: List[Feed]
    total_count: int
    has_more: bool = False
    next_cursor: Optional[str] = None


class SearchFeedsRequest(BaseModel):
    """Request for searching feeds."""
    keyword: str = Field(..., description="Search keyword")
    page: int = Field(default=1, description="Page number")
    limit: int = Field(default=20, description="Number of results per page")


class SearchFeedsResponse(BaseModel):
    """Response for searching feeds."""
    feeds: List[Feed]
    total_count: int
    keyword: str
    page: int
    has_more: bool = False


class FeedDetailRequest(BaseModel):
    """Request for getting feed detail."""
    feed_id: str = Field(..., description="Feed ID")
    xsec_token: str = Field(..., description="Security token for the feed")


class Comment(BaseModel):
    """Represents a comment on a feed."""
    comment_id: str
    content: str
    author: str
    author_id: str
    like_count: int = 0
    create_time: Optional[str] = None
    replies: List["Comment"] = Field(default=[])


class FeedDetailResponse(BaseModel):
    """Response for feed detail."""
    feed: Feed
    comments: List[Comment] = Field(default=[])
    total_comments: int = 0


class PostCommentRequest(BaseModel):
    """Request for posting a comment."""
    feed_id: str = Field(..., description="Feed ID to comment on")
    xsec_token: str = Field(..., description="Security token for the feed")
    content: str = Field(..., description="Comment content")


class PostCommentResponse(BaseModel):
    """Response for posting a comment."""
    success: bool
    comment_id: Optional[str] = None
    message: str


class UserProfileRequest(BaseModel):
    """Request for getting user profile."""
    user_id: str = Field(..., description="User ID")
    xsec_token: str = Field(..., description="Security token")


class UserProfile(BaseModel):
    """Represents user profile information."""
    user_id: str
    username: str
    nickname: str
    avatar: Optional[str] = None
    description: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    likes_count: int = 0
    is_verified: bool = False
    verification_info: Optional[str] = None


class UserProfileResponse(BaseModel):
    """Response for user profile."""
    user: UserProfile
    recent_posts: List[Feed] = Field(default=[])


class XiaohongshuError(Exception):
    """Custom exception for Xiaohongshu operations."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


@dataclass
class XiaohongshuConfig:
    """Configuration for Xiaohongshu service."""
    headless: bool = True
    browser_path: Optional[str] = None
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    timeout: int = 30
    max_images_per_post: int = 9
    max_title_length: int = 20
    max_content_length: int = 1000