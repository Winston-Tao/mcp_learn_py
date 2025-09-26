"""Environment detection and browser compatibility utilities."""

import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from .logger import get_logger


class EnvironmentDetector:
    """Detect environment capabilities and browser availability."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def has_gui(self) -> bool:
        """Check if GUI environment is available."""
        try:
            # Check for DISPLAY environment variable (Linux/Unix)
            if os.environ.get('DISPLAY'):
                return True

            # Check for WAYLAND_DISPLAY (Wayland)
            if os.environ.get('WAYLAND_DISPLAY'):
                return True

            # Check if running on Windows (usually has GUI)
            if sys.platform.startswith('win'):
                return True

            # Check if running on macOS (usually has GUI)
            if sys.platform == 'darwin':
                return True

            return False
        except Exception as e:
            self.logger.debug(f"Error checking GUI availability: {e}")
            return False

    def find_chrome_binary(self) -> Optional[str]:
        """Find Chrome/Chromium binary path."""
        possible_paths = [
            # Common Chrome paths (Linux)
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/opt/google/chrome/google-chrome',
            # Snap packages
            '/snap/bin/chromium',
            '/snap/bin/chrome',
            # Flatpak
            '/var/lib/flatpak/app/com.google.Chrome/current/active/export/bin/com.google.Chrome',
            # macOS
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            # Windows
            'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
            'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        ]

        # Check common paths
        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                self.logger.debug(f"Found Chrome at: {path}")
                return path

        # Try to find using 'which' command
        try:
            for cmd in ['google-chrome', 'google-chrome-stable', 'chromium-browser', 'chromium']:
                result = shutil.which(cmd)
                if result:
                    self.logger.debug(f"Found Chrome via 'which': {result}")
                    return result
        except Exception as e:
            self.logger.debug(f"Error using 'which' command: {e}")

        return None

    def can_install_chrome(self) -> bool:
        """Check if Chrome can be installed on this system."""
        try:
            # Check if we have package manager access
            package_managers = ['apt-get', 'yum', 'dnf', 'pacman', 'zypper']
            for pm in package_managers:
                if shutil.which(pm):
                    return True
            return False
        except Exception:
            return False

    def get_package_manager(self) -> Optional[str]:
        """Get the available package manager."""
        package_managers = {
            'apt-get': 'debian',
            'yum': 'centos',
            'dnf': 'fedora',
            'pacman': 'arch',
            'zypper': 'opensuse'
        }

        for pm, distro in package_managers.items():
            if shutil.which(pm):
                return pm
        return None

    def test_chrome_functionality(self, chrome_path: str) -> bool:
        """Test if Chrome can start successfully."""
        try:
            # Try to start Chrome with minimal arguments
            result = subprocess.run([
                chrome_path, '--version'
            ], capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            self.logger.debug(f"Chrome functionality test failed: {e}")
            return False

    def get_environment_info(self) -> Dict[str, any]:
        """Get comprehensive environment information."""
        chrome_path = self.find_chrome_binary()

        info = {
            'platform': sys.platform,
            'has_gui': self.has_gui(),
            'chrome_path': chrome_path,
            'chrome_works': self.test_chrome_functionality(chrome_path) if chrome_path else False,
            'can_install_chrome': self.can_install_chrome(),
            'package_manager': self.get_package_manager(),
            'display': os.environ.get('DISPLAY'),
            'wayland_display': os.environ.get('WAYLAND_DISPLAY'),
            'user': os.environ.get('USER', 'unknown'),
            'home': os.environ.get('HOME', '/tmp'),
            'is_root': os.geteuid() == 0 if hasattr(os, 'geteuid') else False,
            'shell': os.environ.get('SHELL', 'unknown'),
        }

        self.logger.debug(f"Environment info: {info}")
        return info

    def get_login_recommendations(self) -> Dict[str, any]:
        """Get recommendations for login methods based on environment."""
        env_info = self.get_environment_info()
        recommendations = {
            'primary_method': None,
            'alternative_methods': [],
            'notes': [],
            'install_instructions': None,
            'manual_instructions': None
        }

        if env_info['chrome_works'] and env_info['has_gui']:
            # Best case: GUI + Working Chrome
            recommendations['primary_method'] = 'interactive_browser'
            recommendations['alternative_methods'] = ['manual_cookie_import', 'qr_code']
            recommendations['notes'].append("✅ 完整的浏览器环境支持")
            recommendations['notes'].append("🎯 推荐使用交互式浏览器登录")

        elif env_info['chrome_works'] and not env_info['has_gui']:
            # Headless Chrome available
            recommendations['primary_method'] = 'qr_code'
            recommendations['alternative_methods'] = ['manual_cookie_import', 'remote_browser']
            recommendations['notes'].append("⚠️  检测到终端环境（无GUI）")
            recommendations['notes'].append("📱 推荐使用二维码登录")

        elif env_info['can_install_chrome'] and env_info['package_manager']:
            # Can install Chrome
            recommendations['primary_method'] = 'install_chrome'
            recommendations['alternative_methods'] = ['manual_cookie_import', 'remote_browser']
            recommendations['notes'].append("❌ 未检测到 Chrome 浏览器")
            recommendations['notes'].append("⚙️  可以自动安装 Chromium")
            recommendations['install_instructions'] = self.get_install_instructions()

        else:
            # Last resort: Manual cookie import
            recommendations['primary_method'] = 'manual_cookie_import'
            recommendations['alternative_methods'] = ['remote_browser']
            recommendations['notes'].append("❌ 无法使用浏览器自动登录")
            recommendations['notes'].append("📋 请使用手动 Cookie 导入")
            recommendations['manual_instructions'] = self.get_manual_instructions()

        return recommendations

    def get_install_instructions(self) -> Dict[str, str]:
        """Get Chrome installation instructions for current system."""
        pm = self.get_package_manager()

        instructions = {
            'apt-get': {
                'description': 'Debian/Ubuntu 系统安装说明',
                'commands': [
                    'sudo apt-get update',
                    'sudo apt-get install -y chromium-browser',
                    # Alternative: Install Google Chrome
                    '# 或者安装 Google Chrome:',
                    'wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -',
                    'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list',
                    'sudo apt-get update',
                    'sudo apt-get install -y google-chrome-stable'
                ]
            },
            'yum': {
                'description': 'CentOS/RHEL 系统安装说明',
                'commands': [
                    'sudo yum install -y chromium',
                    '# 或者安装 Google Chrome:',
                    'wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm',
                    'sudo yum install -y google-chrome-stable_current_x86_64.rpm'
                ]
            },
            'dnf': {
                'description': 'Fedora 系统安装说明',
                'commands': [
                    'sudo dnf install -y chromium',
                    '# 或者安装 Google Chrome:',
                    'wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm',
                    'sudo dnf install -y google-chrome-stable_current_x86_64.rpm'
                ]
            }
        }

        return instructions.get(pm, {
            'description': '通用安装说明',
            'commands': ['请访问 https://www.google.com/chrome/ 下载 Chrome 浏览器']
        })

    def get_manual_instructions(self) -> Dict[str, any]:
        """Get manual cookie import instructions."""
        return {
            'description': '手动 Cookie 导入说明',
            'steps': [
                '1. 在有浏览器的设备上访问 https://www.xiaohongshu.com',
                '2. 完成登录（微信扫码或手机号登录）',
                '3. 按 F12 打开开发者工具',
                '4. 切换到 Console (控制台) 标签',
                '5. 粘贴以下代码并按回车:',
                '''copy(JSON.stringify(document.cookie.split(';').map(c => {
    const [name, value] = c.trim().split('=');
    return {name, value, domain: '.xiaohongshu.com'};
})))''',
                '6. Cookie 数据已复制到剪贴板',
                '7. 将数据保存到文件 cookies.json',
                '8. 上传到服务器并使用 Cookie 导入功能'
            ],
            'alternative': {
                'description': '或者使用浏览器扩展导出 Cookie',
                'extensions': [
                    'Cookie-Editor (Chrome/Firefox)',
                    'EditThisCookie (Chrome)',
                    'cookies.txt (Firefox)'
                ]
            }
        }


# Global singleton instance
_environment_detector = None


def get_environment_detector() -> EnvironmentDetector:
    """Get singleton environment detector instance."""
    global _environment_detector
    if _environment_detector is None:
        _environment_detector = EnvironmentDetector()
    return _environment_detector