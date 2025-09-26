"""Xiaohongshu service implementation for browser automation."""

import asyncio
import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse
from functools import wraps

import httpx
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from ..utils.logger import get_logger
from ..utils.cookie_manager import get_cookie_manager
from ..utils.environment import get_environment_detector
from .xiaohongshu_models import (
    XiaohongshuConfig,
    XiaohongshuError,
    LoginStatusResponse,
    LoginQrcodeResponse,
    LoginQrcodeRequest,
    PublishContentRequest,
    PublishContentResponse,
    ListFeedsResponse,
    SearchFeedsRequest,
    SearchFeedsResponse,
    FeedDetailRequest,
    FeedDetailResponse,
    PostCommentRequest,
    PostCommentResponse,
    UserProfileRequest,
    UserProfileResponse,
    Feed,
    Comment,
    UserProfile,
)


def retry_on_error(max_retries: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """Decorator to retry function on specific exceptions.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        # Get logger and service instance
                        logger = None
                        service = None
                        if args and hasattr(args[0], 'logger'):
                            logger = args[0].logger
                            service = args[0]
                        else:
                            logger = get_logger(__name__)

                        logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. Retrying in {delay}s...")

                        # Reset browser state if this is a browser-related error
                        if service and hasattr(service, '_reset_browser_state'):
                            try:
                                await service._reset_browser_state()
                            except Exception as reset_e:
                                logger.warning(f"Failed to reset browser state: {reset_e}")

                        await asyncio.sleep(delay * (attempt + 1))  # Exponential backoff
                    else:
                        raise last_exception
            raise last_exception
        return wrapper
    return decorator


class XiaohongshuService:
    """Service for interacting with Xiaohongshu platform."""

    def __init__(self, config: XiaohongshuConfig):
        """Initialize Xiaohongshu service.

        Args:
            config: Configuration for the service
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.driver: Optional[webdriver.Chrome] = None
        self.session_id: Optional[str] = None
        self.cookie_manager = get_cookie_manager()
        self.environment = get_environment_detector()
        self._temp_user_data_dir: Optional[str] = None

        # Xiaohongshu URLs (based on Go implementation)
        self.base_url = "https://www.xiaohongshu.com"
        self.login_url = f"{self.base_url}/explore"
        self.publish_url = "https://creator.xiaohongshu.com/publish/publish?source=official"

        # Initialize environment-aware settings
        self._setup_environment_config()

    def _setup_environment_config(self):
        """Setup configuration based on environment capabilities."""
        env_info = self.environment.get_environment_info()

        # Log environment info
        self.logger.info(f"Environment: {env_info['platform']}")
        self.logger.info(f"GUI support: {env_info['has_gui']}")
        self.logger.info(f"Chrome available: {bool(env_info['chrome_path'])}")

        # Adjust config based on environment
        if not env_info['has_gui']:
            # Force headless mode in non-GUI environments
            self.config.headless = True
            self.logger.info("Forced headless mode due to no GUI environment")

        if not env_info['chrome_works']:
            self.logger.warning("Chrome browser not available or not working")

    def can_use_browser(self) -> bool:
        """Check if browser-based login is available."""
        env_info = self.environment.get_environment_info()
        return env_info['chrome_works']

    def get_recommended_login_method(self) -> str:
        """Get the recommended login method for current environment."""
        recommendations = self.environment.get_login_recommendations()
        return recommendations['primary_method']

    def get_login_options(self) -> Dict[str, Any]:
        """Get all available login options for current environment."""
        return self.environment.get_login_recommendations()

    def _setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome driver with appropriate options."""
        # Check if browser is available
        env_info = self.environment.get_environment_info()
        if not env_info['chrome_path']:
            raise XiaohongshuError(
                "Chrome/Chromium 浏览器未找到。请使用手动 Cookie 导入或安装浏览器。"
            )

        options = Options()

        # Use configured headless mode
        if self.config.headless:
            options.add_argument("--headless")
            self.logger.debug("Using headless mode")

        # Essential arguments for stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        # Use random port to avoid conflicts with other instances
        import random
        debug_port = random.randint(9223, 9299)
        options.add_argument(f"--remote-debugging-port={debug_port}")
        self.logger.debug(f"Using remote debugging port: {debug_port}")
        options.add_argument(f"--user-agent={self.config.user_agent}")

        # Use a consistent user data directory for cookie persistence
        import tempfile
        import os
        from pathlib import Path

        # Create a persistent user data directory in temp
        temp_dir = Path(tempfile.gettempdir())
        persistent_user_data = temp_dir / "xiaohongshu_chrome_persistent"
        persistent_user_data.mkdir(exist_ok=True)

        self._temp_user_data_dir = str(persistent_user_data)
        options.add_argument(f"--user-data-dir={self._temp_user_data_dir}")
        self.logger.debug(f"Using persistent user data directory: {self._temp_user_data_dir}")

        # Force a new session and avoid reusing existing instances
        options.add_argument("--no-first-run")
        options.add_argument("--no-service-autorun")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-sync")
        options.add_argument("--metrics-recording-only")
        options.add_argument("--safebrowsing-disable-auto-update")
        options.add_argument("--enable-automation")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Windows specific fixes
        import sys
        if sys.platform == "win32":
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--log-level=3")  # Suppress INFO, WARNING and ERROR

        # Add experimental options for better stability
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Set window size for headless mode
        if self.config.headless:
            options.add_argument("--window-size=1920,1080")

        # Use environment-detected Chrome path if config doesn't specify one
        chrome_path = self.config.browser_path or env_info['chrome_path']
        service = None
        if chrome_path:
            # Set the Chrome binary path
            options.binary_location = chrome_path
            self.logger.debug(f"Using Chrome binary: {chrome_path}")

        try:
            driver = webdriver.Chrome(service=service, options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.implicitly_wait(10)

            # Load cookies if available
            self._load_cookies_to_driver(driver)

            return driver
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {e}")
            raise XiaohongshuError(f"Browser setup failed: {e}")

    async def _ensure_driver(self):
        """Ensure driver is initialized."""
        if self.driver is None:
            try:
                self.logger.info("Initializing Chrome driver...")
                self.driver = self._setup_driver()
                self.logger.info("Chrome driver initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize driver: {e}")
                raise XiaohongshuError(f"Driver initialization failed: {e}")

    async def _safe_navigate(self, url: str, max_retries: int = 3) -> bool:
        """Safely navigate to URL with retries.

        Args:
            url: URL to navigate to
            max_retries: Maximum retry attempts

        Returns:
            bool: Success status
        """
        self.logger.info(f"Starting navigation to URL: {url}")
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Navigation attempt {attempt + 1}/{max_retries}")
                await self._ensure_driver()
                self.logger.debug("Driver ensured, calling driver.get()")
                self.driver.get(url)
                # Wait for page to load
                self.logger.debug("Waiting for page to load...")
                await asyncio.sleep(2)
                final_url = self.driver.current_url
                self.logger.info(f"Navigation successful. Final URL: {final_url}")
                return True
            except WebDriverException as e:
                self.logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    self.logger.debug("Retrying navigation after delay...")
                    await asyncio.sleep(1)
                    # Try to recover driver
                    if self.driver:
                        try:
                            self.logger.debug("Quitting driver for recovery...")
                            self.driver.quit()
                        except:
                            pass
                        self.driver = None
                else:
                    self.logger.error(f"All navigation attempts failed for {url}: {e}")
                    raise XiaohongshuError(f"Failed to navigate to {url}: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error during navigation: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    if self.driver:
                        try:
                            self.driver.quit()
                        except:
                            pass
                        self.driver = None
                else:
                    raise XiaohongshuError(f"Unexpected error navigating to {url}: {e}")
        return False


    def _load_cookies_to_driver(self, driver: webdriver.Chrome):
        """Load saved cookies to the browser driver.

        Args:
            driver: Chrome WebDriver instance
        """
        try:
            cookies = self.cookie_manager.load_cookies()
            if not cookies:
                self.logger.info("No cookies to load")
                return

            # Navigate to domain first to set cookies
            driver.get(self.base_url)
            time.sleep(1)

            # Add each cookie
            cookies_added = 0
            for cookie in cookies:
                try:
                    # Ensure cookie is for the correct domain
                    if 'domain' not in cookie:
                        cookie['domain'] = '.xiaohongshu.com'

                    driver.add_cookie(cookie)
                    cookies_added += 1
                except Exception as e:
                    self.logger.warning(f"Failed to add cookie {cookie.get('name', 'unknown')}: {e}")

            self.logger.info(f"Loaded {cookies_added} cookies to browser")

        except Exception as e:
            self.logger.error(f"Failed to load cookies to driver: {e}")

    def _save_cookies_from_driver(self, driver: webdriver.Chrome):
        """Save current browser cookies.

        Args:
            driver: Chrome WebDriver instance
        """
        try:
            cookies = driver.get_cookies()
            if cookies:
                success = self.cookie_manager.save_cookies(cookies)
                if success:
                    self.logger.info("Login session saved successfully")
                else:
                    self.logger.error("Failed to save login session")
            else:
                self.logger.warning("No cookies to save")
        except Exception as e:
            self.logger.error(f"Failed to save cookies: {e}")

    async def _reset_browser_state(self):
        """Reset browser state for retry attempts."""
        try:
            if self.driver:
                self.logger.debug("Resetting browser state for retry...")
                # Try to refresh the page first
                try:
                    self.driver.refresh()
                    await asyncio.sleep(2)
                    return
                except WebDriverException:
                    pass

                # If refresh fails, quit and restart driver
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

                # Wait a bit before restarting
                await asyncio.sleep(1)

                # Driver will be recreated on next _ensure_driver call
                self.logger.debug("Browser state reset completed")
        except Exception as e:
            self.logger.warning(f"Error during browser state reset: {e}")

    async def cleanup(self):
        """Cleanup browser resources."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")
            finally:
                self.driver = None

        # Don't clean up persistent user data directory
        # Only clean up if it was a truly temporary directory (for compatibility)
        if self._temp_user_data_dir and not self._temp_user_data_dir.endswith("xiaohongshu_chrome_persistent"):
            try:
                import shutil
                shutil.rmtree(self._temp_user_data_dir, ignore_errors=True)
                self.logger.debug(f"Cleaned up temporary directory: {self._temp_user_data_dir}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up temporary directory: {e}")
        else:
            self.logger.debug("Keeping persistent user data directory for cookie persistence")

        self._temp_user_data_dir = None

    @retry_on_error(max_retries=2, delay=1.0, exceptions=(WebDriverException, TimeoutException))
    async def check_login_status(self) -> LoginStatusResponse:
        """Check if user is logged into Xiaohongshu.

        Returns:
            LoginStatusResponse: Login status information
        """
        await self._ensure_driver()

        try:
            self.logger.info("Checking login status...")
            success = await self._safe_navigate(self.login_url)
            if not success:
                return LoginStatusResponse(
                    is_logged_in=False,
                    message="无法加载页面，请检查网络连接"
                )

            # Wait for page to load
            await asyncio.sleep(2)

            # Check for login indicators using Go version's precise selector
            try:
                # Use the exact selector from Go implementation for reliable detection
                login_indicator_selector = ".main-container .user .link-wrapper .channel"

                # Wait a moment for elements to load
                await asyncio.sleep(1)

                # Check if the login indicator element exists and is displayed
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, login_indicator_selector)
                    is_logged_in = bool(elements and any(elem.is_displayed() for elem in elements))

                    if is_logged_in:
                        self.logger.info("User is logged in - found login indicator element")
                    else:
                        self.logger.info("User is not logged in - login indicator element not found")

                except NoSuchElementException:
                    is_logged_in = False
                    self.logger.info("User is not logged in - login indicator element not found")

                user_info = None
                if is_logged_in:
                    try:
                        # Try to extract basic user info if available
                        user_info = {"status": "logged_in"}

                        # Save cookies when login is detected
                        self._save_cookies_from_driver(self.driver)
                    except Exception as e:
                        self.logger.warning(f"Could not extract user info: {e}")

                return LoginStatusResponse(
                    is_logged_in=is_logged_in,
                    user_info=user_info,
                    message="已登录" if is_logged_in else "未登录，请手动登录后重试"
                )

            except Exception as e:
                self.logger.error(f"Error checking login status: {e}")
                return LoginStatusResponse(
                    is_logged_in=False,
                    message=f"检查登录状态失败: {e}"
                )

        except Exception as e:
            self.logger.error(f"Failed to check login status: {e}")
            raise XiaohongshuError(f"Login status check failed: {e}")

    async def get_login_qrcode(self, request: Optional[LoginQrcodeRequest] = None) -> LoginQrcodeResponse:
        """Get login QR code for authentication.

        Args:
            request: QR code request parameters

        Returns:
            LoginQrcodeResponse: QR code response with image data
        """
        await self._ensure_driver()

        if request is None:
            request = LoginQrcodeRequest()

        try:
            self.logger.info("Getting login QR code...")

            # Navigate to login page
            success = await self._safe_navigate(self.login_url)
            if not success:
                return LoginQrcodeResponse(
                    timeout="0s",
                    is_logged_in=False,
                    img=None
                )

            # Wait for page to load
            await asyncio.sleep(2)

            # Check if already logged in
            login_status = await self.check_login_status()
            if login_status.is_logged_in:
                return LoginQrcodeResponse(
                    timeout="0s",
                    is_logged_in=True,
                    img=None
                )

            # Look for QR code image
            qr_selectors = [
                ".login-container .qrcode-img",
                ".qrcode-img",
                "img[src*='qr']",
                ".qr-code img",
                "[class*='qr'] img",
                "img[alt*='二维码']",
                "img[alt*='qrcode']"
            ]

            qr_image_src = None
            for selector in qr_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            src = element.get_attribute("src")
                            if src and ("qr" in src.lower() or "data:image" in src.lower()):
                                qr_image_src = src
                                break
                    if qr_image_src:
                        break
                except NoSuchElementException:
                    continue

            if qr_image_src:
                # Convert image to base64 if needed
                if qr_image_src.startswith("data:image"):
                    # Already base64 encoded
                    img_data = qr_image_src.split(",", 1)[1] if "," in qr_image_src else qr_image_src
                else:
                    # Download image and encode to base64
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(qr_image_src)
                            if response.status_code == 200:
                                img_data = base64.b64encode(response.content).decode('utf-8')
                            else:
                                img_data = None
                    except Exception as e:
                        self.logger.warning(f"Failed to download QR code image: {e}")
                        img_data = None

                timeout_str = f"{request.timeout_seconds}s"
                return LoginQrcodeResponse(
                    timeout=timeout_str,
                    is_logged_in=False,
                    img=img_data
                )
            else:
                self.logger.warning("QR code image not found on page")
                return LoginQrcodeResponse(
                    timeout="0s",
                    is_logged_in=False,
                    img=None
                )

        except Exception as e:
            self.logger.error(f"Failed to get login QR code: {e}")
            return LoginQrcodeResponse(
                timeout="0s",
                is_logged_in=False,
                img=None
            )

    async def wait_for_login(self, timeout_seconds: int = 300) -> bool:
        """Wait for user to complete login via QR code or other methods.

        Args:
            timeout_seconds: Maximum time to wait for login completion

        Returns:
            bool: True if login completed successfully, False if timeout or error
        """
        try:
            self.logger.info(f"Waiting for login completion (timeout: {timeout_seconds}s)...")

            start_time = time.time()
            check_interval = 2  # Check every 2 seconds

            while time.time() - start_time < timeout_seconds:
                try:
                    # Check current login status
                    status = await self.check_login_status()
                    if status.is_logged_in:
                        self.logger.info("Login detected successfully!")
                        return True

                    await asyncio.sleep(check_interval)

                except Exception as e:
                    self.logger.warning(f"Error checking login status during wait: {e}")
                    await asyncio.sleep(check_interval)

            self.logger.warning(f"Login wait timeout ({timeout_seconds}s)")
            return False

        except Exception as e:
            self.logger.error(f"Error during login wait: {e}")
            return False

    @retry_on_error(max_retries=2, delay=2.0, exceptions=(WebDriverException, TimeoutException))
    async def publish_content(self, request: PublishContentRequest) -> PublishContentResponse:
        """Publish content to Xiaohongshu.

        Args:
            request: Publish content request

        Returns:
            PublishContentResponse: Publish operation result
        """
        await self._ensure_driver()

        # Validate request
        if not request.validate_title_length():
            return PublishContentResponse(
                success=False,
                message=f"标题长度超出限制（最大{self.config.max_title_length}字符）"
            )

        if len(request.content) > self.config.max_content_length:
            return PublishContentResponse(
                success=False,
                message=f"内容长度超出限制（最大{self.config.max_content_length}字符）"
            )

        if len(request.images) > self.config.max_images_per_post:
            return PublishContentResponse(
                success=False,
                message=f"图片数量超出限制（最大{self.config.max_images_per_post}张）"
            )

        try:
            self.logger.info(f"Publishing content: {request.title}")

            # Navigate directly to publish page (based on Go implementation)
            self.logger.info(f"Navigating to publish URL: {self.publish_url}")
            success = await self._safe_navigate(self.publish_url)
            if not success:
                self.logger.error("Failed to navigate to publish page")
                return PublishContentResponse(
                    success=False,
                    message="无法访问发布页面，请检查登录状态和网络连接"
                )

            current_url = self.driver.current_url
            self.logger.info(f"Current URL after navigation: {current_url}")

            # Wait for page to load and check for upload content area
            try:
                upload_content_selector = "div.upload-content"
                self.logger.info(f"Waiting for upload content area: {upload_content_selector}")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, upload_content_selector))
                )
                self.logger.info("Upload content area found successfully")
                await asyncio.sleep(2)
            except TimeoutException:
                current_url = self.driver.current_url.lower()
                self.logger.error(f"Timeout waiting for upload content area. Current URL: {current_url}")

                # Log page source for debugging
                try:
                    page_source = self.driver.page_source[:1000]  # First 1000 chars
                    self.logger.debug(f"Page source snippet: {page_source}")
                except Exception as e:
                    self.logger.warning(f"Could not get page source: {e}")

                if "login" in current_url or "sign" in current_url:
                    return PublishContentResponse(
                        success=False,
                        message="需要先登录才能发布内容"
                    )
                return PublishContentResponse(
                    success=False,
                    message=f"发布页面加载失败，当前页面: {current_url}"
                )

            # Click "上传图文" button (based on Go implementation)
            try:
                self.logger.info("Looking for '上传图文' tab...")
                tab_selectors = [
                    "div.creator-tab",
                    ".creator-tab",
                    "button[contains(text(), '上传图文')]",
                    "[data-testid='upload-tab']"
                ]

                upload_tab_clicked = False
                for selector in tab_selectors:
                    try:
                        self.logger.debug(f"Trying selector: {selector}")
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        self.logger.debug(f"Found {len(elements)} elements for selector {selector}")

                        for i, element in enumerate(elements):
                            try:
                                element_text = element.text
                                is_displayed = element.is_displayed()
                                self.logger.debug(f"Element {i}: text='{element_text}', displayed={is_displayed}")

                                if is_displayed and "上传图文" in element_text:
                                    self.logger.info(f"Clicking '上传图文' tab with selector: {selector}")
                                    element.click()
                                    self.logger.info("Click executed, waiting for page response...")

                                    # Wait and verify the click took effect (based on Go implementation)
                                    await asyncio.sleep(1)  # Go version waits 1 second

                                    # Check if upload area appeared after click
                                    try:
                                        # Look for elements that should appear after clicking upload tab
                                        upload_indicators = [
                                            ".upload-input",
                                            ".upload-area",
                                            ".file-upload",
                                            "[class*='upload']",
                                            "input[type='file']"
                                        ]

                                        page_changed = False
                                        for indicator in upload_indicators:
                                            try:
                                                WebDriverWait(self.driver, 2).until(
                                                    EC.presence_of_element_located((By.CSS_SELECTOR, indicator))
                                                )
                                                self.logger.info(f"Upload interface appeared with indicator: {indicator}")
                                                page_changed = True
                                                break
                                            except TimeoutException:
                                                continue

                                        if not page_changed:
                                            self.logger.warning("No upload interface detected after clicking tab")

                                    except Exception as e:
                                        self.logger.debug(f"Error checking page state after click: {e}")

                                    upload_tab_clicked = True
                                    self.logger.info("Successfully clicked '上传图文' tab")
                                    break
                            except Exception as e:
                                self.logger.debug(f"Error checking element {i}: {e}")

                        if upload_tab_clicked:
                            break
                    except Exception as e:
                        self.logger.debug(f"Failed to find elements with selector {selector}: {e}")
                        continue

                if not upload_tab_clicked:
                    self.logger.warning("Could not find '上传图文' tab, continuing...")

                    # Log available elements for debugging
                    try:
                        all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                        all_divs = self.driver.find_elements(By.TAG_NAME, "div")
                        self.logger.debug(f"Found {len(all_buttons)} buttons and {len(all_divs)} divs on page")

                        # Log first few button texts
                        for i, btn in enumerate(all_buttons[:10]):
                            try:
                                if btn.is_displayed():
                                    self.logger.debug(f"Button {i}: '{btn.text}'")
                            except:
                                pass
                    except Exception as e:
                        self.logger.warning(f"Could not log page elements: {e}")

            except Exception as e:
                self.logger.error(f"Error clicking upload tab: {e}, continuing...")

            self.logger.info("Tab clicking completed, proceeding to next steps...")

            # Handle image uploads first if any (based on Go implementation)
            if request.images and len(request.images) > 0:
                self.logger.info(f"Starting image upload for {len(request.images)} images...")
                success = await self._upload_images(request.images)
                if not success:
                    self.logger.error("Image upload failed")
                    return PublishContentResponse(
                        success=False,
                        message="图片上传失败"
                    )
                self.logger.info("Image upload completed successfully")
            else:
                self.logger.info("No images provided, skipping image upload step")

            # Fill in title (based on Go implementation)
            self.logger.info("Starting title input process...")
            title_input_found = False
            try:
                title_selectors = [
                    "div.d-input input",  # Go implementation selector
                    "input[placeholder*='标题']",
                    "input[placeholder*='请输入标题']",
                    "input[placeholder*='title']",
                    ".title-input",
                    ".publish-title input",
                    "input[class*='title']",
                    "[data-testid='title-input']",
                    "textarea[placeholder*='标题']"
                ]

                title_input = None
                for i, selector in enumerate(title_selectors):
                    try:
                        self.logger.debug(f"Trying title selector {i+1}/{len(title_selectors)}: {selector}")
                        title_input = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        if title_input.is_displayed():
                            self.logger.info(f"Found title input with selector: {selector}")
                            break
                        else:
                            self.logger.debug(f"Title input found but not displayed: {selector}")
                            title_input = None
                    except TimeoutException:
                        self.logger.debug(f"Timeout for title selector: {selector}")
                        continue

                if title_input:
                    self.logger.info(f"Filling title: {request.title[:30]}...")
                    title_input.clear()
                    title_input.send_keys(request.title)
                    await asyncio.sleep(1)
                    title_input_found = True
                    self.logger.info("Successfully filled title")

                if not title_input_found:
                    self.logger.warning("Could not find title input, continuing without title...")

            except Exception as e:
                self.logger.error(f"Title input error: {e}, continuing without title...")

            # Fill in content (based on Go implementation)
            self.logger.info("Starting content input process...")
            try:
                content_selectors = [
                    "div.ql-editor",  # Go implementation primary selector
                    "textarea[placeholder*='添加笔记内容']",
                    "textarea[placeholder*='内容']",
                    "textarea[placeholder*='请输入内容']",
                    "textarea[placeholder*='content']",
                    ".content-textarea",
                    ".publish-content textarea",
                    "[data-testid='content-input']",
                    "div[contenteditable='true']",
                    "textarea[class*='content']",
                    "textarea:not([placeholder*='标题'])"
                ]

                content_input = None
                for i, selector in enumerate(content_selectors):
                    try:
                        self.logger.debug(f"Trying content selector {i+1}/{len(content_selectors)}: {selector}")
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        self.logger.debug(f"Found {len(elements)} elements for content selector: {selector}")

                        for j, elem in enumerate(elements):
                            if elem.is_displayed():
                                self.logger.info(f"Found content input with selector: {selector} (element {j})")
                                content_input = elem
                                break
                        if content_input:
                            break
                    except NoSuchElementException:
                        self.logger.debug(f"No elements found for content selector: {selector}")
                        continue

                if content_input:
                    self.logger.info(f"Filling content ({len(request.content)} chars)...")
                    if content_input.tag_name == 'div':
                        self.logger.debug("Using contenteditable div approach")
                        # For contenteditable div
                        self.driver.execute_script("arguments[0].innerHTML = '';", content_input)
                        self.driver.execute_script("arguments[0].textContent = arguments[1];", content_input, request.content)
                    else:
                        self.logger.debug("Using textarea approach")
                        content_input.clear()
                        content_input.send_keys(request.content)
                    await asyncio.sleep(2)
                    self.logger.info("Successfully filled content")
                else:
                    self.logger.error("No content input element found")
                    return PublishContentResponse(
                        success=False,
                        message="找不到内容输入框"
                    )
            except Exception as e:
                self.logger.error(f"Content input error: {e}")
                return PublishContentResponse(
                    success=False,
                    message=f"填写内容失败: {e}"
                )

            # Submit the post (updated selectors with improved error handling)
            try:
                submit_selectors = [
                    "div.submit div.d-button-content",  # Go implementation selector
                    "button[contains(text(), '发布笔记')]",
                    "button[contains(text(), '发布')]",
                    "button[contains(text(), '发表')]",
                    "button[contains(text(), '提交')]",
                    ".publish-btn",
                    ".submit-btn",
                    ".reds-button-primary",
                    "[data-testid='publish-button']",
                    "button[class*='publish']",
                    "button[class*='submit']"
                ]

                submit_button = None
                submit_attempts = 0
                max_submit_attempts = 3

                while submit_attempts < max_submit_attempts and not submit_button:
                    submit_attempts += 1
                    self.logger.debug(f"Looking for submit button, attempt {submit_attempts}")

                    for selector in submit_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    submit_button = element
                                    self.logger.debug(f"Found submit button with selector: {selector}")
                                    break
                            if submit_button:
                                break
                        except (NoSuchElementException, TimeoutException):
                            continue

                    if not submit_button and submit_attempts < max_submit_attempts:
                        await asyncio.sleep(2)  # Wait and try again

                if submit_button:
                    try:
                        # Scroll to button if needed
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
                        await asyncio.sleep(1)

                        # Try to click the button
                        submit_button.click()
                        self.logger.info("Submit button clicked successfully")

                        await asyncio.sleep(5)  # Wait for submission

                        # Check if publish was successful
                        current_url = self.driver.current_url.lower()
                        success_indicators = ["explore", "user", "profile", "success"]

                        # Check for success by URL change or success indicators
                        if any(indicator in current_url for indicator in success_indicators) or "publish" not in current_url:
                            return PublishContentResponse(
                                success=True,
                                message="内容发布成功",
                                url=current_url
                            )
                        else:
                            # Check for error messages on the page
                            error_selectors = [
                                ".error-message", ".alert-error", "[class*='error']",
                                ".message-error", ".notification-error"
                            ]

                            error_message = None
                            for error_selector in error_selectors:
                                try:
                                    error_elements = self.driver.find_elements(By.CSS_SELECTOR, error_selector)
                                    for element in error_elements:
                                        if element.is_displayed() and element.text.strip():
                                            error_message = element.text.strip()
                                            break
                                    if error_message:
                                        break
                                except:
                                    continue

                            if error_message:
                                return PublishContentResponse(
                                    success=False,
                                    message=f"发布失败: {error_message}"
                                )
                            else:
                                return PublishContentResponse(
                                    success=False,
                                    message="发布状态不明确，请检查是否成功"
                                )

                    except Exception as click_e:
                        return PublishContentResponse(
                            success=False,
                            message=f"点击发布按钮失败: {click_e}"
                        )
                else:
                    return PublishContentResponse(
                        success=False,
                        message="找不到可用的发布按钮"
                    )

            except Exception as e:
                return PublishContentResponse(
                    success=False,
                    message=f"发布过程出错: {e}"
                )

        except Exception as e:
            self.logger.error(f"Failed to publish content: {e}")
            raise XiaohongshuError(f"Content publishing failed: {e}")

    async def _upload_images(self, images: List[str]) -> bool:
        """Upload images for post.

        Args:
            images: List of image URLs or local paths

        Returns:
            bool: Success status
        """
        try:
            # Wait for upload input to appear (based on Go implementation)
            self.logger.info("Waiting for .upload-input element to appear...")
            try:
                # Use explicit wait like Go version: pp.MustElement(".upload-input")
                upload_input = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".upload-input"))
                )
                self.logger.info("Found .upload-input element successfully")
            except TimeoutException:
                self.logger.error("Timeout waiting for .upload-input element")

                # Try alternative selectors as fallback
                upload_selectors = [
                    "input[type='file']",
                    "input[accept*='image']",
                    "input[multiple]",
                    "[data-testid='image-upload']",
                    ".image-upload-input",
                    ".file-input",
                    "input[class*='upload']"
                ]

                upload_input = None
                for selector in upload_selectors:
                    try:
                        self.logger.debug(f"Trying fallback selector: {selector}")
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed():
                                # Check if the input accepts images
                                accept_attr = elem.get_attribute('accept') or ''
                                if 'image' in accept_attr or not accept_attr:
                                    upload_input = elem
                                    self.logger.info(f"Found upload input with fallback selector: {selector}")
                                    break
                        if upload_input:
                            break
                    except NoSuchElementException:
                        continue

                if not upload_input:
                    self.logger.error("Could not find image upload input with any selector")
                    return False

            # Prepare all image paths for upload
            valid_image_paths = []
            for image_path in images:
                if image_path.startswith(('http://', 'https://')):
                    # Download image first
                    local_path = await self._download_image(image_path)
                    if local_path:
                        valid_image_paths.append(os.path.abspath(local_path))
                elif os.path.exists(image_path):
                    valid_image_paths.append(os.path.abspath(image_path))
                else:
                    self.logger.warning(f"Image file not found: {image_path}")

            if valid_image_paths:
                # Upload all images at once (similar to Go implementation)
                upload_input.send_keys('\n'.join(valid_image_paths))
                await asyncio.sleep(3)  # Wait for upload

                # Wait for image preview area to show uploaded images (based on Go implementation)
                try:
                    preview_selector = ".img-preview-area .pr"
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, preview_selector))
                    )
                    self.logger.debug("Image upload completed successfully")
                except TimeoutException:
                    self.logger.warning("Image upload timeout, but continuing...")

            return True

        except Exception as e:
            self.logger.error(f"Image upload failed: {e}")
            return False

    async def _download_image(self, url: str) -> Optional[str]:
        """Download image from URL to temporary location.

        Args:
            url: Image URL

        Returns:
            str: Local file path if successful, None otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()

                # Create temp directory
                temp_dir = Path("/tmp/xiaohongshu_images")
                temp_dir.mkdir(exist_ok=True)

                # Determine file extension
                content_type = response.headers.get("content-type", "")
                ext = ".jpg"  # default
                if "png" in content_type:
                    ext = ".png"
                elif "gif" in content_type:
                    ext = ".gif"
                elif "webp" in content_type:
                    ext = ".webp"

                # Save file
                filename = f"image_{int(time.time())}{ext}"
                file_path = temp_dir / filename

                with open(file_path, "wb") as f:
                    f.write(response.content)

                return str(file_path)

        except Exception as e:
            self.logger.error(f"Failed to download image {url}: {e}")
            return None

    @retry_on_error(max_retries=2, delay=1.0, exceptions=(WebDriverException, TimeoutException))
    async def list_feeds(self) -> ListFeedsResponse:
        """Get list of recommended feeds.

        Returns:
            ListFeedsResponse: List of feeds
        """
        await self._ensure_driver()

        try:
            self.logger.info("Getting recommended feeds...")
            success = await self._safe_navigate(self.login_url)
            if not success:
                return ListFeedsResponse(
                    feeds=[],
                    total_count=0,
                    has_more=False
                )
            await asyncio.sleep(3)

            feeds = []

            # Parse feed elements from page (updated selectors)
            feed_selectors = [
                ".note-item",
                ".feed-item",
                ".explore-item",
                ".note-card",
                ".waterfall-item",
                "[data-testid='note-item']",
                "[class*='note']",
                "[class*='feed']",
                ".masonry-item",
                "article"
            ]

            feed_elements = []
            for selector in feed_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 3:  # Ensure we have substantial content
                        feed_elements = elements
                        break
                except Exception:
                    continue

            for element in feed_elements[:20]:  # Limit to 20 feeds
                try:
                    feed = await self._parse_feed_element(element)
                    if feed:
                        feeds.append(feed)
                except Exception as e:
                    self.logger.warning(f"Failed to parse feed element: {e}")
                    continue

            return ListFeedsResponse(
                feeds=feeds,
                total_count=len(feeds),
                has_more=len(feeds) >= 20
            )

        except Exception as e:
            self.logger.error(f"Failed to list feeds: {e}")
            raise XiaohongshuError(f"Feed listing failed: {e}")

    async def _parse_feed_element(self, element) -> Optional[Feed]:
        """Parse a feed element into Feed object.

        Args:
            element: Web element representing a feed

        Returns:
            Feed: Parsed feed object or None if failed
        """
        try:
            # Extract feed information from element
            # This is a simplified implementation - actual selectors may vary

            # Extract feed ID from various sources
            feed_id = (
                element.get_attribute("data-id") or
                element.get_attribute("data-note-id") or
                element.get_attribute("data-item-id") or
                f"feed_{int(time.time())}_{hash(str(element))}"
            )

            # Try to get title/content (updated selectors)
            title_selectors = [
                ".title", ".note-title", ".card-title", ".item-title",
                "h3", "h4", ".feed-title", "[class*='title']", ".note-content"
            ]

            title = "无标题"
            for selector in title_selectors:
                try:
                    title_element = element.find_element(By.CSS_SELECTOR, selector)
                    if title_element.text.strip():
                        title = title_element.text.strip()
                        break
                except NoSuchElementException:
                    continue

            # Get author info (updated selectors)
            author_selectors = [
                ".author", ".user-name", ".username", ".nickname",
                ".author-name", "[class*='user']", "[class*='author']"
            ]

            author = "未知用户"
            for selector in author_selectors:
                try:
                    author_element = element.find_element(By.CSS_SELECTOR, selector)
                    if author_element.text.strip():
                        author = author_element.text.strip()
                        break
                except NoSuchElementException:
                    continue

            # Extract xsec_token from link or page context
            xsec_token = await self._extract_xsec_token(element)

            return Feed(
                feed_id=feed_id,
                title=title[:50],  # Truncate long titles
                content=title,  # Use title as content for now
                author=author,
                author_id=f"user_{hash(author)}",
                xsec_token=xsec_token
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse feed element: {e}")
            return None

    @retry_on_error(max_retries=2, delay=1.0, exceptions=(WebDriverException, TimeoutException))
    async def search_feeds(self, request: SearchFeedsRequest) -> SearchFeedsResponse:
        """Search feeds by keyword."""
        await self._ensure_driver()

        try:
            self.logger.info(f"Searching feeds with keyword: {request.keyword}")

            # Navigate to Xiaohongshu search page
            search_url = f"{self.base_url}/search_result?keyword={request.keyword}"
            success = await self._safe_navigate(search_url)
            if not success:
                return SearchFeedsResponse(
                    feeds=[],
                    total_count=0,
                    keyword=request.keyword,
                    page=request.page,
                    has_more=False
                )
            await asyncio.sleep(3)

            feeds = []

            # Parse search results (updated selectors)
            search_selectors = [
                ".note-item",
                ".search-item",
                ".search-result-item",
                ".result-item",
                ".feed-item",
                ".note-card",
                "[data-testid='search-item']",
                "[class*='search']",
                "[class*='result']",
                "article",
                ".waterfall-item"
            ]

            feed_elements = []
            for selector in search_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 1:  # Ensure we have content
                        feed_elements = elements
                        break
                except Exception:
                    continue

            for element in feed_elements[:request.limit]:
                try:
                    feed = await self._parse_feed_element(element)
                    if feed:
                        feeds.append(feed)
                except Exception as e:
                    self.logger.warning(f"Failed to parse search result element: {e}")
                    continue

            return SearchFeedsResponse(
                feeds=feeds,
                total_count=len(feeds),
                keyword=request.keyword,
                page=request.page,
                has_more=len(feeds) >= request.limit
            )

        except Exception as e:
            self.logger.error(f"Failed to search feeds: {e}")
            raise XiaohongshuError(f"Feed search failed: {e}")

    @retry_on_error(max_retries=2, delay=1.0, exceptions=(WebDriverException, TimeoutException))
    async def get_feed_detail(self, request: FeedDetailRequest) -> FeedDetailResponse:
        """Get detailed information about a specific feed."""
        await self._ensure_driver()

        try:
            self.logger.info(f"Getting feed detail for: {request.feed_id}")

            # Navigate to feed detail page
            feed_url = f"{self.base_url}/explore/{request.feed_id}"
            success = await self._safe_navigate(feed_url)
            if not success:
                raise XiaohongshuError("无法加载帖子详情页面")
            await asyncio.sleep(3)

            # Parse feed details
            feed = await self._parse_detailed_feed()
            comments = await self._parse_comments()

            return FeedDetailResponse(
                feed=feed,
                comments=comments,
                total_comments=len(comments)
            )

        except Exception as e:
            self.logger.error(f"Failed to get feed detail: {e}")
            raise XiaohongshuError(f"Get feed detail failed: {e}")

    async def _parse_detailed_feed(self) -> Feed:
        """Parse detailed feed information from current page."""
        try:
            # Extract detailed feed information
            title_element = None
            content_element = None
            author_element = None

            # Try different selectors for title (updated)
            title_selectors = [
                ".note-title", ".title", ".detail-title", ".post-title",
                "h1", "h2", "[data-testid='note-title']", "[class*='title']"
            ]
            title_element = None
            for selector in title_selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if elem.text.strip():
                        title_element = elem
                        break
                except NoSuchElementException:
                    continue

            # Try different selectors for content (updated)
            content_selectors = [
                ".note-content", ".content", ".desc", ".note-desc",
                ".detail-content", ".post-content", "[data-testid='note-content']",
                "[class*='content']", "[class*='desc']", "p"
            ]
            content_element = None
            for selector in content_selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if elem.text.strip():
                        content_element = elem
                        break
                except NoSuchElementException:
                    continue

            # Try different selectors for author (updated)
            author_selectors = [
                ".author-name", ".user-name", ".username", ".nickname",
                ".author", "[data-testid='author']", "[class*='author']",
                "[class*='user']", "[class*='name']"
            ]
            author_element = None
            for selector in author_selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if elem.text.strip():
                        author_element = elem
                        break
                except NoSuchElementException:
                    continue

            title = title_element.text if title_element else "无标题"
            content = content_element.text if content_element else "无内容"
            author = author_element.text if author_element else "未知用户"

            # Try to get engagement metrics (updated selectors)
            like_count = 0
            comment_count = 0
            share_count = 0

            # Extract like count
            like_selectors = [
                "[data-testid='like-count']", ".like-count", ".likes",
                "[class*='like']", "[class*='heart']", ".interaction-count"
            ]
            for selector in like_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    text = element.text.strip()
                    if text.isdigit():
                        like_count = int(text)
                        break
                    # Handle formatted numbers like "1.2k", "1w"
                    elif 'k' in text.lower():
                        like_count = int(float(text.lower().replace('k', '')) * 1000)
                        break
                    elif 'w' in text.lower():
                        like_count = int(float(text.lower().replace('w', '')) * 10000)
                        break
                except:
                    continue

            # Extract comment count
            comment_selectors = [
                "[data-testid='comment-count']", ".comment-count", ".comments",
                "[class*='comment']", ".interaction-count"
            ]
            for selector in comment_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    text = element.text.strip()
                    if text.isdigit():
                        comment_count = int(text)
                        break
                    elif 'k' in text.lower():
                        comment_count = int(float(text.lower().replace('k', '')) * 1000)
                        break
                    elif 'w' in text.lower():
                        comment_count = int(float(text.lower().replace('w', '')) * 10000)
                        break
                except:
                    continue

            # Extract xsec_token from current page
            xsec_token = await self._extract_xsec_token_from_page()

            return Feed(
                feed_id=f"feed_{int(time.time())}",
                title=title,
                content=content,
                author=author,
                author_id=f"user_{hash(author)}",
                like_count=like_count,
                comment_count=comment_count,
                share_count=share_count,
                xsec_token=xsec_token
            )

        except Exception as e:
            self.logger.error(f"Failed to parse detailed feed: {e}")
            raise

    async def _parse_comments(self) -> List[Comment]:
        """Parse comments from current feed detail page."""
        try:
            comments = []

            # Try different selectors for comments
            comment_selectors = [
                ".comment-item",
                ".comment",
                "[data-testid='comment']",
                ".comment-list .item"
            ]

            comment_elements = []
            for selector in comment_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        comment_elements = elements
                        break
                except Exception:
                    continue

            for element in comment_elements[:20]:  # Limit to 20 comments
                try:
                    comment = await self._parse_comment_element(element)
                    if comment:
                        comments.append(comment)
                except Exception as e:
                    self.logger.warning(f"Failed to parse comment element: {e}")
                    continue

            return comments

        except Exception as e:
            self.logger.error(f"Failed to parse comments: {e}")
            return []

    async def _parse_comment_element(self, element) -> Optional[Comment]:
        """Parse a comment element into Comment object."""
        try:
            # Extract comment information
            comment_id = element.get_attribute("data-id") or f"comment_{int(time.time())}"

            # Get comment content
            content_element = element.find_element(By.CSS_SELECTOR, ".comment-content, .content")
            content = content_element.text if content_element else "无内容"

            # Get author info
            author_element = element.find_element(By.CSS_SELECTOR, ".comment-author, .author")
            author = author_element.text if author_element else "未知用户"

            # Get like count
            like_count = 0
            try:
                like_element = element.find_element(By.CSS_SELECTOR, ".like-count")
                like_count = int(like_element.text) if like_element.text.isdigit() else 0
            except:
                pass

            return Comment(
                comment_id=comment_id,
                content=content,
                author=author,
                author_id=f"user_{hash(author)}",
                like_count=like_count
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse comment element: {e}")
            return None

    @retry_on_error(max_retries=2, delay=1.0, exceptions=(WebDriverException, TimeoutException))
    async def post_comment_to_feed(self, request: PostCommentRequest) -> PostCommentResponse:
        """Post a comment to a specific feed."""
        await self._ensure_driver()

        try:
            self.logger.info(f"Posting comment to feed: {request.feed_id}")

            # Navigate to feed detail page
            feed_url = f"{self.base_url}/explore/{request.feed_id}"
            success = await self._safe_navigate(feed_url)
            if not success:
                return PostCommentResponse(
                    success=False,
                    message="无法加载帖子详情页面"
                )
            await asyncio.sleep(3)

            # Find comment input field (updated selectors)
            comment_selectors = [
                "textarea[placeholder*='评论']",
                "textarea[placeholder*='说点什么']",
                "textarea[placeholder*='输入评论']",
                "textarea[placeholder*='comment']",
                ".comment-input",
                ".reply-input",
                "[data-testid='comment-input']",
                "div[contenteditable='true']",
                "textarea[class*='comment']",
                "input[placeholder*='评论']"
            ]

            comment_input = None
            for selector in comment_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            comment_input = elem
                            break
                    if comment_input:
                        break
                except NoSuchElementException:
                    continue

            if not comment_input:
                return PostCommentResponse(
                    success=False,
                    message="找不到评论输入框"
                )

            # Fill comment content
            try:
                if comment_input.tag_name == 'div':
                    # For contenteditable div
                    self.driver.execute_script("arguments[0].innerHTML = '';", comment_input)
                    self.driver.execute_script("arguments[0].textContent = arguments[1];", comment_input, request.content)
                else:
                    comment_input.clear()
                    comment_input.send_keys(request.content)
                await asyncio.sleep(1)
            except Exception as e:
                return PostCommentResponse(
                    success=False,
                    message=f"填写评论内容失败: {e}"
                )

            # Submit comment (updated selectors)
            submit_selectors = [
                "button[contains(text(), '发布')]",
                "button[contains(text(), '评论')]",
                "button[contains(text(), '发送')]",
                ".comment-submit",
                ".reply-submit",
                "[data-testid='comment-submit']",
                "button[class*='submit']",
                "button[class*='send']",
                ".reds-button[contains(text(), '发布')]"
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if submit_button.is_displayed():
                        break
                except TimeoutException:
                    continue

            if submit_button:
                submit_button.click()
                await asyncio.sleep(3)  # Wait for submission

                return PostCommentResponse(
                    success=True,
                    comment_id=f"comment_{int(time.time())}",
                    message="评论发表成功"
                )
            else:
                return PostCommentResponse(
                    success=False,
                    message="找不到发布按钮"
                )

        except Exception as e:
            self.logger.error(f"Failed to post comment: {e}")
            raise XiaohongshuError(f"Post comment failed: {e}")

    @retry_on_error(max_retries=2, delay=1.0, exceptions=(WebDriverException, TimeoutException))
    async def user_profile(self, request: UserProfileRequest) -> UserProfileResponse:
        """Get user profile information."""
        await self._ensure_driver()

        try:
            self.logger.info(f"Getting user profile: {request.user_id}")

            # Navigate to user profile page
            profile_url = f"{self.base_url}/user/profile/{request.user_id}"
            success = await self._safe_navigate(profile_url)
            if not success:
                raise XiaohongshuError("无法加载用户资料页面")
            await asyncio.sleep(3)

            # Parse user profile information
            user = await self._parse_user_profile()
            recent_posts = await self._parse_user_recent_posts()

            return UserProfileResponse(
                user=user,
                recent_posts=recent_posts
            )

        except Exception as e:
            self.logger.error(f"Failed to get user profile: {e}")
            raise XiaohongshuError(f"Get user profile failed: {e}")

    async def _parse_user_profile(self) -> UserProfile:
        """Parse user profile information from current page."""
        try:
            # Extract user profile information
            username = "unknown_user"
            nickname = "未知用户"
            description = None

            # Try to get username/nickname
            name_selectors = [".username", ".nickname", ".user-name", "[data-testid='username']"]
            for selector in name_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.text:
                        username = element.text
                        nickname = element.text
                        break
                except NoSuchElementException:
                    continue

            # Try to get description
            desc_selectors = [".user-desc", ".description", ".bio", "[data-testid='user-desc']"]
            for selector in desc_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.text:
                        description = element.text
                        break
                except NoSuchElementException:
                    continue

            # Try to get stats
            followers_count = 0
            following_count = 0
            posts_count = 0
            likes_count = 0

            # Extract follower/following counts
            stat_selectors = [
                ".followers-count", ".following-count", ".posts-count",
                "[data-testid='followers']", "[data-testid='following']", "[data-testid='posts']"
            ]

            for selector in stat_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.text.isdigit():
                        if "followers" in selector:
                            followers_count = int(element.text)
                        elif "following" in selector:
                            following_count = int(element.text)
                        elif "posts" in selector:
                            posts_count = int(element.text)
                except:
                    continue

            return UserProfile(
                user_id=f"user_{int(time.time())}",
                username=username,
                nickname=nickname,
                description=description,
                followers_count=followers_count,
                following_count=following_count,
                posts_count=posts_count,
                likes_count=likes_count
            )

        except Exception as e:
            self.logger.error(f"Failed to parse user profile: {e}")
            raise

    async def _parse_user_recent_posts(self) -> List[Feed]:
        """Parse recent posts from user profile page."""
        try:
            posts = []

            # Try different selectors for user posts
            post_selectors = [
                ".user-note",
                ".note-item",
                ".post-item",
                "[data-testid='user-post']"
            ]

            post_elements = []
            for selector in post_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        post_elements = elements
                        break
                except Exception:
                    continue

            for element in post_elements[:10]:  # Limit to 10 recent posts
                try:
                    post = await self._parse_feed_element(element)
                    if post:
                        posts.append(post)
                except Exception as e:
                    self.logger.warning(f"Failed to parse user post element: {e}")
                    continue

            return posts

        except Exception as e:
            self.logger.error(f"Failed to parse user recent posts: {e}")
            return []

    async def _extract_xsec_token(self, element) -> str:
        """Extract xsec_token from element or related links.

        Args:
            element: Web element to extract token from

        Returns:
            str: Extracted token or placeholder
        """
        try:
            # Try to find links with tokens in the element
            link_selectors = ["a", "[href]", "[data-href]"]

            for selector in link_selectors:
                try:
                    links = element.find_elements(By.CSS_SELECTOR, selector)
                    for link in links:
                        href = link.get_attribute('href') or link.get_attribute('data-href')
                        if href and 'xsec_token' in href:
                            # Extract token from URL
                            import re
                            match = re.search(r'xsec_token=([^&]+)', href)
                            if match:
                                return match.group(1)
                except:
                    continue

            # Try to extract from data attributes
            token_attrs = ['data-token', 'data-xsec-token', 'data-sec-token']
            for attr in token_attrs:
                token = element.get_attribute(attr)
                if token:
                    return token

            # Look for token in nearby script tags or data
            try:
                # Try to find token in page scripts
                scripts = self.driver.find_elements(By.TAG_NAME, 'script')
                for script in scripts:
                    script_content = script.get_attribute('innerHTML') or ''
                    if 'xsec_token' in script_content:
                        import re
                        match = re.search(r'["\']xsec_token["\']\\s*:\\s*["\']([^"\'\\s]+)["\']', script_content)
                        if match:
                            return match.group(1)
            except:
                pass

            return f"token_{int(time.time())}_{hash(str(element))}"

        except Exception as e:
            self.logger.warning(f"Failed to extract xsec_token: {e}")
            return f"token_{int(time.time())}"

    async def _extract_xsec_token_from_page(self) -> str:
        """Extract xsec_token from current page.

        Returns:
            str: Extracted token or placeholder
        """
        try:
            # Try to extract from URL parameters
            current_url = self.driver.current_url
            if 'xsec_token' in current_url:
                import re
                match = re.search(r'xsec_token=([^&]+)', current_url)
                if match:
                    return match.group(1)

            # Try to extract from page scripts or data
            scripts = self.driver.find_elements(By.TAG_NAME, 'script')
            for script in scripts:
                script_content = script.get_attribute('innerHTML') or ''
                if 'xsec_token' in script_content:
                    import re
                    patterns = [
                        r'["\']xsec_token["\']\\s*:\\s*["\']([^"\'\\s]+)["\']',
                        r'xsec_token["\']?\\s*=\\s*["\']([^"\'\\s]+)["\']',
                        r'token["\']?\\s*:\\s*["\']([^"\'\\s]+)["\']'
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, script_content)
                        if match and len(match.group(1)) > 10:  # Reasonable token length
                            return match.group(1)

            # Try to extract from meta tags or other elements
            meta_selectors = [
                "meta[name*='token']",
                "meta[property*='token']",
                "[data-token]",
                "[data-xsec-token]"
            ]

            for selector in meta_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        content = element.get_attribute('content') or element.get_attribute('data-token')
                        if content and len(content) > 10:
                            return content
                except:
                    continue

            # Generate a session-based placeholder
            if not hasattr(self, '_session_token'):
                self._session_token = f"session_token_{int(time.time())}_{hash(current_url)}"
            return self._session_token

        except Exception as e:
            self.logger.warning(f"Failed to extract xsec_token from page: {e}")
            return f"page_token_{int(time.time())}"