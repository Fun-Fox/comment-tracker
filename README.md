# 📱 Comment Tracker - 社媒评论监控服务

> 实时监测小红书和 TikTok 帖子/视频的评论变化，自动发送飞书通知

## ✨ 功能特性

- **📕 小红书监控**: 自动检测笔记评论变化，实时推送通知
- **🎵 TikTok 监控**: 监控视频互动数据（评论、点赞、收藏、分享）
- **🔔 飞书通知**: 精美的消息卡片推送，支持签名校验
- **🌐 Web 管理界面**: 基于 Streamlit 的可视化操作面板
- **🔌 RESTful API**: 完整的 API 接口，支持自动化集成
- **🔄 轮询任务**: 可配置的轮询间隔和时长，支持自动重试
- **🍪 Cookie 管理**: 支持动态设置和切换多平台 Cookie
- **🕷️ 反检测**: 随机浏览器指纹 + 反自动化检测脚本

## 🏗️ 项目结构

```
comment-tracker/
├── main.py                     # FastAPI 后端服务主入口
├── streamlit_app.py            # Streamlit Web 管理界面
├── .env                        # 环境变量配置
├── requirements.txt            # Python 依赖
├── pyproject.toml              # 项目配置
│
├── extractor/                  # 📦 平台数据提取器（原 parsers）
│   ├── tiktok_parser.py        # TikTok 视频数据提取
│   └── xhs_parser.py           # 小红书笔记数据提取
│
├── jobs/                       # 📦 轮询任务管理
│   ├── job_manager.py          # 任务管理器
│   ├── tiktok_polling_job.py   # TikTok 轮询任务
│   └── xhs_polling_job.py      # 小红书轮询任务
│
├── services/                   # 📦 服务层
│   └── notification_service.py # 飞书通知服务
│
├── utils/                      # 📦 工具函数
│   └── convert_cookie.py       # Cookie 格式转换工具
│
├── test/                       # 📦 测试工具
│   └── capture_tiktok_comments.py  # TikTok 评论数据捕获工具
│
├── debug_data/                 # 调试数据（自动创建）
└── doc/                        # 文档截图
```

## 📦 模块重命名建议

当前 `parsers/` 目录下的模块命名建议优化为更准确的描述：

### 建议 1: 按功能命名（推荐）
```
parsers/
├── tiktok_scraper.py           # TikTok 数据采集器
└── xhs_scraper.py              # 小红书数据采集器
```

### 建议 2: 按平台+功能命名
```
parsers/
├── tiktok_extractor.py         # TikTok 数据提取器
└── xhs_extractor.py            # 小红书数据提取器
```

### 建议 3: 保持原样
- `tiktok_parser.py` - 语义清晰，无需修改
- `xhs_parser.py` - 语义清晰，无需修改

**推荐使用方案 1**，因为模块主要功能是使用 Playwright 抓取数据，`scraper` 比 `parser` 更准确。

## 🚀 快速开始

### 1. 环境要求

- Python >= 3.12
- Playwright（自动安装）

### 2. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`（如有），或直接编辑 `.env`：

```ini
# 飞书 Webhook 配置
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_HOOK_ID
FEISHU_SIGN_SECRET=YOUR_SIGN_SECRET

# 服务配置
HOST=0.0.0.0
PORT=8000

# 小红书轮询配置（分钟）
XHS_POLL_INTERVAL_MINUTES=1
XHS_POLL_DURATION_MINUTES=60
XHS_MAX_RETRIES=3

# TikTok 轮询配置（分钟）
TIKTOK_POLL_INTERVAL_MINUTES=1
TIKTOK_POLL_DURATION_MINUTES=60
TIKTOK_MAX_RETRIES=3

# 小红书 Cookie（JSON 数组或字符串格式）
XHS_COOKIE=your_cookie_here

# TikTok Cookie（JSON 数组或字符串格式）
TIKTOK_COOKIE=your_cookie_here

# 代理配置（可选）
PLAYWRIGHT_PROXY=http://127.0.0.1:10405
```

### 4. 启动服务

#### 方式 1: 启动后端 API 服务

```bash
python main.py
```

访问 `http://localhost:8000/docs` 查看 API 文档

#### 方式 2: 启动 Web 管理界面（需要先启动后端）

```bash
streamlit run streamlit_app.py
```

访问 `http://localhost:8501` 使用可视化界面

## 📖 API 文档

### 核心接口

#### 1. 提交监控任务

```bash
POST /api/v1/posts/monitor
Content-Type: application/json

{
  "url": "https://www.xiaohongshu.com/explore/xxx"
}
```

支持小红书和 TikTok URL，自动识别平台。

#### 2. 查询任务状态

```bash
GET /api/v1/jobs/{job_id}
```

#### 3. 列出所有任务

```bash
GET /api/v1/jobs
```

#### 4. 取消任务

```bash
DELETE /api/v1/jobs/{job_id}
```

#### 5. 设置 Cookie

```bash
POST /api/v1/cookies
Content-Type: application/json

{
  "cookies": "[{\"name\": \"cookie1\", \"value\": \"value1\", \"domain\": \".xiaohongshu.com\", \"path\": \"/\"}]"
}
```

自动识别平台（根据 domain 判断）。

#### 6. 健康检查

```bash
GET /health
```

## 🔧 独立工具

### TikTok 评论数据捕获

使用 Playwright 自动捕获 TikTok 评论 API 数据：

```bash
python test/capture_tiktok_comments.py
```

功能：
- ✅ 自动打开浏览器
- ✅ 点击评论按钮并滚动加载
- ✅ 监控 `/api/comment/list/` 接口
- ✅ 保存原始 API 响应到 JSON

输出：
- `captured_data/tiktok_comments_api_{video_id}_{timestamp}.json` - API 原始响应
- `captured_data/tiktok_comments_{video_id}_{timestamp}.json` - 纯评论数据

### Cookie 格式转换

将字符串格式的 Cookie 转换为 JSON 格式：

```bash
python utils/convert_cookie.py
```

## 🎯 工作流程

### 监控任务流程

```
1. 提交 URL → POST /api/v1/posts/monitor
        ↓
2. 创建 Job ID，启动异步轮询任务
        ↓
3. 等待轮询间隔（如 1 分钟）
        ↓
4. 使用 Playwright 访问页面
        ↓
5. 提取评论数据（Parser）
        ↓
6. 检测评论变化
        ├─ 有变化 → 发送飞书通知 → 任务完成
        └─ 无变化 → 继续轮询 → 达到最大次数 → 任务完成
```

### 数据解析流程

**小红书 (XHS):**
- 访问笔记页面
- 执行 JavaScript 获取 `window.__INITIAL_STATE__.note.noteDetailMap[note_id]`
- 解析笔记信息（标题、作者、互动数据）
- 提取评论列表（过滤作者评论）

**TikTok:**
- 访问视频页面
- 等待页面加载
- 通过 `data-e2e` 属性定位互动数据（评论、点赞、收藏、分享）
- 提取视频描述和作者信息

## 🔐 Cookie 配置

### 方式 1: 环境变量（推荐）

在 `.env` 中配置：

```ini
# JSON 数组格式
XHS_COOKIE=[{"name": "web_session", "value": "xxx", "domain": ".xiaohongshu.com", "path": "/"}]

# 或字符串格式（自动转换）
TIKTOK_COOKIE=session_id=xxx; csrftoken=yyy;
```

### 方式 2: Web 界面

在 Streamlit 管理界面动态设置：

```
📕 小红书 → Cookie 设置 → 输入 JSON → 保存
🎵 TikTok → Cookie 设置 → 输入 JSON → 保存
```

### 方式 3: API 接口

```bash
curl -X POST http://localhost:8000/api/v1/cookies \
  -H "Content-Type: application/json" \
  -d '{"cookies": "[{\"name\": \"web_session\", \"value\": \"xxx\", \"domain\": \".xiaohongshu.com\", \"path\": \"/\"}]"}'
```

## 🛡️ 反检测策略

项目内置多层反检测机制：

1. **随机浏览器指纹**
   - 随机 User-Agent（Chrome 119-120）
   - 随机屏幕尺寸
   - 模拟真实浏览器环境

2. **隐藏自动化特征**
   - 移除 `webdriver` 标志
   - 伪装 `chrome.runtime`
   - 伪装 `navigator.plugins`
   - 伪装 `navigator.languages`

3. **反检测脚本**
   - 注入 JavaScript 覆盖自动化特征
   - 模拟真实用户行为

4. **代理支持**
   - 配置代理避免 IP 封禁
   - 支持 HTTP/SOCKS5 代理

## 📊 监控配置

### 轮询参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `POLL_INTERVAL_MINUTES` | 1 | 轮询间隔（分钟） |
| `POLL_DURATION_MINUTES` | 60 | 监控总时长（分钟） |
| `MAX_RETRIES` | 3 | 失败重试次数 |

### 计算示例

```
间隔 = 1 分钟
总时长 = 60 分钟
最大轮询次数 = 60 / 1 = 60 次
```

##  日志

使用 `loguru` 记录日志，输出到控制台。日志级别：

- `INFO` - 正常操作流程
- `WARNING` - 警告信息（如未找到数据）
- `ERROR` - 错误信息（如网络失败）

调试数据保存在 `debug_data/` 目录。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [Playwright](https://playwright.dev/) - 浏览器自动化
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [Streamlit](https://streamlit.io/) - Web 界面
- [飞书开放平台](https://open.feishu.cn/) - 消息推送

---

**📱 Comment Tracker** - 让社媒监控更简单
