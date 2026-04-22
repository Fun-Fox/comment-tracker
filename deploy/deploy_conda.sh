#!/bin/bash

# Comment Tracker 手动部署脚本（使用 conda 环境）
# 适用于已有 conda 环境的 Linux 系统

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

# 配置变量
APP_DIR="/home/callfans/data/comment-tracker"
CONDA_ENV="py312"
USER="callfans"

echo "==================================="
echo "  Comment Tracker 部署脚本"
echo "==================================="
echo

# 1. 创建应用目录
log_info "创建应用目录..."
mkdir -p $APP_DIR
mkdir -p $APP_DIR/logs
mkdir -p $APP_DIR/debug_data
mkdir -p $APP_DIR/captured_data

# 2. 检查 conda 环境
log_info "检查 conda 环境..."
if ! command -v conda &> /dev/null; then
    log_error "未找到 conda，请先安装 Miniconda/Anaconda"
    exit 1
fi

# 3. 激活环境并安装依赖
log_info "安装 Python 依赖..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate $CONDA_ENV || {
    log_warn "环境 $CONDA_ENV 不存在，正在创建..."
    conda create -n $CONDA_ENV python=3.12 -y
    conda activate $CONDA_ENV
}

cd $APP_DIR

# 复制 requirements.txt（如果存在）
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    log_warn "未找到 requirements.txt，跳过依赖安装"
fi

# 4. 安装 Playwright
log_info "安装 Playwright 浏览器..."
playwright install chromium
playwright install-deps chromium

# 5. 配置环境变量
log_info "配置环境变量..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        log_warn "请编辑 $APP_DIR/.env 文件，配置必要的环境变量"
    else
        log_error "未找到 .env 或 .env.example 文件"
        exit 1
    fi
fi

chmod 600 .env

# 6. 设置权限
log_info "设置文件权限..."
chown -R $USER:$USER $APP_DIR

# 7. 安装 systemd 服务
log_info "安装 systemd 服务..."
sudo cp deploy/comment-tracker.service /etc/systemd/system/
sudo cp deploy/streamlit.service /etc/systemd/system/

# 重新加载 systemd
sudo systemctl daemon-reload

# 启用服务
sudo systemctl enable comment-tracker
sudo systemctl enable comment-tracker-ui

log_info "服务安装完成！"
echo
echo "==================================="
log_info "后续步骤："
echo "==================================="
echo
echo "1. 编辑配置文件:"
echo "   vim $APP_DIR/.env"
echo
echo "2. 启动服务:"
echo "   sudo systemctl start comment-tracker"
echo "   sudo systemctl start comment-tracker-ui"
echo
echo "3. 查看状态:"
echo "   sudo systemctl status comment-tracker"
echo "   sudo systemctl status comment-tracker-ui"
echo
echo "4. 查看日志:"
echo "   tail -f $APP_DIR/logs/service.log"
echo "   tail -f $APP_DIR/logs/streamlit.log"
echo
echo "5. 访问地址:"
echo "   API:      http://localhost:9000/docs"
echo "   前端界面:  http://localhost:8501"
echo
