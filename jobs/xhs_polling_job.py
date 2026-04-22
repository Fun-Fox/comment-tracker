"""
小红书帖子评论监控的轮询任务管理器。
管理检查新评论的轮询任务。
"""
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from playwright.async_api import BrowserContext
from loguru import logger

from extractor.xhs_parser import XHSParser
from services.notification_service import FeishuNotificationService


class PollingJob:
    """
    代表单个小红书帖子的轮询任务。

    在配置的时长内轮询帖子页面以检测新评论。
    如果检测到评论（数量 > 1），则发送通知并停止。
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
        self.parser = XHSParser(browser_context)

        # 任务状态
        self.status = 'pending'  # pending(待处理), running(运行中), completed(已完成), failed(失败)
        self.created_at = datetime.now()
        self.last_poll_time = None
        self.poll_count = 0
        self.previous_comment_count = 0
        self.retry_count = 0  # 当前重试次数
        self.max_retries = 0  # 最大重试次数
        
        # 从环境变量读取轮询配置
        self.poll_interval_minutes = int(os.getenv('XHS_POLL_INTERVAL_MINUTES', '30'))
        self.poll_duration_minutes = int(os.getenv('XHS_POLL_DURATION_MINUTES', '60'))
        self.max_retries = int(os.getenv('XHS_MAX_RETRIES', '3'))  # 最大重试次数
        
        # 计算最大轮询次数
        self.max_polls = self.poll_duration_minutes // self.poll_interval_minutes
        if self.max_polls < 1:
            self.max_polls = 1
        
        logger.info(f"为URL创建轮询任务 {job_id}: {url}，间隔: {self.poll_interval_minutes}分钟，总时长: {self.poll_duration_minutes}分钟，最多轮询: {self.max_polls}次")

    async def run(self):
        """
        执行轮询任务。
        根据配置的间隔时间和总时长进行轮询。
        """
        try:
            self.status = 'running'
            logger.info(f"开始轮询任务 {self.job_id}，间隔: {self.poll_interval_minutes}分钟，总时长: {self.poll_duration_minutes}分钟，最大重试: {self.max_retries}次")

            # 根据总时长和间隔动态轮询
            for i in range(self.max_polls):
                # 等待间隔时间
                wait_time = self.poll_interval_minutes * 60
                logger.info(f"任务 {self.job_id}: 等待 {wait_time}秒后进行第 {i+1} 次轮询")
                await asyncio.sleep(wait_time)

                # 执行轮询（带重试机制）
                success = await self._perform_poll_with_retry()

                # 如果检测到评论，提前结束
                if self.status == 'completed':
                    logger.info(f"任务 {self.job_id} 在第 {i+1} 次轮询后完成（检测到评论）")
                    return

            logger.info(f"任务 {self.job_id} 完成所有轮询（共{self.max_polls}次）")

        except Exception as e:
            self.status = 'failed'
            logger.error(f"轮询任务 {self.job_id} 失败: {e}", exc_info=True)

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
                        f"小红书任务 {self.job_id}: 第 #{self.poll_count} 次轮询失败（尝试 {attempt + 1}/{self.max_retries + 1}）: {e}"
                        f"\n将在 {retry_wait}秒后重试..."
                    )
                    await asyncio.sleep(retry_wait)
                else:
                    # 已用完所有重试次数
                    logger.error(
                        f"小红书任务 {self.job_id}: 第 #{self.poll_count} 次轮询彻底失败，已达最大重试次数 {self.max_retries}",
                        exc_info=True
                    )
                    return False
        return False

    async def _perform_poll(self):
        """
        执行单次轮询：获取页面、解析评论、检查变化。
        """
        try:
            self.poll_count += 1
            self.last_poll_time = datetime.now()

            logger.info(
                f"任务 {self.job_id}: 执行第 #{self.poll_count} 次轮询"
            )

            # 获取并解析笔记信息（包含标题和评论）
            note_data = await self.parser.get_note_info(self.url)

            if note_data.get('error'):
                logger.warning(
                    f"任务 {self.job_id}: 第 #{self.poll_count} 次轮询时出错: "
                    f"{note_data['error']}"
                )
                return

            current_comment_count = note_data['comment_count']
            comment_list = note_data['comment_list']
            note_title = note_data.get('note_title', '未知标题')

            logger.info(
                f"任务 {self.job_id}: 第 #{self.poll_count} 次轮询 - "
                f"标题: {note_title}, "
                f"找到 {current_comment_count} 条评论 "
                f"(上次: {self.previous_comment_count})"
            )

            # 检查是否有新评论
            if current_comment_count > 1 and len(comment_list) > 0:
                # 检测到评论！发送通知
                logger.info(
                    f"任务 {self.job_id}: 检测到评论！"
                    f"数量: {current_comment_count}. 正在发送飞书通知..."
                )

                notification_sent = await self.notification_service.send_notification(
                    note_id=note_data['note_id'],
                    note_url=self.url,
                    note_title=note_title,
                    comment_count=current_comment_count,
                    comment_list=comment_list
                )

                if notification_sent:
                    logger.info(f"任务 {self.job_id}: 飞书通知发送成功")
                else:
                    logger.error(f"任务 {self.job_id}: 飞书通知发送失败")

                # 标记任务为已完成 - 无需继续轮询
                self.status = 'completed'
                return
            else:
                # 还没有重要评论
                logger.info(
                    f"任务 {self.job_id}: 未检测到新评论. "
                    f"数量: {current_comment_count}"
                )
                self.previous_comment_count = current_comment_count

                # 如果是最后一次轮询，标记为已完成
                if self.poll_count >= self.max_polls:
                    self.status = 'completed'
                    logger.info(
                        f"任务 {self.job_id}: 所有轮询已完成. "
                        f"监控期间未检测到评论."
                    )

        except Exception as e:
            logger.error(
                f"任务 {self.job_id}: 第 #{self.poll_count} 次轮询时出错: {e}",
                exc_info=True
            )
            # 将异常向上抛出，交由 _perform_poll_with_retry 处理
            raise

    def get_status(self) -> Dict[str, Any]:
        """获取当前任务状态信息。"""
        return {
            'job_id': self.job_id,
            'url': self.url,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'last_poll_time': self.last_poll_time.isoformat() if self.last_poll_time else None,
            'poll_count': self.poll_count,
            'max_polls': self.max_polls,
            'previous_comment_count': self.previous_comment_count
        }
