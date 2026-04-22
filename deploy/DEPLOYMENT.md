# Comment Tracker systemd 部署指南（Conda 环境）

## 📋 前置要求

- Linux 系统（Ubuntu/CentOS/Debian）
- 已安装 Miniconda/Anaconda
- Conda 环境 `py312`（Python 3.12）
- 用户 `callfans`（或修改为实际用户）

## 🚀 快速部署

### 方式 1: 使用自动化脚本

```bash
# 1. 克隆项目到目标目录
git clone <your-repo-url> /home/callfans/data/comment-tracker
cd /home/callfans/data/comment-tracker

# 2. 运行部署脚本
bash deploy/deploy_conda.sh

# 3. 编辑配置文件
vim .env

# 4. 启动服务
sudo systemctl start comment-tracker
sudo systemctl start comment-tracker-ui
```

### 方式 2: 手动部署

#### 1. 创建目录结构

```bash
mkdir -p /home/callfans/data/comment-tracker
mkdir -p /home/callfans/data/comment-tracker/logs
mkdir -p /home/callfans/data/comment-tracker/debug_data
mkdir -p /home/callfans/data/comment-tracker/captured_data
```

#### 2. 部署代码

```bash
cd /home/callfans/data/comment-tracker
# 复制代码到此目录
```

#### 3. 安装依赖

```bash
# 激活 conda 环境
conda activate py312

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright
playwright install chromium
playwright install-deps chromium
```

#### 4. 配置环境变量

```bash
cp .env.example .env
vim .env  # 编辑配置

# 设置权限
chmod 600 .env
```

#### 5. 安装 systemd 服务

```bash
# 复制 service 文件
sudo cp deploy/comment-tracker.service /etc/systemd/system/
sudo cp deploy/streamlit.service /etc/systemd/system/

# 重新加载 systemd
sudo systemctl daemon-reload

# 启用服务
sudo systemctl enable comment-tracker
sudo systemctl enable comment-tracker-ui
```

#### 6. 启动服务

```bash
# 启动后端
sudo systemctl start comment-tracker

# 启动前端
sudo systemctl start comment-tracker-ui

# 查看状态
sudo systemctl status comment-tracker
sudo systemctl status comment-tracker-ui
```

## 🔧 配置说明

### 环境变量 (.env)

```ini
# 调试模式
DEBUG=false

# 飞书 Webhook
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_HOOK_ID
FEISHU_SIGN_SECRET=YOUR_SECRET

# 服务配置
HOST=0.0.0.0
PORT=9000

# Streamlit 前端配置
API_BASE_URL=http://localhost:9000

# Cookie 配置
XHS_COOKIE=your_xhs_cookie_here
TIKTOK_COOKIE=your_tiktok_cookie_here

# 代理配置
PLAYWRIGHT_PROXY=socks5://callfans-sma:7778
```

### Service 文件说明

**后端服务 (comment-tracker.service):**
```ini
User=callfans
WorkingDirectory=/home/callfans/data/comment-tracker
ExecStart=/home/callfans/miniconda3/bin/conda run -n py312 python main.py
```

**前端服务 (streamlit.service):**
```ini
User=callfans
WorkingDirectory=/home/callfans/data/comment-tracker
Environment=API_BASE_URL=http://localhost:9000
ExecStart=/home/callfans/miniconda3/bin/conda run -n py312 streamlit run streamlit_app.py ...
```

## 📝 常用管理命令

### 服务管理

```bash
# 启动服务
sudo systemctl start comment-tracker
sudo systemctl start comment-tracker-ui

# 停止服务
sudo systemctl stop comment-tracker
sudo systemctl stop comment-tracker-ui

# 重启服务
sudo systemctl restart comment-tracker
sudo systemctl restart comment-tracker-ui

# 查看状态
sudo systemctl status comment-tracker
sudo systemctl status comment-tracker-ui

# 设置开机自启
sudo systemctl enable comment-tracker
sudo systemctl enable comment-tracker-ui

# 取消开机自启
sudo systemctl disable comment-tracker
sudo systemctl disable comment-tracker-ui
```

### 日志查看

```bash
# 查看后端日志
tail -f /home/callfans/data/comment-tracker/logs/service.log
tail -f /home/callfans/data/comment-tracker/logs/error.log

# 查看前端日志
tail -f /home/callfans/data/comment-tracker/logs/streamlit.log
tail -f /home/callfans/data/comment-tracker/logs/streamlit-error.log

# 使用 journalctl 查看
sudo journalctl -u comment-tracker -f
sudo journalctl -u comment-tracker-ui -f
```

### 故障排查

```bash
# 查看详细错误
sudo journalctl -u comment-tracker -n 50 --no-pager

# 手动测试运行
cd /home/callfans/data/comment-tracker
conda activate py312
python main.py

# 检查端口占用
sudo lsof -i :9000
sudo lsof -i :8501
```

## 🔄 更新部署

```bash
# 1. 停止服务
sudo systemctl stop comment-tracker
sudo systemctl stop comment-tracker-ui

# 2. 拉取最新代码
cd /home/callfans/data/comment-tracker
git pull

# 3. 更新依赖
conda activate py312
pip install -r requirements.txt
playwright install chromium

# 4. 重启服务
sudo systemctl start comment-tracker
sudo systemctl start comment-tracker-ui
```

## 📊 目录结构

```
/home/callfans/data/comment-tracker/
├── main.py                 # 后端入口
├── streamlit_app.py        # 前端入口
├── .env                    # 环境变量（权限 600）
├── requirements.txt        # Python 依赖
├── logs/                   # 日志目录
│   ├── service.log         # 后端日志
│   ├── error.log           # 后端错误日志
│   ├── streamlit.log       # 前端日志
│   └── streamlit-error.log # 前端错误日志
├── debug_data/             # 调试数据（DEBUG=true 时生成）
├── captured_data/          # 捕获数据
├── extractor/              # 数据提取模块
├── jobs/                   # 轮询任务
├── services/               # 通知服务
└── deploy/                 # 部署配置
    ├── comment-tracker.service
    ├── streamlit.service
    └── deploy_conda.sh
```

## 🔐 安全建议

1. **保护敏感信息**
   ```bash
   chmod 600 .env
   chown callfans:callfans .env
   ```

2. **定期备份**
   ```bash
   tar -czf /backup/comment-tracker-$(date +%Y%m%d).tar.gz \
       /home/callfans/data/comment-tracker/.env \
       /home/callfans/data/comment-tracker/captured_data
   ```

3. **监控资源使用**
   ```bash
   htop
   df -h
   ```

## ⚠️ 注意事项

1. **Conda 环境**: 确保 `py312` 环境存在且 Python 版本为 3.12
2. **用户权限**: 所有文件归属 `callfans` 用户
3. **端口配置**: 默认后端 9000，前端 8501，可在 `.env` 中修改
4. **代理配置**: TikTok 需要配置代理才能访问
5. **Cookie 有效期**: 定期检查并更新 Cookie

## 📞 技术支持

- API 文档: `http://localhost:9000/docs`
- 健康检查: `http://localhost:9000/health`
- 前端界面: `http://localhost:8501`
- 查看日志: `tail -f logs/service.log`

---

**部署完成后验证：**
- ✅ 后端服务正常运行
- ✅ 前端界面可访问
- ✅ API 接口响应正常
- ✅ 飞书通知发送成功
- ✅ 日志正常记录
