"""Configuration management for MCP Learning Server."""

import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server Configuration
    server_name: str = Field(default="MCP Learning Server", env="MCP_SERVER_NAME")
    server_version: str = Field(default="0.1.0", env="MCP_SERVER_VERSION")
    server_host: str = Field(default="0.0.0.0", env="MCP_SERVER_HOST")
    server_port: int = Field(default=8000, env="MCP_SERVER_PORT")

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    allowed_hosts: str = Field(default="localhost,127.0.0.1,0.0.0.0", env="ALLOWED_HOSTS")

    # File Operations Settings
    max_file_size_mb: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    allowed_file_extensions: str = Field(
        default=".txt,.json,.csv,.md,.py,.js,.html,.xml",
        env="ALLOWED_FILE_EXTENSIONS"
    )
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")

    # Web Scraping Settings
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    max_concurrent_requests: int = Field(default=5, env="MAX_CONCURRENT_REQUESTS")
    user_agent: str = Field(default="MCP-Learning-Server/1.0", env="USER_AGENT")

    # Monitoring and Logging
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")

    # Xiaohongshu Settings
    xiaohongshu_headless: bool = Field(default=True, env="XIAOHONGSHU_HEADLESS")
    xiaohongshu_browser_path: Optional[str] = Field(default=None, env="XIAOHONGSHU_BROWSER_PATH")
    xiaohongshu_timeout: int = Field(default=30, env="XIAOHONGSHU_TIMEOUT")
    xiaohongshu_max_images_per_post: int = Field(default=9, env="XIAOHONGSHU_MAX_IMAGES_PER_POST")
    xiaohongshu_max_title_length: int = Field(default=20, env="XIAOHONGSHU_MAX_TITLE_LENGTH")
    xiaohongshu_max_content_length: int = Field(default=1000, env="XIAOHONGSHU_MAX_CONTENT_LENGTH")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def get_allowed_hosts(self) -> List[str]:
        """Parse allowed hosts from comma-separated string."""
        return [host.strip() for host in self.allowed_hosts.split(",")]

    def get_allowed_file_extensions(self) -> List[str]:
        """Parse allowed file extensions from comma-separated string."""
        return [ext.strip() for ext in self.allowed_file_extensions.split(",")]


# Global settings instance
_settings: Optional[Settings] = None


def get_config() -> Settings:
    """Get application configuration.

    Returns:
        Settings: The application settings instance.
    """
    global _settings

    if _settings is None:
        # Load environment variables from .env file
        load_dotenv()
        _settings = Settings()

    return _settings


def reload_config() -> Settings:
    """Reload configuration from environment.

    Returns:
        Settings: The reloaded application settings instance.
    """
    global _settings
    load_dotenv(override=True)
    _settings = Settings()
    return _settings


def get_env_info() -> Dict[str, str]:
    """Get environment information for debugging.

    Returns:
        Dict[str, str]: Environment information.
    """
    config = get_config()
    return {
        "environment": config.environment,
        "debug": str(config.debug),
        "log_level": config.log_level,
        "server_host": config.server_host,
        "server_port": str(config.server_port),
        "python_version": os.sys.version,
        "working_directory": os.getcwd(),
    }