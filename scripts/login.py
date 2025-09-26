#!/usr/bin/env python3
"""交互式登录脚本 - 小红书MCP服务器登录管理"""

import sys
import asyncio
import argparse
import time
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.tools.xiaohongshu_service import XiaohongshuService
from src.tools.xiaohongshu_models import XiaohongshuConfig
from src.utils.logger import get_logger
from src.utils.cookie_manager import get_cookie_manager
from src.utils.environment import get_environment_detector
from src.utils.cookie_importer import get_cookie_importer


def print_banner():
    """Print login script banner."""
    print("\n" + "=" * 60)
    print("🔑 小红书 MCP 服务器 - 智能登录工具")
    print("=" * 60)


def print_status(message: str, status_type: str = "info"):
    """Print status message with formatting."""
    if status_type == "success":
        print(f"✅ {message}")
    elif status_type == "error":
        print(f"❌ {message}")
    elif status_type == "warning":
        print(f"⚠️  {message}")
    elif status_type == "info":
        print(f"ℹ️  {message}")
    else:
        print(f"   {message}")


async def check_login_status(service: XiaohongshuService) -> bool:
    """Check current login status."""
    try:
        print_status("检查当前登录状态...")
        result = await service.check_login_status()

        if result.is_logged_in:
            print_status("您已成功登录小红书！", "success")
            if result.user_info:
                print_status(f"登录信息: {result.user_info}")
            return True
        else:
            print_status("您尚未登录小红书", "warning")
            print_status(f"状态说明: {result.message}")
            return False

    except Exception as e:
        print_status(f"检查登录状态失败: {e}", "error")
        return False


def show_environment_info():
    """Show environment information."""
    try:
        env_detector = get_environment_detector()
        env_info = env_detector.get_environment_info()

        print_status("环境信息:")
        print_status(f"平台: {env_info['platform']}")
        print_status(f"GUI 支持: {'是' if env_info['has_gui'] else '否'}")
        print_status(f"Chrome 路径: {env_info['chrome_path'] or '未找到'}")
        print_status(f"Chrome 可用: {'是' if env_info['chrome_works'] else '否'}")
        print_status(f"可安装 Chrome: {'是' if env_info['can_install_chrome'] else '否'}")
        print_status(f"包管理器: {env_info['package_manager'] or '未找到'}")

    except Exception as e:
        print_status(f"获取环境信息失败: {e}", "error")


def show_login_recommendations():
    """Show login method recommendations based on environment."""
    try:
        env_detector = get_environment_detector()
        recommendations = env_detector.get_login_recommendations()

        print()
        print_status("🎯 推荐的登录方案:")

        # Show notes
        for note in recommendations['notes']:
            print_status(note)

        print()
        print_status(f"主要方法: {recommendations['primary_method']}")

        if recommendations['alternative_methods']:
            print_status("备选方法: " + ", ".join(recommendations['alternative_methods']))

        # Show specific instructions if available
        if recommendations['install_instructions']:
            print("\n📦 Chrome 安装说明:")
            install_info = recommendations['install_instructions']
            print_status(install_info['description'])
            for cmd in install_info['commands']:
                print(f"   {cmd}")

        if recommendations['manual_instructions']:
            print("\n📋 手动登录说明:")
            manual_info = recommendations['manual_instructions']
            print_status(manual_info['description'])
            for step in manual_info['steps']:
                print(f"   {step}")

        return recommendations

    except Exception as e:
        print_status(f"获取登录建议失败: {e}", "error")
        return None


async def perform_browser_login(service: XiaohongshuService) -> bool:
    """Perform browser-based login."""
    try:
        print_status("启动浏览器登录流程...", "info")
        print()
        print("📱 浏览器登录步骤:")
        print("   1. 浏览器将会自动打开小红书页面")
        print("   2. 如果出现登录窗口，请使用微信扫码或手机号登录")
        print("   3. 登录成功后，登录状态将被自动保存")
        print("   4. 按 Ctrl+C 可随时退出")
        print()

        # Wait for user confirmation
        try:
            input("请按 Enter 键继续，或按 Ctrl+C 退出...")
        except KeyboardInterrupt:
            print_status("用户取消登录", "info")
            return False

        print_status("正在初始化浏览器（非无头模式）...")

        # Create service with non-headless mode for login
        config = XiaohongshuConfig(
            headless=False,  # 必须使用非无头模式进行登录
            timeout=service.config.timeout,
            max_images_per_post=service.config.max_images_per_post,
            max_title_length=service.config.max_title_length,
            max_content_length=service.config.max_content_length,
            user_agent=service.config.user_agent,
            browser_path=service.config.browser_path
        )

        login_service = XiaohongshuService(config)

        try:
            # Check initial status
            print_status("导航到小红书首页...")
            initial_status = await login_service.check_login_status()

            if initial_status.is_logged_in:
                print_status("检测到您已登录！", "success")
                return True

            print_status("检测到未登录状态，请在浏览器中完成登录...")
            print()
            print("💡 提示:")
            print("   - 如果看到登录窗口，请使用您偏好的登录方式")
            print("   - 登录成功后，页面会自动刷新")
            print("   - 本工具将在后台检测登录状态")
            print()

            # Wait for login completion
            max_wait_time = 300  # 5 minutes
            check_interval = 5   # 5 seconds
            elapsed = 0

            print_status(f"等待登录完成（超时时间: {max_wait_time}秒）...")

            while elapsed < max_wait_time:
                try:
                    # Check login status
                    current_status = await login_service.check_login_status()

                    if current_status.is_logged_in:
                        print_status("登录成功！", "success")
                        print_status("登录状态已自动保存，下次使用时将自动恢复登录")
                        return True

                    # Show progress
                    remaining = max_wait_time - elapsed
                    print(f"\r⏳ 等待登录中... 剩余时间: {remaining}秒", end="", flush=True)

                    await asyncio.sleep(check_interval)
                    elapsed += check_interval

                except KeyboardInterrupt:
                    print_status("\n用户取消登录", "info")
                    return False
                except Exception as e:
                    print_status(f"\n检查登录状态时出错: {e}", "warning")
                    await asyncio.sleep(check_interval)
                    elapsed += check_interval

            print_status(f"\n登录超时（{max_wait_time}秒），请重试", "error")
            return False

        finally:
            await login_service.cleanup()

    except Exception as e:
        print_status(f"浏览器登录失败: {e}", "error")
        return False


def perform_manual_cookie_import() -> bool:
    """Perform manual cookie import."""
    try:
        print_status("启动手动 Cookie 导入流程...", "info")
        print()

        cookie_importer = get_cookie_importer()
        return cookie_importer.interactive_import()

    except Exception as e:
        print_status(f"手动 Cookie 导入失败: {e}", "error")
        return False


async def install_browser_and_login(service: XiaohongshuService) -> bool:
    """Install browser and perform login."""
    try:
        env_detector = get_environment_detector()

        if not env_detector.can_install_chrome():
            print_status("无法在此环境安装 Chrome 浏览器", "error")
            return False

        install_info = env_detector.get_install_instructions()

        print_status("Chrome 浏览器安装", "info")
        print()
        print_status(install_info['description'])
        print("安装命令:")
        for cmd in install_info['commands']:
            print(f"   {cmd}")
        print()

        try:
            confirm = input("是否要自动安装 Chromium 浏览器? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print_status("用户取消安装", "info")
                return False
        except KeyboardInterrupt:
            print_status("\n用户取消安装", "info")
            return False

        # Get package manager
        pm = env_detector.get_package_manager()
        if not pm:
            print_status("未找到可用的包管理器", "error")
            return False

        print_status(f"使用 {pm} 安装 Chromium...")

        import subprocess
        try:
            if pm == 'apt-get':
                # Update package list first
                print_status("更新软件包列表...")
                subprocess.run(['sudo', 'apt-get', 'update'], check=True)
                print_status("安装 Chromium...")
                subprocess.run(['sudo', 'apt-get', 'install', '-y', 'chromium-browser'], check=True)
            else:
                print_status(f"请手动运行安装命令", "warning")
                return False

            print_status("Chromium 安装成功！", "success")

            # Verify installation
            chrome_path = env_detector.find_chrome_binary()
            if chrome_path:
                print_status(f"Chrome 路径: {chrome_path}")
                # Now try browser login
                return await perform_browser_login(service)
            else:
                print_status("安装后未能找到 Chrome，请检查安装", "error")
                return False

        except subprocess.CalledProcessError as e:
            print_status(f"安装失败: {e}", "error")
            return False
        except FileNotFoundError:
            print_status("未找到 sudo 命令，需要管理员权限", "error")
            return False

    except Exception as e:
        print_status(f"安装浏览器失败: {e}", "error")
        return False


async def perform_interactive_login(service: XiaohongshuService) -> bool:
    """Smart interactive login based on environment capabilities."""
    try:
        env_detector = get_environment_detector()
        recommendations = env_detector.get_login_recommendations()

        if not recommendations:
            print_status("无法获取登录建议，尝试默认浏览器登录...", "warning")
            return await perform_browser_login(service)

        primary_method = recommendations['primary_method']

        if primary_method == 'interactive_browser':
            return await perform_browser_login(service)
        elif primary_method == 'manual_cookie_import':
            return perform_manual_cookie_import()
        elif primary_method == 'install_chrome':
            return await install_browser_and_login(service)
        elif primary_method == 'qr_code':
            # For now, fallback to manual cookie import
            print_status("检测到终端环境，推荐使用手动 Cookie 导入", "info")
            return perform_manual_cookie_import()
        else:
            print_status(f"不支持的登录方法: {primary_method}", "error")
            return False

    except Exception as e:
        print_status(f"智能登录失败: {e}", "error")
        # Fallback to manual cookie import
        print_status("尝试备用方案：手动 Cookie 导入...", "info")
        return perform_manual_cookie_import()


def show_cookie_info():
    """Show cookie information."""
    try:
        cookie_manager = get_cookie_manager()
        info = cookie_manager.get_cookie_info()

        print_status(f"Cookie 文件路径: {info['path']}")
        print_status(f"Cookie 文件存在: {'是' if info['exists'] else '否'}")

        if info['exists']:
            print_status(f"Cookie 数量: {info['count']}")
            if info['timestamp']:
                timestamp = int(info['timestamp']) / 1000
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                print_status(f"保存时间: {time_str}")
            if info['domain']:
                print_status(f"域名: {info['domain']}")

    except Exception as e:
        print_status(f"获取 Cookie 信息失败: {e}", "error")


def clear_login_session():
    """Clear saved login session."""
    try:
        cookie_manager = get_cookie_manager()
        if cookie_manager.clear_cookies():
            print_status("登录会话已清除", "success")
        else:
            print_status("清除登录会话失败", "error")
    except Exception as e:
        print_status(f"清除登录会话失败: {e}", "error")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="小红书 MCP 服务器交互式登录工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/login.py                    # 检查登录状态并引导登录
  python scripts/login.py --login           # 强制进入交互式登录
  python scripts/login.py --status          # 仅检查登录状态
  python scripts/login.py --info            # 显示 Cookie 信息
  python scripts/login.py --clear           # 清除保存的登录状态
        """
    )

    parser.add_argument(
        "--login",
        action="store_true",
        help="强制进入交互式登录流程"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="仅检查登录状态"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="显示 Cookie 信息"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="清除保存的登录会话"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="使用无头模式（仅用于状态检查）"
    )
    parser.add_argument(
        "--env-info",
        action="store_true",
        help="显示环境信息和登录建议"
    )
    parser.add_argument(
        "--method",
        choices=["browser", "manual", "install", "auto"],
        default="auto",
        help="指定登录方法 (browser=浏览器, manual=手动Cookie, install=安装浏览器, auto=自动检测)"
    )

    args = parser.parse_args()

    print_banner()

    # Handle specific commands
    if args.info:
        show_cookie_info()
        return

    if args.clear:
        clear_login_session()
        return

    if args.env_info:
        show_environment_info()
        show_login_recommendations()
        return

    # Setup service
    logger = get_logger(__name__)

    # Use headless mode only for status checks, never for login
    use_headless = args.headless and (args.status or not args.login)

    config = XiaohongshuConfig(
        headless=use_headless,
        timeout=30,
        max_images_per_post=9,
        max_title_length=20,
        max_content_length=1000,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        browser_path=None
    )

    service = XiaohongshuService(config)

    try:
        # Check current status first
        is_logged_in = await check_login_status(service)

        if args.status:
            # Status-only mode
            exit_code = 0 if is_logged_in else 1
            sys.exit(exit_code)

        if is_logged_in and not args.login:
            print_status("您已登录，无需重新登录！", "success")
            print_status("如需重新登录，请使用 --login 参数")
            return

        if not is_logged_in or args.login:
            # Show environment recommendations first
            if args.method == "auto":
                recommendations = show_login_recommendations()
                print()

            # Need to login - cleanup current service first to avoid conflicts
            await service.cleanup()

            print()
            success = False

            # Route to specific login method
            if args.method == "browser":
                success = await perform_browser_login(service)
            elif args.method == "manual":
                success = perform_manual_cookie_import()
            elif args.method == "install":
                success = await install_browser_and_login(service)
            else:  # auto
                success = await perform_interactive_login(service)

            if success:
                print_status("登录流程完成！", "success")
                # Verify final status
                await check_login_status(service)
            else:
                print_status("登录流程未完成", "warning")
                print_status("您可以尝试其他登录方法：")
                print_status("  --method manual    手动 Cookie 导入")
                print_status("  --method browser   强制浏览器登录")
                print_status("  --method install   安装浏览器")
                print_status("  --env-info         查看环境信息")
                sys.exit(1)

    except KeyboardInterrupt:
        print_status("\n操作已取消", "info")
        sys.exit(0)
    except Exception as e:
        print_status(f"运行出错: {e}", "error")
        logger.error(f"Login script error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await service.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_status("\n程序已退出", "info")
        sys.exit(0)
    except Exception as e:
        print_status(f"程序异常退出: {e}", "error")
        sys.exit(1)