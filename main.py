"""
小红书评论轮询任务服务

一个基于FastAPI的服务，用于监控小红书帖子的新评论。
当通过API提交帖子URL时，它会启动一个轮询任务，
检查评论并在检测到时发送通知。
"""
import os
import json
from contextlib import asynccontextmanager
from typing import List
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from aiohttp import ClientSession
from playwright.async_api import async_playwright, BrowserContext
from loguru import logger

from jobs.job_manager import JobManager
from services.notification_service import FeishuNotificationService


# 全局实例
aiohttp_session: ClientSession = None
notification_service: FeishuNotificationService = None
job_manager: JobManager = None
browser_context: BrowserContext = None
browser = None
# templates = None

# Cookie 管理
xhs_cookies = []

def get_xhs_cookie_from_env() -> list:
    """从环境变量读取 Cookie"""
    cookie_str = os.getenv('XHS_COOKIE', '')
    if not cookie_str:
        return []
    try:
        return json.loads(cookie_str)
    except:
        logger.error("XHS_COOKIE 格式错误，应该是 JSON 数组")
        return []

def set_xhs_cookies(cookies: list):
    """设置全局 Cookie"""
    global xhs_cookies
    xhs_cookies = cookies
    # 更新环境变量
    os.environ['XHS_COOKIE'] = json.dumps(cookies)
    logger.info(f"已更新 XHS Cookie，共 {len(cookies)} 个")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用程序生命周期 - 初始化和清理。"""
    global aiohttp_session, notification_service, job_manager, browser, browser_context, xhs_cookies

    # 启动
    logger.info("正在启动小红书评论轮询服务...")
    
    # 从环境变量加载 Cookie
    xhs_cookies = get_xhs_cookie_from_env()
    if xhs_cookies:
        logger.info(f"已加载 {len(xhs_cookies)} 个 XHS Cookie")
    
    # 初始化Playwright浏览器 - 使用随机指纹
    playwright = await async_playwright().start()
    
    # 随机浏览器指纹配置
    import random
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    screen_sizes = [
        {'width': 1920, 'height': 1080},
        {'width': 1536, 'height': 864},
        {'width': 1366, 'height': 768},
        {'width': 1440, 'height': 900},
    ]
    
    selected_ua = random.choice(user_agents)
    selected_screen = random.choice(screen_sizes)
    
    logger.info(f"使用随机指纹 - UA: {selected_ua[:50]}... 屏幕: {selected_screen['width']}x{selected_screen['height']}")
    
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--window-size={},{}'.format(selected_screen['width'], selected_screen['height']),
            '--disable-features=IsolateOrigins,site-per-process',
        ],
        ignore_default_args=['--enable-automation'],
    )
    
    # 创建带有随机指纹的浏览器上下文
    context_options = {
        'user_agent': selected_ua,
        'viewport': {'width': selected_screen['width'], 'height': selected_screen['height']},
        'locale': 'zh-CN',
        'timezone_id': 'Asia/Shanghai',
        'extra_http_headers': {
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        },
    }
    
    # 如果有 cookie，添加进去
    if xhs_cookies:
        context_options['storage_state'] = {'cookies': xhs_cookies}
    
    browser_context = await browser.new_context(**context_options)
    
    # 更强的反检测脚本
    await browser_context.add_init_script("""
        // 隐藏 webdriver 特征
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        
        // 伪装 chrome 对象
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        
        // 伪装 plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                {name: 'Native Client', filename: 'internal-nacl-plugin'}
            ]
        });
        
        // 伪装 languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en']
        });
        
        // 伪装 permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // 伪装 screen
        Object.defineProperty(screen, 'availWidth', {get: () => 1920});
        Object.defineProperty(screen, 'availHeight', {get: () => 1080});
        
        // 移除 automation 痕迹
        delete navigator.__proto__.webdriver;
    """)
    
    logger.info("✓ Playwright浏览器启动成功（随机指纹 + 反检测）")

    aiohttp_session = ClientSession()
    notification_service = FeishuNotificationService(aiohttp_session)
    job_manager = JobManager(browser_context, notification_service)
    
    # 初始化模板引擎
    # templates = Jinja2Templates(directory="templates")
    
    logger.info("服务启动成功")

    yield

    # 关闭
    logger.info("正在关闭小红书评论轮询服务...")
    if browser_context:
        await browser_context.close()
    if aiohttp_session:
        await aiohttp_session.close()
    logger.info("服务关闭完成")


# 创建FastAPI应用
app = FastAPI(
    title="小红书评论轮询服务",
    description="监控小红书帖子的新评论并发送通知",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求/响应模型
class SubmitPostRequest(BaseModel):
    """提交小红书帖子URL的请求模型。"""
    url: str


class SubmitPostResponse(BaseModel):
    """提交帖子URL后的响应模型。"""
    job_id: str
    message: str
    url: str


class JobStatusResponse(BaseModel):
    """任务状态的响应模型。"""
    job_id: str
    url: str
    status: str
    created_at: str
    last_poll_time: str | None = None
    poll_count: int
    max_polls: int
    previous_comment_count: int


class HealthResponse(BaseModel):
    """健康检查响应。"""
    status: str
    active_jobs: int
    total_jobs: int


# API端点
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点。"""
    return HealthResponse(
        status="healthy",
        active_jobs=job_manager.get_active_job_count(),
        total_jobs=job_manager.get_total_job_count()
    )


@app.post("/api/v1/posts/monitor", response_model=SubmitPostResponse)
async def submit_post(request: SubmitPostRequest):
    """
    提交小红书帖子URL进行评论监控。

    Args:
        request: 包含小红书帖子URL

    Returns:
        用于跟踪监控任务的Job ID
    """
    try:
        # 验证URL包含小红书域名
        if 'xiaohongshu.com' not in request.url:
            raise HTTPException(
                status_code=400,
                detail="无效的URL。必须是有效的小红书帖子URL"
            )

        # 创建轮询任务
        job_id = await job_manager.create_job(request.url)

        logger.info(f"提交了新的监控任务 {job_id}，URL: {request.url}")

        return SubmitPostResponse(
            job_id=job_id,
            message="监控任务创建成功。",
            url=request.url
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建监控任务时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@app.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    获取特定监控任务的状态。

    Args:
        job_id: 提交帖子时返回的任务ID

    Returns:
        当前任务状态信息
    """
    status = job_manager.get_job_status(job_id)

    if not status:
        raise HTTPException(status_code=404, detail="未找到任务")

    return JobStatusResponse(**status)


@app.get("/api/v1/jobs", response_model=List[JobStatusResponse])
async def list_jobs():
    """
    列出所有监控任务及其状态。

    Returns:
        所有任务的列表
    """
    return job_manager.list_jobs()


@app.delete("/api/v1/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    取消正在运行的监控任务。

    Args:
        job_id: 要取消的任务ID

    Returns:
        成功消息
    """
    success = await job_manager.cancel_job(job_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail="任务未找到或已完成/已取消"
        )

    return {"message": f"任务 {job_id} 已成功取消"}


@app.post("/api/v1/test/notification")
async def test_notification():
    """
    发送测试通知以验证通知服务是否正常工作。

    Returns:
        成功/失败状态
    """
    success = await notification_service.send_test_notification()

    if not success:
        raise HTTPException(
            status_code=500,
            detail="发送测试通知失败。请检查FEISHU_WEBHOOK_URL和FEISHU_SIGN_SECRET配置。"
        )

    return {"message": "测试通知发送成功"}


# @app.get("/")
# async def admin_page(request: Request):
#     """管理页面。"""
#     return templates.TemplateResponse(
#         "admin.html",
#         {
#             "request": request,
#             "cookies": xhs_cookies,
#             "cookie_count": len(xhs_cookies)
#         }
#     )


class CookieRequest(BaseModel):
    """Cookie 设置请求。"""
    cookies: str  # JSON 字符串


@app.post("/api/v1/cookies")
async def set_cookies(request_data: CookieRequest):
    """
    设置小红书 Cookie。
    
    Args:
        request_data: 包含 cookies JSON 字符串
    
    Returns:
        设置结果
    """
    try:
        cookies = json.loads(request_data.cookies)
        if not isinstance(cookies, list):
            raise HTTPException(status_code=400, detail="Cookie 必须是 JSON 数组")
        
        set_xhs_cookies(cookies)
        
        return {
            "message": f"成功设置 {len(cookies)} 个 Cookie",
            "count": len(cookies)
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Cookie 格式错误，必须是有效的 JSON")


@app.get("/api/v1/cookies")
async def get_cookies():
    """
    获取当前 Cookie。
    
    Returns:
        当前 Cookie 列表
    """
    return {
        "cookies": xhs_cookies,
        "count": len(xhs_cookies)
    }


@app.delete("/api/v1/cookies")
async def clear_cookies():
    """
    清除所有 Cookie。
    
    Returns:
        清除结果
    """
    set_xhs_cookies([])
    return {"message": "已清除所有 Cookie", "count": 0}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8000'))

    logger.info(f"在 {host}:{port} 上启动服务器")
    uvicorn.run(app, host=host, port=port)