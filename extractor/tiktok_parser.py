"""
TikTok 视频评论监控解析模块。
从 TikTok 视频页面提取评论数量。
"""
import re
import os
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from playwright.async_api import BrowserContext
from loguru import logger

# 加载环境变量
load_dotenv()


class TikTokParser:
    """TikTok 视频页面解析器，用于提取评论数量信息。"""

    def __init__(self, browser_context: BrowserContext):
        self.browser_context = browser_context

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        从 TikTok 视频 URL 中提取视频 ID。

        Args:
            url: TikTok 视频 URL（例如：https://www.tiktok.com/@username/video/7610587901335833878）

        Returns:
            如果找到则返回视频 ID，否则返回 None
        """
        # 模式: /video/{video_id}
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)

        # 模式: /@{username}/video/{video_id}
        match = re.search(r'/@[\w.]+/video/(\d+)', url)
        if match:
            return match.group(1)

        logger.warning(f"无法从 URL 提取视频 ID: {url}")
        return None

    async def fetch_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        使用 Playwright 获取 TikTok 视频的互动数据。

        Args:
            url: TikTok 视频 URL

        Returns:
            包含视频互动数据的字典，失败则返回 None
        """
        page = None
        try:
            # 创建新页面
            page = await self.browser_context.new_page()

            logger.info(f"正在加载 TikTok 视频页面: {url}")
            response = await page.goto(url, timeout=30000)

            if response and response.status != 200:
                logger.error(f"获取页面失败: HTTP {response.status}")
                await page.close()
                return None

            # 等待页面完全加载
            await page.wait_for_timeout(20000)

            # 提取视频 ID
            video_id = self.extract_video_id(url)
            if not video_id:
                logger.error("无法提取视频 ID")
                await page.close()
                return None

            # 获取各互动数据（通过 data-e2e 属性定位 strong 标签）
            like_text = await self._get_interactive_count(page, 'like-count')
            comment_text = await self._get_interactive_count(page, 'comment-count')
            bookmark_text = await self._get_interactive_count(page, 'undefined-count')
            share_text = await self._get_interactive_count(page, 'share-count')

            # 获取视频描述和作者信息
            video_description = await self._get_video_description(page)
            author_name = await self._get_author_name(page)

            # 构建返回数据（保留原始文本）
            result = {
                'video_id': video_id,
                'video_url': url,
                'video_description': video_description or '未知描述',
                'author_name': author_name or '未知作者',
                'like_text': like_text or '0',
                'comment_text': comment_text or '0',
                'bookmark_text': bookmark_text or '0',
                'share_text': share_text or '0',
                'fetch_time': datetime.now().isoformat()
            }

            # 调试：保存数据到文件（仅在 DEBUG 模式下）
            if os.getenv('DEBUG', 'false').lower() == 'true':
                debug_dir = "debug_data"
                os.makedirs(debug_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_file = os.path.join(debug_dir, f"tiktok_video_{video_id}_{timestamp}.json")
                
                import json
                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                logger.info(f"视频数据已保存到: {debug_file}")

            logger.info(
                f"✓ 成功获取 TikTok 视频信息: "
                f"视频ID={video_id}, "
                f"评论={result['comment_text']}, "
                f"点赞={result['like_text']}, "
                f"收藏={result['bookmark_text']}, "
                f"分享={result['share_text']}"
            )

            await page.close()
            return result

        except Exception as e:
            logger.error(f"获取 TikTok 视频信息时出错: {e}", exc_info=True)
            if page:
                await page.close()
            return None

    async def _get_interactive_count(self, page, data_e2e: str) -> str:
        """
        根据 data-e2e 属性获取互动数据。
        
        Args:
            page: Playwright 页面对象
            data_e2e: data-e2e 属性值（如 'like-count', 'comment-count' 等）
        
        Returns:
            互动数据文本，如 "1.4M", "4252", "72.5K"
        """
        try:
            # 定位 strong 标签
            strong = await page.query_selector(f'strong[data-e2e="{data_e2e}"]')
            if strong:
                text = await strong.text_content()
                return text.strip() if text else '0'
            return '0'
        except Exception as e:
            logger.error(f"获取互动数据失败 (data-e2e={data_e2e}): {e}")
            return '0'

    async def _get_video_description(self, page) -> Optional[str]:
        """从页面中提取视频描述。"""
        try:
            # 查找视频描述元素
            desc_element = await page.query_selector('h2[data-e2e="video-desc"], div[data-e2e="video-desc"]')
            if desc_element:
                return await desc_element.text_content()

            # 尝试通过 CSS 类查找
            desc_element = await page.query_selector('span[data-e2e="video-desc"]')
            if desc_element:
                return await desc_element.text_content()

            return None

        except Exception as e:
            logger.error(f"提取视频描述时出错: {e}")
            return None

    async def _get_author_name(self, page) -> Optional[str]:
        """从页面中提取作者名称。"""
        try:
            # 查找作者名称元素
            author_element = await page.query_selector('h3[data-e2e="video-author"], a[data-e2e="video-author"]')
            if author_element:
                return await author_element.text_content()

            # 尝试通过 URL 提取作者名
            url = page.url
            match = re.search(r'tiktok\.com/@([^/]+)', url)
            if match:
                return match.group(1)

            return None

        except Exception as e:
            logger.error(f"提取作者名称时出错: {e}")
            return None
