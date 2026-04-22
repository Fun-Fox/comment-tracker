"""
TikTok 评论接口数据捕获工具
打开视频页面，点击评论按钮，滚动到评论区，监控并捕获评论列表接口的响应数据
"""
import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright, BrowserContext, Page
from loguru import logger
from typing import Optional, List, Dict, Any

# 加载 .env 文件
load_dotenv()


class TikTokCommentMonitor:
    """TikTok 评论接口监控器"""

    def __init__(self, headless: bool = False, cookie_file: Optional[str] = None):
        """
        初始化监控器
        
        Args:
            headless: 是否使用无头模式
            cookie_file: Cookie 文件路径（JSON 格式）
        """
        self.headless = headless
        self.cookie_file = cookie_file
        self.captured_comments: List[Dict[str, Any]] = []
        self.comment_api_responses: List[Dict[str, Any]] = []

    async def setup_browser(self) -> BrowserContext:
        """设置浏览器并加载 Cookie 和代理配置"""
        self.playwright = await async_playwright().start()
        
        # 准备浏览器启动参数
        launch_args = {
            'headless': self.headless
        }
        
        # 准备浏览器上下文参数
        context_args = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'viewport': {'width': 1920, 'height': 1080}
        }
        
        # 从 .env 读取代理配置
        proxy_url = os.getenv('PLAYWRIGHT_PROXY')
        if proxy_url:
            logger.info(f"使用代理: {proxy_url}")
            context_args['proxy'] = {'server': proxy_url}
        else:
            logger.info("未配置代理，将使用直连")
        
        # 启动浏览器
        self.browser = await self.playwright.chromium.launch(**launch_args)
        context = await self.browser.new_context(**context_args)

        # 加载 Cookie
        if self.cookie_file and os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                logger.info(f"已加载 Cookie: {self.cookie_file}")
            except Exception as e:
                logger.warning(f"加载 Cookie 失败: {e}")
        
        # 加载 TikTok Cookie 从环境变量
        tiktok_cookie = os.getenv('TIKTOK_COOKIE')
        if tiktok_cookie:
            try:
                # 如果是字符串格式，转换为 JSON
                if tiktok_cookie.startswith('['):
                    cookies = json.loads(tiktok_cookie)
                else:
                    # 字符串格式转换为 JSON
                    from utils.convert_cookie import convert_cookie_string_to_json
                    cookies = json.loads(convert_cookie_string_to_json(tiktok_cookie, ".tiktok.com"))
                
                await context.add_cookies(cookies)
                logger.info("已从环境变量加载 TikTok Cookie")
            except Exception as e:
                logger.warning(f"加载 TikTok Cookie 失败: {e}")

        return context

    async def monitor_comment_api(self, page: Page):
        """
        监控评论列表 API 请求
        
        Args:
            page: Playwright 页面对象
        """
        async def handle_response(response):
            url = response.url
            # 匹配评论列表接口
            if '/api/comment/list/' in url:
                try:
                    # 获取响应数据
                    body = await response.body()
                    json_data = json.loads(body)
                    
                    # 记录接口信息
                    api_info = {
                        'url': url,
                        'status': response.status,
                        'timestamp': datetime.now().isoformat(),
                        'data': json_data
                    }
                    self.comment_api_responses.append(api_info)
                    
                    logger.info(f"✓ 捕获到评论列表接口响应")
                    logger.info(f"  URL: {url[:100]}...")
                    
                    # 提取评论数据
                    if 'comments' in json_data:
                        comments = json_data['comments']
                        self.captured_comments.extend(comments)
                        logger.info(f"  获取到 {len(comments)} 条评论")
                    
                except Exception as e:
                    logger.error(f"处理评论接口响应失败: {e}")

        # 注册响应监听器
        page.on('response', handle_response)
        logger.info("已启动评论接口监控")

    async def click_comment_and_scroll(self, page: Page):
        """
        点击评论按钮并滚动到评论区
        
        Args:
            page: Playwright 页面对象
        """
        try:
            # 等待页面加载
            await page.wait_for_timeout(3000)
            
            # 点击评论按钮 - 使用 data-testid 定位
            comment_button_selectors = [
                'button[data-testid="tux-web-tab-bar"]',  # 评论按钮
                'button:has-text("评论")',  # 包含"评论"文本的按钮
                'button:has-text("Comments")',  # 英文版本
                '[data-e2e="comment-icon"]',
                '[data-e2e="comment-level-1"]',
            ]
            
            clicked = False
            for selector in comment_button_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        await button.click()
                        logger.info(f"已点击评论按钮: {selector}")
                        clicked = True
                        await page.wait_for_timeout(3000)
                        break
                except Exception as e:
                    logger.debug(f"尝试选择器 {selector} 失败: {e}")
                    continue
            
            if not clicked:
                logger.warning("未找到评论按钮，尝试直接查找评论区域")
            
            # 等待评论区域加载
            await page.wait_for_timeout(2000)
            
            # 定位评论区域容器并滚动
            comment_container_selectors = [
                'div[class*="RightPanelContainer"]',  # 右侧面板容器
                '[data-e2e="comment-list"]',
                'div[class*="comment-list"]',
            ]
            
            scrolled = False
            for selector in comment_container_selectors:
                try:
                    container = await page.query_selector(selector)
                    if container:
                        await container.scroll_into_view_if_needed()
                        logger.info(f"已滚动到评论区域: {selector}")
                        scrolled = True
                        break
                except Exception as e:
                    logger.debug(f"尝试滚动选择器 {selector} 失败: {e}")
                    continue
            
            if not scrolled:
                # 如果找不到特定容器，尝试滚动整个页面
                await page.evaluate('window.scrollBy(0, window.innerHeight)')
                logger.info("已向下滚动页面")
            
            await page.wait_for_timeout(2000)
            
            # 多次滚动以加载更多评论
            for i in range(5):
                await page.evaluate('window.scrollBy(0, 400)')
                await page.wait_for_timeout(1500)
                logger.info(f"滚动加载更多评论 ({i+1}/5)")
                
                # 检查是否有新评论加载（可选）
                new_comments_count = len(self.captured_comments)
                if new_comments_count > 0:
                    logger.info(f"当前已捕获 {new_comments_count} 条评论")
            
        except Exception as e:
            logger.error(f"点击评论和滚动失败: {e}")

    async def capture_comments(self, video_url: str, output_dir: str = "captured_data", max_retries: int = 2) -> Optional[str]:
        """
        捕获指定视频的评论数据
        
        Args:
            video_url: TikTok 视频 URL
            output_dir: 输出目录
            max_retries: 最大重试次数
            
        Returns:
            输出文件路径
        """
        page = None
        
        # 清理 URL（移除连续的点）
        import re
        video_url = re.sub(r'@([\w.]+)', lambda m: '@' + re.sub(r'\.+', '.', m.group(1)), video_url)
        logger.info(f"清理后的 URL: {video_url}")
        
        for attempt in range(max_retries + 1):
            try:
                # 设置浏览器
                context = await self.setup_browser()
                page = await context.new_page()
                
                # 启动接口监控
                await self.monitor_comment_api(page)
                
                # 访问视频页面
                logger.info(f"正在访问视频 (尝试 {attempt + 1}/{max_retries + 1}): {video_url}")
                await page.goto(video_url, timeout=60000, wait_until='domcontentloaded')
                
                # 等待页面加载
                await page.wait_for_timeout(20000)
                
                # 点击评论并滚动
                await self.click_comment_and_scroll(page)
                
                # 等待接口请求完成
                await page.wait_for_timeout(5000)
                
                # 保存数据
                os.makedirs(output_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # 提取视频 ID
                video_id_match = re.search(r'/video/(\d+)', video_url)
                video_id = video_id_match.group(1) if video_id_match else 'unknown'
                
                # 保存原始 API 响应
                api_output_file = os.path.join(output_dir, f"tiktok_comments_api_{video_id}_{timestamp}.json")
                with open(api_output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'video_url': video_url,
                        'video_id': video_id,
                        'capture_time': timestamp,
                        'total_api_calls': len(self.comment_api_responses),
                        'total_comments': len(self.captured_comments),
                        'api_responses': self.comment_api_responses
                    }, f, ensure_ascii=False, indent=2)
                logger.info(f"API 响应已保存到: {api_output_file}")
                
                # 保存纯评论数据
                comments_output_file = os.path.join(output_dir, f"tiktok_comments_{video_id}_{timestamp}.json")
                with open(comments_output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'video_url': video_url,
                        'video_id': video_id,
                        'capture_time': timestamp,
                        'total_comments': len(self.captured_comments),
                        'comments': self.captured_comments
                    }, f, ensure_ascii=False, indent=2)
                logger.info(f"评论数据已保存到: {comments_output_file}")
                
                # 正确顺序关闭资源
                await page.close()
                await context.close()
                await self.browser.close()
                await self.playwright.stop()
                return comments_output_file
                
            except Exception as e:
                logger.error(f"捕获评论失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                if attempt < max_retries:
                    logger.info(f"等待 3 秒后重试...")
                    await asyncio.sleep(3)
                else:
                    logger.error(f"已达到最大重试次数，放弃")
            finally:
                # 正确顺序关闭资源
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass
                if 'context' in locals() and context:
                    try:
                        await context.close()
                    except Exception:
                        pass
                if hasattr(self, 'browser') and self.browser:
                    try:
                        await self.browser.close()
                    except Exception:
                        pass
                if hasattr(self, 'playwright') and self.playwright:
                    try:
                        await self.playwright.stop()
                    except Exception:
                        pass
        
        return None


async def main():
    """主函数"""
    # 配置
    VIDEO_URL = "https://www.tiktok.com/@new..art4/video/7613411270804491550"  # URL 清理会自动处理多余的点
    COOKIE_FILE = None  # 如果需要登录，设置 Cookie 文件路径，例如: "tiktok_cookies.json"
    # 也可以从 .env 读取：COOKIE_FILE = os.getenv('TIKTOK_COOKIE_FILE')
    
    # 创建监控器
    monitor = TikTokCommentMonitor(
        headless=False,  # 设置为 False 可以看到浏览器操作
        cookie_file=COOKIE_FILE
    )
    
    # 捕获评论
    output_file = await monitor.capture_comments(VIDEO_URL)
    
    if output_file:
        logger.info(f"\n✓ 完成！评论数据已保存到: {output_file}")
    else:
        logger.error(" 捕获失败")


if __name__ == "__main__":
    asyncio.run(main())
