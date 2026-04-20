"""
飞书通知服务模块。
当检测到新评论时，通过飞书webhook发送消息卡片通知。
支持签名校验。
"""
import os
import time
import hmac
import hashlib
import base64
from typing import Dict, Any, List
from aiohttp import ClientSession
from loguru import logger


class FeishuNotificationService:
    """飞书webhook通知服务，使用消息卡片格式。"""

    def __init__(self, session: ClientSession):
        self.session = session
        # 从环境变量加载飞书webhook配置
        self.webhook_url = os.getenv('FEISHU_WEBHOOK_URL', '')
        self.sign_secret = os.getenv('FEISHU_SIGN_SECRET', '')

    def _generate_signature(self) -> tuple:
        """
        生成飞书webhook签名（签名校验方式）。

        签名方法：timestamp + "\n" + secret 作为签名字符串，
        使用HmacSHA256算法计算签名，然后进行Base64编码。

        Returns:
            元组 (timestamp, sign)，如果未配置密钥则返回 (None, None)
        """
        if not self.sign_secret:
            return None, None

        # 获取当前时间戳（秒级）
        timestamp = str(int(time.time()))

        # 拼接timestamp和密钥
        string_to_sign = f'{timestamp}\n{self.sign_secret}'

        # 使用HmacSHA256计算签名
        hmac_code = hmac.new(
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()

        # 进行Base64编码
        sign = base64.b64encode(hmac_code).decode('utf-8')

        return timestamp, sign

    def _build_card_payload(
        self,
        note_id: str,
        note_url: str,
        note_title: str,
        comment_count: int,
        first_comment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        构建飞书消息卡片payload。

        Args:
            note_id: 笔记ID
            note_url: 笔记URL
            note_title: 笔记标题
            comment_count: 评论数量
            first_comment: 第一条评论数据

        Returns:
            飞书消息卡片payload
        """
        # 获取第一条评论的详细内容
        comment_content = first_comment.get('content', '无内容')
        
        # 获取评论用户信息
        user_info = first_comment.get('userInfo', {})
        if isinstance(user_info, dict):
            comment_user = user_info.get('nickname', '未知用户')
        else:
            comment_user = '未知用户'

        # 截断过长的评论内容（飞书卡片有长度限制）
        if len(comment_content) > 200:
            comment_content = comment_content[:200] + '...'

        # 构建飞书消息卡片（使用更美观的样式）
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🔔 小红书新评论提醒"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**作品链接：** [{note_title}]({note_url})"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**💬 第一条评论：**\n> {comment_content}\n\n**👤 用户：** {comment_user}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📊 当前评论数：** {comment_count} 条"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": " 立即查看"
                            },
                            "type": "primary",
                            "url": note_url
                        }
                    ]
                }
            ]
        }

        # 构建完整的请求payload
        payload = {
            "msg_type": "interactive",
            "card": card
        }

        return payload

    async def send_notification(
        self,
        note_id: str,
        note_url: str,
        note_title: str,
        comment_count: int,
        comment_list: List[Dict[str, Any]]
    ) -> bool:
        """
        通过飞书webhook发送新评论通知（消息卡片格式）。

        Args:
            note_id: 小红书笔记/帖子ID
            note_url: 原始小红书帖子URL
            note_title: 笔记标题
            comment_count: 检测到的评论数量
            comment_list: 评论对象列表

        Returns:
            如果通知发送成功返回True，否则返回False
        """
        try:
            if not self.webhook_url:
                logger.error("飞书webhook URL未配置，请设置 FEISHU_WEBHOOK_URL 环境变量")
                return False

            if not comment_list:
                logger.warning("评论列表为空，不发送通知")
                return False

            # 获取第一条评论
            first_comment = comment_list[0]

            # 构建消息卡片
            payload = self._build_card_payload(
                note_id=note_id,
                note_url=note_url,
                note_title=note_title or '未知标题',
                comment_count=comment_count,
                first_comment=first_comment
            )

            # 生成签名（如果配置了签名密钥）
            timestamp, sign = self._generate_signature()
            if timestamp and sign:
                payload['timestamp'] = timestamp
                payload['sign'] = sign

            headers = {
                'Content-Type': 'application/json',
            }

            logger.info(f"正在发送飞书通知：笔记 {note_id}，标题 {note_title}，评论数: {comment_count}")

            async with self.session.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            ) as response:
                response_text = await response.text()
                if response.status in (200, 201):
                    logger.info(f"飞书通知发送成功，响应: {response_text}")
                    return True
                else:
                    logger.error(
                        f"发送飞书通知失败: HTTP {response.status}, "
                        f"响应: {response_text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"发送飞书通知时出错: {e}", exc_info=True)
            return False

    async def send_test_notification(self) -> bool:
        """
        发送测试通知以验证飞书webhook是否正常工作。

        Returns:
            如果测试通知发送成功返回True
        """
        return await self.send_notification(
            note_id='test_123',
            note_url='https://www.xiaohongshu.com/explore/test',
            note_title='测试作品标题',
            comment_count=1,
            comment_list=[{
                'content': '这是一条测试评论内容',
                'user': {'nickname': '测试用户', 'userid': 'test_user'},
            }]
        )