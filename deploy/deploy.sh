#!/bin/bash

# Comment Tracker 部署脚本
# 适用于 Ubuntu 20.04/22.04, Debian 11/12, CentOS 8+

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以 root 运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户运行此脚本 (sudo)"
        exit 1
    fi
}

# 检测操作系统
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        log_error "无法检测操作系统"
        exit 1
    fi
    log_info "检测到操作系统: $OS $VERSION"
}

# 安装系统依赖
install_system_deps() {
    log_info "安装系统依赖..."
    
    case $OS in
        ubuntu|debian)
            apt-get update
            apt-get install -y \
                python3.12 \
                python3.12-venv \
                python3-pip \
                git \
                curl \
                wget \
                gnupg \
                libnss3 \
                libnspr4 \
                libatk1.0-0 \
                libatk-bridge2.0-0 \
                libcups2 \
                libdrm2 \
                libxkbcommon0 \
                libxcomposite1 \
                libxdamage1 \
                libxfixes3 \
                libxrandr2 \
                libgbm1 \
                libpango-1.0-0 \
                libcairo2 \
                libasound2
            ;;
        centos|rhel|almalinux|rocky)
            dnf install -y epel-release
            dnf install -y \
                python3.12 \
                python3.12-devel \
                git \
                curl \
                wget \
                nss \
                atk \
                at-spi2-atk \
                cups-libs \
                libdrm \
                libxkbcommon \
                libXcomposite \
                libXdamage \
                libXfixes \
                libXrandr \
                mesa-libgbm \
                pango \
                cairo \
                alsa-lib
            ;;
        *)
            log_error "不支持的操作系统: $OS"
            exit 1
            ;;
    esac
    
    log_info "系统依赖安装完成"
}

# 创建应用目录
create_app_directory() {
    log_info "创建应用目录..."
    APP_DIR="/opt/comment-tracker"
    
    mkdir -p $APP_DIR
    mkdir -p $APP_DIR/logs
    mkdir -p $APP_DIR/debug_data
    mkdir -p $APP_DIR/captured_data
    
    # 设置权限
    useradd -r -s /bin/false comment-tracker 2>/dev/null || true
    chown -R comment-tracker:comment-tracker $APP_DIR
    
    log_info "应用目录创建完成: $APP_DIR"
}

# 部署应用代码
deploy_app() {
    log_info "部署应用代码..."
    APP_DIR="/opt/comment-tracker"
    
    # 如果有 git 仓库，可以克隆
    # git clone <your-repo-url> $APP_DIR
    
    # 或者从本地复制
    # cp -r /path/to/local/code/* $APP_DIR/
    
    log_info "请手动将代码复制到 $APP_DIR 目录"
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
}

# 创建虚拟环境
create_venv() {
    log_info "创建 Python 虚拟环境..."
    APP_DIR="/opt/comment-tracker"
    
    cd $APP_DIR
    python3.12 -m venv venv
    source $APP_DIR/venv/bin/activate
    
    # 升级 pip
    pip install --upgrade pip
    
    # 安装依赖
    pip install -r requirements.txt
    
    # 安装 Playwright
    playwright install chromium
    playwright install-deps chromium
    
    log_info "虚拟环境创建完成"
}

# 配置环境变量
setup_env() {
    log_info "配置环境变量..."
    APP_DIR="/opt/comment-tracker"
    
    if [ ! -f $APP_DIR/.env ]; then
        cp $APP_DIR/.env.example $APP_DIR/.env
        log_warn "请编辑 $APP_DIR/.env 文件，配置必要的环境变量"
        read -p "按 Enter 继续..."
    fi
    
    # 设置正确的权限
    chmod 600 $APP_DIR/.env
    chown comment-tracker:comment-tracker $APP_DIR/.env
}

# 安装 systemd 服务
install_service() {
    log_info "安装 systemd 服务..."
    APP_DIR="/opt/comment-tracker"
    
    # 复制 service 文件
    cp $APP_DIR/deploy/comment-tracker.service /etc/systemd/system/
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    # 启用并启动服务
    systemctl enable comment-tracker
    systemctl start comment-tracker
    
    log_info "systemd 服务安装完成"
}

# 安装 Nginx（可选）
install_nginx() {
    log_info "安装 Nginx..."
    
    read -p "是否安装并配置 Nginx？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return
    fi
    
    case $OS in
        ubuntu|debian)
            apt-get install -y nginx
            ;;
        centos|rhel|almalinux|rocky)
            dnf install -y nginx
            ;;
    esac
    
    # 复制 Nginx 配置
    APP_DIR="/opt/comment-tracker"
    cp $APP_DIR/deploy/nginx.conf /etc/nginx/sites-available/comment-tracker
    
    # 创建符号链接
    ln -sf /etc/nginx/sites-available/comment-tracker /etc/nginx/sites-enabled/
    
    # 测试配置
    nginx -t
    
    # 重启 Nginx
    systemctl restart nginx
    systemctl enable nginx
    
    log_info "Nginx 安装完成"
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙..."
    
    read -p "是否配置防火墙（开放 80/443 端口）？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return
    fi
    
    case $OS in
        ubuntu|debian)
            ufw allow 80/tcp
            ufw allow 443/tcp
            ;;
        centos|rhel|almalinux|rocky)
            firewall-cmd --permanent --add-service=http
            firewall-cmd --permanent --add-service=https
            firewall-cmd --reload
            ;;
    esac
    
    log_info "防火墙配置完成"
}

# 显示服务状态
show_status() {
    log_info "服务状态:"
    systemctl status comment-tracker --no-pager
    echo
    log_info "查看日志:"
    echo "  journalctl -u comment-tracker -f"
    echo
    log_info "访问地址:"
    echo "  http://localhost:8000/docs (API 文档)"
    echo "  http://localhost:8000/health (健康检查)"
}

# 主函数
main() {
    echo "==================================="
    echo "  Comment Tracker 部署脚本"
    echo "==================================="
    echo
    
    check_root
    detect_os
    
    install_system_deps
    create_app_directory
    deploy_app
    create_venv
    setup_env
    install_service
    install_nginx
    setup_firewall
    
    echo
    echo "==================================="
    log_info "部署完成！"
    echo "==================================="
    show_status
}

# 运行主函数
main
