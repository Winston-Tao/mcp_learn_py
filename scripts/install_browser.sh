#!/bin/bash
# Chrome/Chromium Browser Installation Script
# Supports multiple Linux distributions

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
print_banner() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}🌐 Chrome/Chromium 安装脚本${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        DISTRO=$ID
        VERSION=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
        DISTRO=$(echo "$OS" | tr '[:upper:]' '[:lower:]')
        VERSION=$(lsb_release -sr)
    elif [ -f /etc/redhat-release ]; then
        OS="Red Hat"
        DISTRO="rhel"
    elif [ -f /etc/debian_version ]; then
        OS="Debian"
        DISTRO="debian"
    else
        OS=$(uname -s)
        DISTRO="unknown"
    fi

    log_info "检测到系统: $OS ($DISTRO $VERSION)"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "检测到以 root 用户运行"
        USE_SUDO=""
    else
        log_info "检测到普通用户，将使用 sudo"
        USE_SUDO="sudo"

        # Check if sudo is available
        if ! command -v sudo &> /dev/null; then
            log_error "sudo 命令不可用，请以 root 用户运行此脚本"
            exit 1
        fi
    fi
}

# Check if Chrome/Chromium is already installed
check_existing_installation() {
    log_info "检查现有的 Chrome/Chromium 安装..."

    local chrome_paths=(
        "/usr/bin/google-chrome"
        "/usr/bin/google-chrome-stable"
        "/usr/bin/chromium-browser"
        "/usr/bin/chromium"
        "/opt/google/chrome/google-chrome"
        "/snap/bin/chromium"
    )

    for path in "${chrome_paths[@]}"; do
        if [ -x "$path" ]; then
            log_success "发现已安装的浏览器: $path"

            # Test if it works
            if "$path" --version &>/dev/null; then
                log_success "浏览器工作正常"
                return 0
            else
                log_warning "浏览器安装存在问题"
            fi
        fi
    done

    log_info "未发现可用的 Chrome/Chromium 安装"
    return 1
}

# Install Chromium on Debian/Ubuntu
install_debian_chromium() {
    log_info "在 Debian/Ubuntu 系统上安装 Chromium..."

    # Update package list
    log_info "更新软件包列表..."
    $USE_SUDO apt-get update

    # Install Chromium
    log_info "安装 Chromium 浏览器..."
    $USE_SUDO apt-get install -y chromium-browser

    # Verify installation
    if command -v chromium-browser &> /dev/null; then
        log_success "Chromium 安装成功!"
        chromium-browser --version
        return 0
    else
        log_error "Chromium 安装失败"
        return 1
    fi
}

# Install Google Chrome on Debian/Ubuntu
install_debian_chrome() {
    log_info "在 Debian/Ubuntu 系统上安装 Google Chrome..."

    # Add Google Chrome repository
    log_info "添加 Google Chrome 软件源..."

    # Download and install the signing key
    if command -v wget &> /dev/null; then
        wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | $USE_SUDO apt-key add -
    elif command -v curl &> /dev/null; then
        curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | $USE_SUDO apt-key add -
    else
        log_error "需要 wget 或 curl 来下载 Google Chrome"
        return 1
    fi

    # Add repository
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | $USE_SUDO tee /etc/apt/sources.list.d/google-chrome.list

    # Update package list
    log_info "更新软件包列表..."
    $USE_SUDO apt-get update

    # Install Google Chrome
    log_info "安装 Google Chrome..."
    $USE_SUDO apt-get install -y google-chrome-stable

    # Verify installation
    if command -v google-chrome &> /dev/null; then
        log_success "Google Chrome 安装成功!"
        google-chrome --version
        return 0
    else
        log_error "Google Chrome 安装失败"
        return 1
    fi
}

# Install Chromium on CentOS/RHEL/Fedora
install_redhat_chromium() {
    log_info "在 Red Hat 系列系统上安装 Chromium..."

    local package_manager=""
    if command -v dnf &> /dev/null; then
        package_manager="dnf"
    elif command -v yum &> /dev/null; then
        package_manager="yum"
    else
        log_error "未找到可用的包管理器 (dnf/yum)"
        return 1
    fi

    log_info "使用 $package_manager 安装 Chromium..."

    # Enable EPEL repository for CentOS/RHEL
    if [[ "$DISTRO" == "centos" || "$DISTRO" == "rhel" ]]; then
        log_info "启用 EPEL 仓库..."
        $USE_SUDO $package_manager install -y epel-release
    fi

    # Install Chromium
    $USE_SUDO $package_manager install -y chromium

    # Verify installation
    if command -v chromium-browser &> /dev/null; then
        log_success "Chromium 安装成功!"
        chromium-browser --version
        return 0
    else
        log_error "Chromium 安装失败"
        return 1
    fi
}

# Install using Snap (universal)
install_snap_chromium() {
    log_info "使用 Snap 安装 Chromium..."

    if ! command -v snap &> /dev/null; then
        log_warning "Snap 不可用，跳过 Snap 安装"
        return 1
    fi

    # Install Chromium via Snap
    $USE_SUDO snap install chromium

    # Verify installation
    if command -v chromium &> /dev/null || [ -x "/snap/bin/chromium" ]; then
        log_success "Chromium (Snap) 安装成功!"
        if command -v chromium &> /dev/null; then
            chromium --version
        else
            /snap/bin/chromium --version
        fi
        return 0
    else
        log_error "Chromium (Snap) 安装失败"
        return 1
    fi
}

# Main installation function
install_browser() {
    log_info "开始安装浏览器..."

    case "$DISTRO" in
        "ubuntu"|"debian"|"linuxmint"|"pop")
            # Try Chromium first (usually more stable)
            if install_debian_chromium; then
                return 0
            fi

            log_warning "Chromium 安装失败，尝试 Google Chrome..."
            if install_debian_chrome; then
                return 0
            fi

            log_warning "包管理器安装失败，尝试 Snap..."
            install_snap_chromium
            ;;

        "centos"|"rhel"|"fedora"|"opensuse")
            if install_redhat_chromium; then
                return 0
            fi

            log_warning "包管理器安装失败，尝试 Snap..."
            install_snap_chromium
            ;;

        *)
            log_warning "未识别的发行版，尝试通用安装方法..."

            # Try Snap first for unknown distributions
            if install_snap_chromium; then
                return 0
            fi

            log_error "无法在此系统上自动安装浏览器"
            log_info "请手动安装 Chrome 或 Chromium 浏览器:"
            echo "  - Debian/Ubuntu: sudo apt-get install chromium-browser"
            echo "  - CentOS/RHEL: sudo yum install chromium"
            echo "  - Fedora: sudo dnf install chromium"
            echo "  - 或访问 https://www.google.com/chrome/ 下载 Chrome"
            return 1
            ;;
    esac
}

# Test browser installation
test_browser() {
    log_info "测试浏览器安装..."

    local chrome_paths=(
        "google-chrome"
        "google-chrome-stable"
        "chromium-browser"
        "chromium"
        "/snap/bin/chromium"
        "/opt/google/chrome/google-chrome"
    )

    for browser in "${chrome_paths[@]}"; do
        if command -v "$browser" &> /dev/null || [ -x "$browser" ]; then
            log_info "测试浏览器: $browser"
            if "$browser" --version &>/dev/null; then
                log_success "浏览器测试成功: $browser"
                log_info "路径: $(which "$browser" 2>/dev/null || echo "$browser")"
                return 0
            fi
        fi
    done

    log_error "无法找到可用的浏览器"
    return 1
}

# Main function
main() {
    print_banner

    # Check if we need to install
    if check_existing_installation; then
        log_success "系统中已有可用的 Chrome/Chromium 浏览器"

        echo -e "\n是否要重新安装? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_info "跳过安装"
            exit 0
        fi
    fi

    # Environment checks
    detect_distro
    check_root

    # Confirm installation
    echo -e "\n将在您的系统上安装 Chrome/Chromium 浏览器"
    echo -e "系统: $OS ($DISTRO $VERSION)"
    echo -e "是否继续? (y/N): "
    read -r response

    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "用户取消安装"
        exit 0
    fi

    # Install browser
    if install_browser; then
        log_success "浏览器安装完成!"

        # Test installation
        echo -e "\n正在测试安装..."
        if test_browser; then
            log_success "安装验证成功!"
            echo -e "\n${GREEN}🎉 Chrome/Chromium 已成功安装并可以使用!${NC}"
            echo -e "现在您可以使用小红书 MCP 工具的浏览器登录功能了。"
        else
            log_warning "安装可能存在问题，请手动验证"
        fi
    else
        log_error "浏览器安装失败"
        echo -e "\n${YELLOW}💡 手动安装建议:${NC}"
        echo -e "1. 访问 https://www.google.com/chrome/ 下载 Chrome"
        echo -e "2. 或使用系统包管理器安装 Chromium"
        echo -e "3. 确保浏览器可执行并在 PATH 中"
        exit 1
    fi
}

# Handle interruption
trap 'echo -e "\n用户中断安装"; exit 130' INT

# Run main function
main "$@"