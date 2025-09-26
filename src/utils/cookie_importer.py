"""Manual cookie import utilities for environments without browser support."""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from .logger import get_logger
from .cookie_manager import get_cookie_manager


class CookieImporter:
    """Handle manual cookie import from various sources."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.cookie_manager = get_cookie_manager()

    def import_from_json_file(self, file_path: Union[str, Path]) -> bool:
        """Import cookies from JSON file.

        Args:
            file_path: Path to JSON file containing cookies

        Returns:
            bool: True if import successful
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                self.logger.error(f"Cookie file not found: {file_path}")
                return False

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different JSON formats
            cookies = self._normalize_cookie_data(data)

            if not cookies:
                self.logger.error("No valid cookies found in file")
                return False

            # Validate cookies
            valid_cookies = []
            for cookie in cookies:
                if self._validate_cookie(cookie):
                    valid_cookies.append(cookie)

            if not valid_cookies:
                self.logger.error("No valid cookies after validation")
                return False

            # Save cookies
            success = self.cookie_manager.save_cookies(valid_cookies)
            if success:
                self.logger.info(f"Successfully imported {len(valid_cookies)} cookies from {file_path}")
                return True
            else:
                self.logger.error("Failed to save imported cookies")
                return False

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON format: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to import cookies from file: {e}")
            return False

    def import_from_text(self, cookie_text: str, format_type: str = "auto") -> bool:
        """Import cookies from text input.

        Args:
            cookie_text: Raw cookie text
            format_type: Format type ("auto", "json", "netscape", "header")

        Returns:
            bool: True if import successful
        """
        try:
            if format_type == "auto":
                format_type = self._detect_format(cookie_text)

            cookies = []

            if format_type == "json":
                cookies = self._parse_json_text(cookie_text)
            elif format_type == "netscape":
                cookies = self._parse_netscape_format(cookie_text)
            elif format_type == "header":
                cookies = self._parse_header_format(cookie_text)
            elif format_type == "browser_console":
                cookies = self._parse_browser_console_format(cookie_text)
            else:
                self.logger.error(f"Unsupported format type: {format_type}")
                return False

            if not cookies:
                self.logger.error("No cookies could be parsed from text")
                return False

            # Validate and filter cookies
            valid_cookies = [c for c in cookies if self._validate_cookie(c)]

            if not valid_cookies:
                self.logger.error("No valid cookies after parsing")
                return False

            # Save cookies
            success = self.cookie_manager.save_cookies(valid_cookies)
            if success:
                self.logger.info(f"Successfully imported {len(valid_cookies)} cookies from text")
                return True
            else:
                self.logger.error("Failed to save imported cookies")
                return False

        except Exception as e:
            self.logger.error(f"Failed to import cookies from text: {e}")
            return False

    def _normalize_cookie_data(self, data: Any) -> List[Dict[str, Any]]:
        """Normalize cookie data from various formats."""
        cookies = []

        if isinstance(data, list):
            # Direct list of cookies
            cookies = data
        elif isinstance(data, dict):
            if 'cookies' in data:
                # Wrapped in cookies key
                cookies = data['cookies']
            elif all(k in data for k in ['name', 'value']):
                # Single cookie object
                cookies = [data]
            else:
                # Try to extract cookie-like objects
                for key, value in data.items():
                    if isinstance(value, dict) and 'value' in value:
                        cookie = {'name': key, **value}
                        cookies.append(cookie)

        return cookies

    def _validate_cookie(self, cookie: Dict[str, Any]) -> bool:
        """Validate a single cookie object."""
        if not isinstance(cookie, dict):
            return False

        # Required fields
        if 'name' not in cookie or 'value' not in cookie:
            return False

        # Check for xiaohongshu domain
        domain = cookie.get('domain', '')
        if domain and 'xiaohongshu.com' not in domain:
            # Add domain if missing
            cookie['domain'] = '.xiaohongshu.com'

        # Ensure required Selenium format
        if 'domain' not in cookie:
            cookie['domain'] = '.xiaohongshu.com'

        return True

    def _detect_format(self, text: str) -> str:
        """Auto-detect cookie format from text."""
        text_stripped = text.strip()

        if text_stripped.startswith('[') or text_stripped.startswith('{'):
            return "json"
        elif "# Netscape HTTP Cookie File" in text:
            return "netscape"
        elif text_stripped.startswith("Cookie:"):
            return "header"
        elif "document.cookie" in text:
            return "browser_console"
        else:
            # Try to detect based on content
            if re.search(r'\w+\s*=\s*[^;]+', text):
                return "header"
            return "json"  # Default fallback

    def _parse_json_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse JSON format cookie text."""
        try:
            data = json.loads(text)
            return self._normalize_cookie_data(data)
        except json.JSONDecodeError:
            return []

    def _parse_netscape_format(self, text: str) -> List[Dict[str, Any]]:
        """Parse Netscape cookie file format."""
        cookies = []
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('#') or not line:
                continue

            parts = line.split('\t')
            if len(parts) >= 7:
                cookie = {
                    'domain': parts[0],
                    'path': parts[2],
                    'secure': parts[3].upper() == 'TRUE',
                    'httpOnly': False,
                    'name': parts[5],
                    'value': parts[6]
                }
                cookies.append(cookie)

        return cookies

    def _parse_header_format(self, text: str) -> List[Dict[str, Any]]:
        """Parse HTTP header cookie format."""
        cookies = []

        # Remove "Cookie:" prefix if present
        cookie_text = re.sub(r'^Cookie:\s*', '', text, flags=re.IGNORECASE)

        # Split by semicolons
        for cookie_str in cookie_text.split(';'):
            cookie_str = cookie_str.strip()
            if '=' in cookie_str:
                name, value = cookie_str.split('=', 1)
                cookie = {
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.xiaohongshu.com'
                }
                cookies.append(cookie)

        return cookies

    def _parse_browser_console_format(self, text: str) -> List[Dict[str, Any]]:
        """Parse browser console JavaScript format."""
        # Extract JSON from JavaScript code
        json_match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return self._normalize_cookie_data(data)
            except json.JSONDecodeError:
                pass

        return []

    def get_import_instructions(self) -> Dict[str, Any]:
        """Get detailed import instructions for users."""
        return {
            'title': '🍪 小红书 Cookie 导入指南',
            'methods': {
                'browser_console': {
                    'name': '浏览器控制台导出 (推荐)',
                    'steps': [
                        '1. 在有浏览器的设备上访问 https://www.xiaohongshu.com',
                        '2. 完成登录（微信扫码或手机号登录）',
                        '3. 按 F12 打开开发者工具',
                        '4. 切换到 Console (控制台) 标签',
                        '5. 粘贴以下代码并按回车:'
                    ],
                    'code': '''copy(JSON.stringify(document.cookie.split(';').map(c => {
    const [name, value] = c.trim().split('=');
    return {name, value, domain: '.xiaohongshu.com'};
}).filter(c => c.name && c.value)))''',
                    'next_steps': [
                        '6. Cookie 数据已复制到剪贴板',
                        '7. 将数据保存到文件 cookies.json',
                        '8. 使用导入功能加载 Cookie'
                    ]
                },
                'extension': {
                    'name': '浏览器扩展导出',
                    'extensions': [
                        'Cookie-Editor (Chrome/Firefox)',
                        'EditThisCookie (Chrome)',
                        'cookies.txt (Firefox)'
                    ],
                    'steps': [
                        '1. 安装上述任一扩展',
                        '2. 访问小红书并登录',
                        '3. 使用扩展导出 cookies',
                        '4. 选择 JSON 或文本格式',
                        '5. 使用导入功能加载'
                    ]
                },
                'manual': {
                    'name': '手动复制 Cookie',
                    'steps': [
                        '1. 登录小红书后按 F12',
                        '2. 切换到 Application 标签',
                        '3. 左侧选择 Storage > Cookies > xiaohongshu.com',
                        '4. 复制重要的 Cookie 值',
                        '5. 按格式手动输入'
                    ],
                    'format_example': '''[
    {"name": "web_session", "value": "xxx", "domain": ".xiaohongshu.com"},
    {"name": "xsecappid", "value": "xxx", "domain": ".xiaohongshu.com"}
]'''
                }
            },
            'tips': [
                '💡 推荐使用浏览器控制台方法，最快捷准确',
                '🔒 Cookie 包含敏感信息，请妥善保管',
                '⏰ Cookie 有有效期，过期后需要重新导入',
                '🌐 确保从 xiaohongshu.com 域名导出 Cookie'
            ]
        }

    def interactive_import(self) -> bool:
        """Interactive cookie import with user guidance."""
        print("\n" + "=" * 60)
        print("🍪 小红书 Cookie 导入工具")
        print("=" * 60)

        instructions = self.get_import_instructions()
        print(f"\n{instructions['title']}\n")

        # Show available methods
        methods = instructions['methods']
        print("可用的导入方式：")
        method_keys = list(methods.keys())
        for i, (key, method) in enumerate(methods.items(), 1):
            print(f"{i}. {method['name']}")

        print("\n选择导入方式 [1-3] (默认: 1):", end=" ")
        try:
            choice = input().strip() or "1"
            choice_idx = int(choice) - 1

            if choice_idx < 0 or choice_idx >= len(method_keys):
                print("❌ 无效选择")
                return False

            selected_method = method_keys[choice_idx]
            method_info = methods[selected_method]

            # Show instructions
            print(f"\n📋 {method_info['name']} 说明：")
            for step in method_info['steps']:
                print(f"   {step}")

            if 'code' in method_info:
                print(f"\n📝 复制以下代码到浏览器控制台：")
                print("-" * 50)
                print(method_info['code'])
                print("-" * 50)

            if 'next_steps' in method_info:
                for step in method_info['next_steps']:
                    print(f"   {step}")

            # Get cookie data
            print(f"\n请输入 Cookie 数据 (支持 JSON 格式或文件路径):")
            print("输入完成后按回车，输入 'quit' 退出：")

            cookie_input = []
            while True:
                line = input()
                if line.strip().lower() == 'quit':
                    return False
                if not line.strip():
                    break
                cookie_input.append(line)

            cookie_text = '\n'.join(cookie_input).strip()
            if not cookie_text:
                print("❌ 未输入任何数据")
                return False

            # Try to import
            if cookie_text.startswith('/') or cookie_text.endswith('.json'):
                # File path
                success = self.import_from_json_file(cookie_text)
            else:
                # Text input
                success = self.import_from_text(cookie_text)

            if success:
                print("✅ Cookie 导入成功！")
                return True
            else:
                print("❌ Cookie 导入失败，请检查格式")
                return False

        except KeyboardInterrupt:
            print("\n操作已取消")
            return False
        except ValueError:
            print("❌ 无效输入")
            return False
        except Exception as e:
            print(f"❌ 导入失败: {e}")
            return False


def get_cookie_importer() -> CookieImporter:
    """Get singleton cookie importer instance."""
    if not hasattr(get_cookie_importer, '_instance'):
        get_cookie_importer._instance = CookieImporter()
    return get_cookie_importer._instance