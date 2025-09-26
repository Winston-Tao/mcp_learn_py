"""Cookie persistence manager for browser automation."""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from .logger import get_logger


class CookieManager:
    """Manages browser cookie persistence for login sessions."""

    def __init__(self, cookies_path: Optional[str] = None):
        """Initialize cookie manager.

        Args:
            cookies_path: Custom path for cookie storage. If None, uses environment
                         variable COOKIES_PATH or defaults to 'cookies.json'
        """
        self.logger = get_logger(__name__)
        self.cookies_path = self._get_cookies_path(cookies_path)

    def _get_cookies_path(self, custom_path: Optional[str] = None) -> Path:
        """Get the path for cookie storage with fallback logic.

        Args:
            custom_path: Custom cookie file path

        Returns:
            Path object for cookie storage
        """
        if custom_path:
            return Path(custom_path)

        # Check environment variable
        env_path = os.getenv("COOKIES_PATH")
        if env_path:
            return Path(env_path)

        # For backward compatibility, check if old path exists
        old_path = Path("/tmp/cookies.json")
        if old_path.exists():
            self.logger.info(f"Using existing cookie file at {old_path}")
            return old_path

        # Default to current directory
        return Path("cookies.json")

    def save_cookies(self, cookies: List[Dict[str, Any]]) -> bool:
        """Save browser cookies to file.

        Args:
            cookies: List of cookie dictionaries from Selenium WebDriver

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            self.cookies_path.parent.mkdir(parents=True, exist_ok=True)

            # Serialize cookies to JSON
            cookies_data = {
                "cookies": cookies,
                "timestamp": str(int(time.time() * 1000)),  # Unix timestamp in ms
                "domain": "xiaohongshu.com"
            }

            with open(self.cookies_path, 'w', encoding='utf-8') as f:
                json.dump(cookies_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Saved {len(cookies)} cookies to {self.cookies_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save cookies: {e}")
            return False

    def load_cookies(self) -> Optional[List[Dict[str, Any]]]:
        """Load browser cookies from file.

        Returns:
            List of cookie dictionaries if successful, None otherwise
        """
        try:
            if not self.cookies_path.exists():
                self.logger.info(f"No cookie file found at {self.cookies_path}")
                return None

            with open(self.cookies_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            cookies = data.get("cookies", [])
            if not cookies:
                self.logger.warning("Cookie file exists but contains no cookies")
                return None

            # Validate cookie format
            valid_cookies = []
            for cookie in cookies:
                if self._validate_cookie(cookie):
                    valid_cookies.append(cookie)
                else:
                    self.logger.warning(f"Skipping invalid cookie: {cookie}")

            self.logger.info(f"Loaded {len(valid_cookies)} valid cookies from {self.cookies_path}")
            return valid_cookies if valid_cookies else None

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in cookie file: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load cookies: {e}")
            return None

    def _validate_cookie(self, cookie: Dict[str, Any]) -> bool:
        """Validate cookie format for Selenium WebDriver.

        Args:
            cookie: Cookie dictionary

        Returns:
            True if cookie is valid, False otherwise
        """
        required_fields = ['name', 'value']
        return all(field in cookie for field in required_fields)

    def clear_cookies(self) -> bool:
        """Clear stored cookies by removing the cookie file.

        Returns:
            True if successful or file doesn't exist, False on error
        """
        try:
            if self.cookies_path.exists():
                self.cookies_path.unlink()
                self.logger.info(f"Cleared cookies file: {self.cookies_path}")
            else:
                self.logger.info("No cookie file to clear")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear cookies: {e}")
            return False

    def has_cookies(self) -> bool:
        """Check if cookie file exists and contains valid cookies.

        Returns:
            True if valid cookies exist, False otherwise
        """
        cookies = self.load_cookies()
        return cookies is not None and len(cookies) > 0

    def get_cookie_info(self) -> Dict[str, Any]:
        """Get information about stored cookies.

        Returns:
            Dictionary with cookie information
        """
        info = {
            "path": str(self.cookies_path),
            "exists": self.cookies_path.exists(),
            "count": 0,
            "timestamp": None,
            "domain": None
        }

        try:
            if self.cookies_path.exists():
                with open(self.cookies_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                info["count"] = len(data.get("cookies", []))
                info["timestamp"] = data.get("timestamp")
                info["domain"] = data.get("domain")
        except Exception as e:
            self.logger.warning(f"Failed to read cookie info: {e}")

        return info


# Global cookie manager instance
_cookie_manager = None


def get_cookie_manager(cookies_path: Optional[str] = None) -> CookieManager:
    """Get the global cookie manager instance.

    Args:
        cookies_path: Custom path for cookie storage

    Returns:
        CookieManager instance
    """
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = CookieManager(cookies_path)
    return _cookie_manager