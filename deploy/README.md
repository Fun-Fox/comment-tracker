# Comment Tracker Linux 部署指南

## 📋 系统要求

- **操作系统**: Ubuntu 20.04/22.04, Debian 11/12, CentOS 8+
- **Python**: 3.12+
- **内存**: 至少 2GB RAM（推荐 4GB）
- **磁盘**: 至少 5GB 可用空间
- **网络**: 可访问 TikTok 和小红书

## 🚀 快速部署

### 方式 1: 使用 Docker（推荐）

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd comment-tracker

# 2. 配置环境变量
cp .env.example .env
vim .env  # 编辑配置

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

### 方式 2: 使用自动化脚本

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd comment-tracker

# 2. 运行部署脚本（需要 root 权限）
sudo bash deploy/deploy.sh
```

### 方式 3: 手动部署

#### 1. 安装系统依赖

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y \
    python3.12 python3.12-venv python3-pip \
    wget gnupg libnss3 libnspr4 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2
```

**CentOS/RHEL:**
```bash
sudo dnf install -y epel-release
sudo dnf install -y \
    python3.12 python3.12-devel git curl wget \
    nss atk at-spi2-atk cups-libs libdrm \
    libxkbcommon libXcomposite libXdamage \
    libXfixes libXrandr mesa-libgbm pango cairo alsa-lib
```

#### 2. 创建应用目录

```bash
sudo mkdir -p /opt/comment-tracker
sudo useradd -r -s /bin/false comment-tracker
sudo chown -R comment-tracker:comment-tracker /opt/comment-tracker
```

#### 3. 部署代码

```bash
# 复制代码到 /opt/comment-tracker
sudo cp -r . /opt/comment-tracker/
cd /opt/comment-tracker
```

#### 4. 创建虚拟环境

```bash
python3.12 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 安装 Playwright
playwright install chromium
playwright install-deps chromium
```

#### 5. 配置环境变量

```bash
cp .env.example .env
vim .env  # 编辑配置

# 设置权限
chmod 600 .env
sudo chown comment-tracker:comment-tracker .env
```

#### 6. 安装 systemd 服务

```bash
# 复制 service 文件
sudo cp deploy/comment-tracker.service /etc/systemd/system/
sudo chmod 755 /home/callfans/data/comment-tracker/logs
# 重新加载 systemd
sudo systemctl daemon-reload

# 启用并启动服务
sudo systemctl enable comment-tracker
sudo systemctl start comment-tracker

# 查看状态
sudo systemctl status comment-tracker
```

## 🛡️ 配置 Nginx 反向代理

### 1. 安装 Nginx

```bash
# Ubuntu/Debian
sudo apt-get install -y nginx

# CentOS/RHEL
sudo dnf install -y nginx
```

### 2. 配置 Nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/comment-tracker
sudo ln -sf /etc/nginx/sites-available/comment-tracker /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

### 3. 配置 SSL（可选）

```bash
# 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 获取 SSL 证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

## 📝 常用管理命令

### 服务管理

```bash
# 启动服务
sudo systemctl start comment-tracker

# 停止服务
sudo systemctl stop comment-tracker

# 重启服务
sudo systemctl restart comment-tracker

# 查看状态
sudo systemctl status comment-tracker

# 设置开机自启
sudo systemctl enable comment-tracker

# 取消开机自启
sudo systemctl disable comment-tracker
```

### 日志查看

```bash
# 查看服务日志
sudo journalctl -u comment-tracker -f

# 查看应用日志
tail -f /opt/comment-tracker/logs/service.log

# 查看错误日志
tail -f /opt/comment-tracker/logs/error.log
```

### Docker 管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 更新镜像
docker-compose pull
docker-compose up -d
```

## 🔧 配置说明

### 环境变量 (.env)

```bash
# 调试模式（生产环境设置为 false）
DEBUG=false

# 飞书 Webhook
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_HOOK_ID
FEISHU_SIGN_SECRET=YOUR_SECRET

# 服务配置
HOST=0.0.0.0
PORT=8000

# 代理配置（如需要）
PLAYWRIGHT_PROXY=http://127.0.0.1:10405
```

### 目录结构

```
/opt/comment-tracker/
├── main.py              # 应用入口
├── .env                 # 环境变量（权限 600）
├── venv/                # Python 虚拟环境
├── logs/                # 应用日志
├── debug_data/          # 调试数据（DEBUG=true 时生成）
├── captured_data/       # 捕获数据
└── deploy/              # 部署配置
```

## 🔍 故障排查

### 服务无法启动

```bash
# 查看详细错误
sudo journalctl -u comment-tracker -n 50 --no-pager

# 检查 Python 环境
cd /opt/comment-tracker
source venv/bin/activate
python main.py  # 手动运行查看错误
```

### Playwright 浏览器问题

```bash
# 重新安装 Playwright
cd /opt/comment-tracker
source venv/bin/activate
playwright install --force chromium
playwright install-deps chromium
```

### 端口被占用

```bash
# 查看端口占用
sudo lsof -i :8000

# 修改端口
vim /opt/comment-tracker/.env
# 修改 PORT=8001
```

### 权限问题

```bash
# 修复权限
sudo chown -R comment-tracker:comment-tracker /opt/comment-tracker
sudo chmod 600 /opt/comment-tracker/.env
```

## 📊 性能优化

### 1. 增加 Worker 进程（多进程部署）

修改 `main.py` 启动参数：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 2. 调整 systemd 资源限制

编辑 `/etc/systemd/system/comment-tracker.service`:

```ini
[Service]
LimitNOFILE=65536
LimitNPROC=4096
```

### 3. 配置日志轮转

创建 `/etc/logrotate.d/comment-tracker`:

```
/opt/comment-tracker/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 comment-tracker comment-tracker
}
```

## 🔐 安全建议

1. **防火墙配置**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

2. **定期更新**
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   ```

3. **监控服务**
   ```bash
   # 安装监控工具
   sudo apt-get install -y htop iotop
   
   # 查看资源使用
   htop
   ```

4. **备份数据**
   ```bash
   # 备份环境变量
   cp /opt/comment-tracker/.env /backup/

   # 备份数据
   tar -czf /backup/comment-tracker-$(date +%Y%m%d).tar.gz \
       /opt/comment-tracker/debug_data \
       /opt/comment-tracker/captured_data
   ```

## 📞 技术支持

- 查看 API 文档: `http://your-domain.com/docs`
- 健康检查: `http://your-domain.com/health`
- 查看日志: `sudo journalctl -u comment-tracker -f`

---

**部署完成后，请确保测试以下功能：**
- ✅ 服务正常运行
- ✅ API 接口可访问
- ✅ 飞书通知正常发送
- ✅ 日志正常记录
- ✅ 数据持久化正常
