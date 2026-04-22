"""
小红书 (XHS) 帖子解析模块。
从小红书帖子页面提取评论数据。
"""
import re
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from playwright.async_api import BrowserContext
from loguru import logger

# 加载环境变量
load_dotenv()


class XHSParser:
    """小红书帖子页面解析器，用于提取评论信息。"""

    def __init__(self, browser_context: BrowserContext):
        self.browser_context = browser_context
        # 注意：使用persistent_context时，不要手动设置User-Agent
        # 让它使用真实的Chrome UA以避免被检测

    @staticmethod
    def extract_note_id(url: str) -> Optional[str]:
        """
        从小红书帖子URL中提取笔记ID。

        Args:
            url: 小红书帖子URL（例如：https://www.xiaohongshu.com/explore/xxx 或 https://xhslink.com/xxx）

        Returns:
            如果找到则返回笔记ID，否则返回None
        """
        # 模式1: /explore/{note_id}
        match = re.search(r'/explore/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)

        # 模式2: /discovery/item/{note_id}
        match = re.search(r'/discovery/item/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)

        # 模式3: xhslink.com 短链接需要先解析
        logger.warning(f"无法从URL提取笔记ID: {url}")
        return None

    async def fetch_initial_state(self, url: str) -> Optional[Dict[str, Any]]:
        """
        使用Playwright获取小红书帖子的数据。
        先通过JavaScript获取noteDetailMap中的笔记对象，然后在Python端解析。

        Args:
            url: 小红书帖子URL

        Returns:
            包含笔记标题和评论列表的字典，失败则返回None
        """
        page = None
        try:
            # 创建新页面
            page = await self.browser_context.new_page()
            
            # 如果有全局cookie，添加到页面
            try:
                from main import xhs_cookies
                if xhs_cookies:
                    await self.browser_context.add_cookies(xhs_cookies)
                    logger.info(f"已添加 {len(xhs_cookies)} 个 Cookie 到浏览器上下文")
            except:
                pass

            logger.info(f"正在加载页面: {url}")
            response = await page.goto(url, timeout=30000)

            if response and response.status != 200:
                logger.error(f"获取页面失败: HTTP {response.status}")
                await page.close()
                return None

            # 等待页面完全加载和JavaScript执行
            await page.wait_for_timeout(8000)

            # 提取笔记ID
            note_id = self.extract_note_id(url)
            if not note_id:
                logger.error("无法提取笔记ID")
                await page.close()
                return None

            # 执行 JavaScript 获取 noteDetailMap[note_id] 对象
            note_detail = await page.evaluate("() => window.__INITIAL_STATE__?.note?.noteDetailMap")

            if not note_detail:
                logger.warning("✗ 浏览器中未找到指定笔记数据")
                await page.close()
                return None

            logger.info("✓ 成功获取笔记原始数据")

            # 在Python端解析数据
            note_data = self.parse_note_detail(note_detail[note_id], note_id)

            # 调试：保存数据到文件（仅在 DEBUG 模式下）
            if os.getenv('DEBUG', 'false').lower() == 'true':
                debug_dir = "debug_data"
                os.makedirs(debug_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_file = os.path.join(debug_dir, f"xhs_parsed_{note_id}_{timestamp}.json")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump(note_data, f, ensure_ascii=False, indent=2)
                logger.info(f"解析数据已保存到: {debug_file}")

            await page.close()
            return note_data

        except Exception as e:
            logger.error(f"获取页面时出错: {e}")
            if page:
                await page.close()
            return None

    def parse_note_detail(self, note_detail: Dict[str, Any], note_id: str) -> Dict[str, Any]:
        """
        在Python端解析noteDetail对象，提取所需数据。
        数据结构：noteDetailMap[note_id] 包含 note 和 comments 两个主要字段。

        Args:
            note_detail: 从浏览器获取的noteDetailMap[note_id]对象
            note_id: 笔记ID

        Returns:
            解析后的结构化数据
        """
        try:
            # note 字段包含笔记详细信息
            note_info = note_detail.get('note', {})
            
            # comments 字段包含评论数据
            comments_data = note_detail.get('comments', {})
            comment_list = comments_data.get('list', [])
            
            # 过滤掉作者的评论（showTags 包含 'is_author'）
            filtered_comments = [c for c in comment_list if 'is_author' not in c.get('showTags', [])]
            
            # 提取笔记信息
            title = note_info.get('title') or note_info.get('desc') or '未知标题'
            user = note_info.get('user', {})
            interact_info = note_info.get('interactInfo', {})
            
            # 提取每条评论的关键信息
            comments = []
            for c in filtered_comments:
                comment_user = c.get('user', {})
                comments.append({
                    'id': c.get('id'),
                    'content': c.get('content'),
                    'user': {
                        'nickname': comment_user.get('nickname'),
                        'image': comment_user.get('image'),
                        'userId': comment_user.get('userId')
                    },
                    'likeCount': c.get('likeCount', 0),
                    'showTags': c.get('showTags', []),
                    'createTime': c.get('createTime')
                })
            
            # 构建返回数据
            result = {
                'noteId': note_id,
                'title': title,
                'author': {
                    'nickname': user.get('nickname'),
                    'image': user.get('image')
                },
                'likedCount': interact_info.get('likedCount', 0),
                'shareCount': interact_info.get('shareCount', 0),
                'commentCount': len(filtered_comments),
                'totalComments': len(comment_list),
                'comments': comments,
                'hasMore': comments_data.get('hasMore', False),
                'cursor': comments_data.get('cursor')
            }
            
            logger.info(f"✓ 成功解析笔记: {title}")
            logger.info(f"总评论数: {len(comment_list)}, 过滤后用户评论: {len(filtered_comments)}")
            
            return result
            
        except Exception as e:
            logger.error(f"解析笔记数据时出错: {e}", exc_info=True)
            return None


    def extract_note_data(self, initial_state: Dict[str, Any], note_id: str) -> Dict[str, Any]:
        """
        从INITIAL_STATE中提取笔记数据和评论列表。

        根据截图，数据结构是:
        window.__INITIAL_STATE__.note.previousData
        或者可能是 note.noteDetailMap[note_id]

        Args:
            initial_state: __INITIAL_STATE__字典
            note_id: 笔记/帖子ID

        Returns:
            包含note_title、comment_count和comment_list的字典
        """
        result = {
            'note_title': '未知标题',
            'comment_count': 0,
            'comment_list': [],
            'has_comments': False
        }

        try:
            note_data = initial_state.get('note', {})

            # 尝试多种可能的数据结构
            # 方式1: noteDetailMap（旧版结构）
            note_detail_map = note_data.get('noteDetailMap', {})
            if note_id in note_detail_map:
                note_info = note_detail_map[note_id].get('note', {})
                comments_data = note_detail_map[note_id].get('comments', {})
                result['note_title'] = note_info.get('title', note_info.get('desc', '未知标题'))
                all_comments = comments_data.get('list', [])
                # 过滤掉作者的评论（showTags 包含 'is_author'）
                comment_list = [c for c in all_comments if 'is_author' not in c.get('showTags', [])]
                result['comment_count'] = len(comment_list)
                result['comment_list'] = comment_list
                result['has_comments'] = len(comment_list) > 0
                logger.info(f"找到笔记 {note_id}，标题: {result['note_title']}，{len(all_comments)} 条总评论，{result['comment_count']} 条用户评论")
                return result

            # 方式2: previousData（新版结构，根据截图）
            previous_data = note_data.get('previousData', {})
            if previous_data:
                # 从previousData中提取信息
                result['note_title'] = previous_data.get('title', previous_data.get('desc', '未知标题'))

                # 尝试获取评论数据
                if 'comments' in previous_data:
                    comment_list = previous_data['comments'].get('list', [])
                    result['comment_count'] = len(comment_list)
                    result['comment_list'] = comment_list
                    result['has_comments'] = len(comment_list) > 0

                logger.info(f"找到笔记 {note_id}，标题: {result['note_title']}，{result['comment_count']} 条评论")
                return result

            logger.warning(f"在INITIAL_STATE中未找到笔记ID {note_id}的数据")
            logger.debug(f"可用的note键: {list(note_data.keys())}")

        except Exception as e:
            logger.error(f"提取笔记数据时出错: {e}", exc_info=True)

        return result

    async def get_note_info(self, url: str) -> Dict[str, Any]:
        """
        主方法：从小红书帖子URL获取笔记信息和评论。

        Args:
            url: 小红书帖子URL

        Returns:
            包含note_id、note_title、comment_count、comment_list和has_comments的字典
        """
        note_data = await self.fetch_initial_state(url)
        if not note_data:
            return {
                'note_id': None,
                'note_title': '',
                'comment_count': 0,
                'comment_list': [],
                'has_comments': False,
                'error': '获取笔记数据失败'
            }

        # 转换数据结构以兼容旧接口
        result = {
            'note_id': note_data.get('noteId'),
            'note_title': note_data.get('title', '未知标题'),
            'comment_count': note_data.get('commentCount', 0),
            'comment_list': note_data.get('comments', []),
            'has_comments': note_data.get('commentCount', 0) > 0,
            'author': note_data.get('author', {}),
            'liked_count': note_data.get('likedCount', 0),
            'share_count': note_data.get('shareCount', 0),
            'has_more': note_data.get('hasMore', False)
        }

        return result
