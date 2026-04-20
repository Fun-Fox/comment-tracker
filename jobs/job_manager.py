"""
任务管理器，用于并发处理多个轮询任务。
"""
import asyncio
import uuid
from typing import Dict, Any, List, Optional
from playwright.async_api import BrowserContext
from loguru import logger

from jobs.polling_job import PollingJob
from services.notification_service import FeishuNotificationService


class JobManager:
    """管理所有活跃的轮询任务。"""

    def __init__(self, browser_context: BrowserContext, notification_service: FeishuNotificationService):
        self.browser_context = browser_context
        self.notification_service = notification_service
        self.jobs: Dict[str, PollingJob] = {}
        self.tasks: Dict[str, asyncio.Task] = {}

    async def create_job(self, url: str) -> str:
        """
        创建一个新的轮询任务。

        Args:
            url: 小红书帖子URL

        Returns:
            任务ID
        """
        job_id = str(uuid.uuid4())
        job = PollingJob(job_id, url, self.browser_context, self.notification_service)
        self.jobs[job_id] = job

        # 启动异步任务
        task = asyncio.create_task(job.run())
        self.tasks[job_id] = task

        logger.info(f"创建并启动轮询任务 {job_id}，URL: {url}")
        return job_id

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态。

        Args:
            job_id: 任务ID

        Returns:
            任务状态字典，如果不存在则返回None
        """
        if job_id not in self.jobs:
            return None
        return self.jobs[job_id].get_status()

    def list_jobs(self) -> List[Dict[str, Any]]:
        """
        列出所有任务。

        Returns:
            所有任务的状态列表
        """
        return [job.get_status() for job in self.jobs.values()]

    async def cancel_job(self, job_id: str) -> bool:
        """
        取消任务。

        Args:
            job_id: 任务ID

        Returns:
            如果取消成功返回True
        """
        if job_id not in self.jobs:
            return False

        job = self.jobs[job_id]
        if job.status in ('completed', 'cancelled'):
            logger.warning(f"无法取消任务 {job_id}: 已经{job.status}")
            return False

        if job_id in self.tasks:
            self.tasks[job_id].cancel()
            try:
                await self.tasks[job_id]
            except asyncio.CancelledError:
                pass
            job.status = 'cancelled'
            logger.info(f"已取消任务 {job_id}")
            return True

        return False

    def get_active_job_count(self) -> int:
        """获取活跃任务数量。"""
        return sum(1 for job in self.jobs.values() if job.status == 'running')

    def get_total_job_count(self) -> int:
        """获取总任务数量。"""
        return len(self.jobs)