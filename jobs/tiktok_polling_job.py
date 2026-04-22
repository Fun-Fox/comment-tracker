"""
TikTok 视频评论监控的轮询任务管理器。
管理检查 TikTok 视频评论数量变化的轮询任务。
"""
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from playwright.async_api import BrowserContext
from loguru import logger

from extractor.tiktok_parser import TikTokParser
from services.notification_service import FeishuNotificationService


class TikTokPollingJob:
    """
    代表单个 TikTok 视频的评论轮询任务。

    在配置的时长内轮询 TikTok 视频页面以检测评论数量变化。
    如果检测到新评论，则发送通知并停止。
    """

    def __init__(
        self,
        job_id: str,
        url: str,
        browser_context: BrowserContext,
        notification_service: FeishuNotificationService
    ):
        self.job_id = job_id
        self.url = url
        self.browser_context = browser_context
        self.notification_service = notification_service
        self.parser = TikTokParser(browser_context)

        # 任务状态
        self.status = 'pending'  # pending(待处理), running(运行中), completed(已完成), failed(失败)
        self.created_at = datetime.now()
        self.last_poll_time = None
        self.poll_count = 0
        self.previous_comment_text = '0'
        self.retry_count = 0  # 当前重试次数
        self.max_retries = 0  # 最大重试次数
        
        # 从环境变量读取轮询配置
        self.poll_interval_minutes = int(os.getenv('TIKTOK_POLL_INTERVAL_MINUTES', '30'))
        self.poll_duration_minutes = int(os.getenv('TIKTOK_POLL_DURATION_MINUTES', '60'))
        self.max_retries = int(os.getenv('TIKTOK_MAX_RETRIES', '3'))  # 最大重试次数
        
        # 计算最大轮询次数
        self.max_polls = self.poll_duration_minutes // self.poll_interval_minutes
        if self.max_polls < 1:
            self.max_polls = 1
        
        logger.info(f"为 TikTok 视频创建轮询任务 {job_id}: {url}，间隔: {self.poll_interval_minutes}分钟，总时长: {self.poll_duration_minutes}分钟，最多轮询: {self.max_polls}次")

    async def run(self):
        """
        执行 TikTok 评论轮询任务。
        根据配置的间隔时间和总时长进行轮询。
        """
        try:
            self.status = 'running'
            logger.info(f"开始 TikTok 评论轮询任务 {self.job_id}，间隔: {self.poll_interval_minutes}分钟，总时长: {self.poll_duration_minutes}分钟，最大重试: {self.max_retries}次")

            # 根据总时长和间隔动态轮询
            for i in range(self.max_polls):
                # 等待间隔时间
                wait_time = self.poll_interval_minutes * 60
                logger.info(f"任务 {self.job_id}: 等待 {wait_time}秒后进行第 {i+1} 次 TikTok 评论轮询")
                await asyncio.sleep(wait_time)

                # 执行轮询（带重试机制）
                success = await self._perform_poll_with_retry()

                # 如果检测到评论变化，提前结束
                if self.status == 'completed':
                    logger.info(f"TikTok 任务 {self.job_id} 在第 {i+1} 次轮询后完成（检测到新评论）")
                    return

            logger.info(f"TikTok 任务 {self.job_id} 完成所有轮询（共{self.max_polls}次）")

        except Exception as e:
            self.status = 'failed'
            logger.error(f"TikTok 轮询任务 {self.job_id} 失败: {e}", exc_info=True)

    async def _perform_poll_with_retry(self) -> bool:
        """
        执行带重试机制的轮询。
        
        Returns:
            bool: 轮询是否成功
        """
        for attempt in range(self.max_retries + 1):  # 原始1次 + 重试N次
            try:
                await self._perform_poll()
                return True  # 成功，退出重试
            except Exception as e:
                self.retry_count += 1
                if attempt < self.max_retries:
                    # 还有重试次数
                    retry_wait = (attempt + 1) * 10  # 递增重试等待时间（10秒、20秒、30秒）
                    logger.warning(
                        f"TikTok 任务 {self.job_id}: 第 #{self.poll_count} 次轮询失败（尝试 {attempt + 1}/{self.max_retries + 1}）: {e}"
                        f"\n将在 {retry_wait}秒后重试..."
                    )
                    await asyncio.sleep(retry_wait)
                else:
                    # 已用完所有重试次数
                    logger.error(
                        f"TikTok 任务 {self.job_id}: 第 #{self.poll_count} 次轮询彻底失败，已达最大重试次数 {self.max_retries}",
                        exc_info=True
                    )
                    return False
        return False

    async def _perform_poll(self):
        """
        执行单次 TikTok 评论轮询：获取页面、解析评论数、检查变化。
        """
        try:
            self.poll_count += 1
            self.last_poll_time = datetime.now()

            logger.info(
                f"TikTok 任务 {self.job_id}: 执行第 #{self.poll_count} 次轮询"
            )

            # 获取并解析视频信息（包含互动数据）
            video_data = await self.parser.fetch_video_info(self.url)

            if not video_data:
                logger.warning(
                    f"TikTok 任务 {self.job_id}: 第 #{self.poll_count} 次轮询时获取视频数据失败"
                )
                return

            current_comment_text = video_data['comment_text']
            current_like_text = video_data.get('like_text', '0')
            current_bookmark_text = video_data.get('bookmark_text', '0')
            current_share_text = video_data.get('share_text', '0')
            video_description = video_data.get('video_description', '未知描述')
            author_name = video_data.get('author_name', '未知作者')

            logger.info(
                f"TikTok 任务 {self.job_id}: 第 #{self.poll_count} 次轮询 - "
                f"作者: {author_name}, "
                f"描述: {video_description[:50]}..., "
                f"评论: {current_comment_text}, "
                f"点赞: {current_like_text}, "
                f"收藏: {current_bookmark_text}, "
                f"分享: {current_share_text}"
            )

            # 检查评论文本是否有变化（简单的字符串比较）
            if current_comment_text != '0' and current_comment_text != self.previous_comment_text:
                # 检测到评论数变化！发送通知
                logger.info(
                    f"TikTok 任务 {self.job_id}: 检测到评论数变化！"
                    f"当前: {current_comment_text}, 上次: {self.previous_comment_text}. "
                    f"正在发送飞书通知..."
                )

                notification_sent = await self.notification_service.send_tiktok_notification(
                    video_id=video_data['video_id'],
                    video_url=self.url,
                    video_description=video_description,
                    author_name=author_name,
                    comment_text=current_comment_text,
                    like_text=current_like_text,
                    bookmark_text=current_bookmark_text,
                    share_text=current_share_text
                )

                if notification_sent:
                    logger.info(f"TikTok 任务 {self.job_id}: 飞书通知发送成功")
                else:
                    logger.error(f"TikTok 任务 {self.job_id}: 飞书通知发送失败")

                # 标记任务为已完成 - 无需继续轮询
                self.status = 'completed'
                return
            else:
                # 评论数没有变化
                if current_comment_text == '0':
                    logger.info(
                        f"TikTok 任务 {self.job_id}: 暂未找到评论数据. "
                        f"当前: {current_comment_text}"
                    )
                else:
                    logger.info(
                        f"TikTok 任务 {self.job_id}: 评论数未变化. "
                        f"当前: {current_comment_text}"
                    )
                self.previous_comment_text = current_comment_text

                # 如果是最后一次轮询，标记为已完成
                if self.poll_count >= self.max_polls:
                    self.status = 'completed'
                    logger.info(
                        f"TikTok 任务 {self.job_id}: 所有轮询已完成. "
                        f"监控期间评论数从 {self.previous_comment_text} 未变化."
                    )

        except Exception as e:
            logger.error(
                f"TikTok 任务 {self.job_id}: 第 #{self.poll_count} 次轮询时出错: {e}",
                exc_info=True
            )
            # 将异常向上抛出，交由 _perform_poll_with_retry 处理
            raise

    def get_status(self) -> Dict[str, Any]:
        """获取当前 TikTok 任务状态信息。"""
        return {
            'job_id': self.job_id,
            'platform': 'tiktok',
            'url': self.url,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'last_poll_time': self.last_poll_time.isoformat() if self.last_poll_time else None,
            'poll_count': self.poll_count,
            'max_polls': self.max_polls,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'previous_comment_text': self.previous_comment_text
        }
