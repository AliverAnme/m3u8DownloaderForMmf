import shutil
from asyncio import subprocess

import requests
import json
import os
import sqlite3
import re
import urllib3
import logging
import time
import argparse
import tempfile
import threading
from datetime import datetime
from dataclasses import asdict
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from video_downloader.download.manager import DownloadManager
from data.models.DataModels import *
from data.models.FeedModels import Feed, FeedVideoItem
from video_downloader.core.logger import LoggerManager, info, warning, error

# 禁用urllib3的不安全请求警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 初始化日志系统
logger_manager = LoggerManager()
# 设置全局日志级别为INFO
logger_manager.set_level("default", logging.INFO)


temp_dir = tempfile.mkdtemp(prefix="video_download_")
# # 用于测试特定标题格式的函数
# def test_title_extraction(text: str):
#     """
#     测试特定格式标题的提取功能
#     """
#     # 测试用户提供的特定标题格式
#     test_description = text

#     print("\n=== 测试特定标题提取 ===")
#     print(f"原始描述: {test_description}")
#     extracted_title = extract_title_from_description(test_description)
#     print(f"提取的标题: {extracted_title}")
#     print(f"标题提取成功: {extracted_title != '未获取到标题信息'}")
#     print("=== 测试结束 ===\n")

# # 用于测试URL合成功能的函数
# def test_url_composition():
#     # 测试用例1: URL为空，使用UID合成URL
#     test_data1 = {
#         'uid': 'test_uid_123',
#         'url': '',
#         'title': '测试视频1',
#         'description': '这是测试视频1的描述'
#     }

#     # 过滤掉不在类字段中的键
#     field_names = {f.name for f in VideoRecord.__dataclass_fields__.values()}
#     filtered_data1 = {k: v for k, v in test_data1.items() if k in field_names}

#     # 处理URL为空的情况
#     url1 = filtered_data1.get('url', '')
#     uid1 = filtered_data1.get('uid', '')
#     if not url1 and uid1:
#         filtered_data1['url'] = f"https://videodelivery.net/{uid1}/manifest/video.m3u8"

#     print(f"测试用例1: URL为空时合成URL - {filtered_data1['url']}")
#     assert filtered_data1['url'] == "https://videodelivery.net/test_uid_123/manifest/video.m3u8", "URL合成失败"

#     # 测试用例2: URL存在，不合成URL
#     test_data2 = {
#         'uid': 'test_uid_456',
#         'url': 'https://existing.url/video.mp4',
#         'title': '测试视频2',
#         'description': '这是测试视频2的描述'
#     }

#     # 过滤掉不在类字段中的键
#     field_names = {f.name for f in VideoRecord.__dataclass_fields__.values()}
#     filtered_data2 = {k: v for k, v in test_data2.items() if k in field_names}

#     # 处理URL为空的情况
#     url2 = filtered_data2.get('url', '')
#     uid2 = filtered_data2.get('uid', '')
#     if not url2 and uid2:
#         filtered_data2['url'] = f"https://videodelivery.net/{uid2}/manifest/video.m3u8"

#     print(f"测试用例2: URL存在时不合成URL - {filtered_data2['url']}")
#     assert filtered_data2['url'] == "https://existing.url/video.mp4", "不应该合成URL"

#     print("URL合成功能测试通过！")


# def test_description_cleanup():
#     print("\n=== 测试description清理功能 ===")
#     # 测试用例1: 包含标题和多个标签的情况
#     description1 = "【0722-28】導演親身示範教大畏表演勾引男人🤣💙幕後花絮 逆愛 Revenged Love #逆愛 #柴雞蛋 #吳所畏 #梓渝 #池騁 #田栩寧 #RevengedLove #ZiYu #WuSuowei #TianXuning #ChiCheng  #Memefans #BL #boyslove"

#     # 模拟处理description - 只保留标签内容
#     if description1:
#         # 匹配所有标签（以#开头的单词）
#         hashtag_pattern = r'(#\S+)'
#         hashtags = re.findall(hashtag_pattern, description1)

#         if hashtags:
#             # 组合所有标签，用空格分隔
#             cleaned_description1 = ' '.join(hashtags)
#         else:
#             cleaned_description1 = description1
#     else:
#         cleaned_description1 = description1

#     print(f"测试用例1: 包含标题和多个标签 - 清理后: '{cleaned_description1}'")
#     expected_result1 = "#逆愛 #柴雞蛋 #吳所畏 #梓渝 #池騁 #田栩寧 #RevengedLove #ZiYu #WuSuowei #TianXuning #ChiCheng #Memefans #BL #boyslove"
#     assert cleaned_description1 == expected_result1, "包含标题和多个标签的情况处理失败"

#     # 测试用例2: 只有标签的情况
#     description2 = "#逆愛 #柴雞蛋 #郭城宇 只有标签没有其他内容"

#     # 模拟处理description - 只保留标签内容
#     if description2:
#         # 匹配所有标签（以#开头的单词）
#         hashtag_pattern = r'(#\S+)'
#         hashtags = re.findall(hashtag_pattern, description2)

#         if hashtags:
#             # 组合所有标签，用空格分隔
#             cleaned_description2 = ' '.join(hashtags)
#         else:
#             cleaned_description2 = description2
#     else:
#         cleaned_description2 = description2

#     print(f"测试用例2: 只有标签的情况 - 清理后: '{cleaned_description2}'")
#     expected_result2 = "#逆愛 #柴雞蛋 #郭城宇"
#     assert cleaned_description2 == expected_result2, "只有标签的情况处理失败"

#     # 测试用例3: 没有标签的情况
#     description3 = "没有标签只有普通描述内容"

#     # 模拟处理description - 只保留标签内容
#     if description3:
#         # 匹配所有标签（以#开头的单词）
#         hashtag_pattern = r'(#\S+)'
#         hashtags = re.findall(hashtag_pattern, description3)

#         if hashtags:
#             # 组合所有标签，用空格分隔
#             cleaned_description3 = ' '.join(hashtags)
#         else:
#             cleaned_description3 = description3
#     else:
#         cleaned_description3 = description3

#     print(f"测试用例3: 没有标签的情况 - 清理后: '{cleaned_description3}'")
#     expected_result3 = "没有标签只有普通描述内容"
#     assert cleaned_description3 == expected_result3, "没有标签的情况处理失败"

#     print("description只保留标签内容功能测试通过！")


class SimpleDatabaseManager:
    """
    简单的数据库管理器 - 不依赖项目现成代码，实现基本的数据库操作
    """

    def __init__(self, db_path: str = "data/simple_m3u8.db"):
        self.db_path = db_path
        self.init_database()

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            # 确保数据库目录存在
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
            yield conn
        except sqlite3.Error as e:
            error(f"数据库连接错误: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def init_database(self):
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 创建作者表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS authors (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    avatar TEXT,
                    region TEXT,
                    created_at TEXT,
                    role TEXT,
                    status TEXT,
                    invitation_id TEXT
                )
            """)

            # 创建集合表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collections (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    region TEXT,
                    author_id TEXT,
                    title TEXT,
                    description TEXT,
                    cover TEXT,
                    original_cover TEXT,
                    subscriber_count INTEGER,
                    contributor_count INTEGER,
                    content_type TEXT,
                    contents_count INTEGER,
                    carnival_status TEXT,
                    carnival_start_time TEXT,
                    is_subscribed INTEGER,
                    is_post_in_collection INTEGER,
                    is_contributor INTEGER,
                    can_commit INTEGER,
                    chat_join_threshold INTEGER,
                    FOREIGN KEY (author_id) REFERENCES authors (id)
                )
            """)

            # 创建视频表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    title TEXT NOT NULL,
                    cover TEXT,
                    url TEXT,
                    url_type TEXT,
                    description TEXT,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    comments_count INTEGER,
                    likes_count INTEGER,
                    collections_count INTEGER,
                    processing_status TEXT,
                    region TEXT,
                    width INTEGER,
                    height INTEGER,
                    uid TEXT,
                    is_locked INTEGER,
                    holdview_amount TEXT,
                    free_seconds INTEGER,
                    author_id TEXT,
                    is_liked INTEGER,
                    is_in_collection INTEGER,
                    is_favorite INTEGER,
                    shoot_period TEXT DEFAULT '0000',
                    FOREIGN KEY (author_id) REFERENCES authors (id)
                )
            """)

            # 创建视频标签表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS video_tags (
                    video_id TEXT,
                    tag TEXT,
                    PRIMARY KEY (video_id, tag),
                    FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
                )
            """)

            # 创建集合视频关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collection_videos (
                    collection_id TEXT,
                    video_id TEXT,
                    sequence INTEGER,
                    PRIMARY KEY (collection_id, video_id),
                    FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE,
                    FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
                )
            """)

            # 创建订阅表 - 修正后的结构，包含分页信息
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feeds (
                    id TEXT PRIMARY KEY DEFAULT 'default_feed',
                    contents_count INTEGER,
                    total INTEGER,
                    page INTEGER,
                    size INTEGER,
                    pages INTEGER
                )
            """)

            # 创建订阅视频关联表
            (
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS feed_videos (
                    feed_id TEXT,
                    video_id TEXT,
                    sequence INTEGER,
                    PRIMARY KEY (feed_id, video_id),
                    FOREIGN KEY (feed_id) REFERENCES feeds (id) ON DELETE CASCADE,
                    FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
                )
            """),
            )

            conn.commit()
            info(f"数据库初始化完成: {self.db_path}")

    def save_author(self, author: "Author"):
        """保存作者信息到数据库"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 插入或替换作者数据
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO authors (
                        id, name, username, avatar, region, created_at, role, status, invitation_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        author.id,
                        author.name,
                        author.username,
                        author.avatar,
                        author.region,
                        author.created_at,
                        author.role,
                        author.status,
                        author.invitation_id,
                    ),
                )
                conn.commit()
                return True
            except sqlite3.Error as e:
                error(f"保存作者信息失败: {e}")
                return False

    def save_collection(self, collection: "CollectionData"):
        """保存集合数据到数据库"""
        # 先保存作者信息（如果有）
        if collection.author:
            self.save_author(collection.author)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 插入或替换集合数据
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO collections (
                        id, type, status, created_at, updated_at, region, author_id, title,
                        description, cover, original_cover, subscriber_count, contributor_count,
                        content_type, contents_count, carnival_status, carnival_start_time,
                        is_subscribed, is_post_in_collection, is_contributor, can_commit,
                        chat_join_threshold
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        collection.id,
                        collection.type,
                        collection.status,
                        collection.created_at,
                        collection.updated_at,
                        collection.region,
                        collection.author_id,
                        collection.title,
                        collection.description,
                        collection.cover,
                        collection.original_cover,
                        collection.subscriber_count,
                        collection.contributor_count,
                        collection.content_type,
                        collection.contents_count,
                        collection.carnival_status,
                        collection.carnival_start_time,
                        1
                        if collection.is_subscribed
                        else 0
                        if collection.is_subscribed is not None
                        else None,
                        1
                        if collection.is_post_in_collection
                        else 0
                        if collection.is_post_in_collection is not None
                        else None,
                        1
                        if collection.is_contributor
                        else 0
                        if collection.is_contributor is not None
                        else None,
                        1
                        if collection.can_commit
                        else 0
                        if collection.can_commit is not None
                        else None,
                        collection.chat_join_threshold,
                    ),
                )
                conn.commit()
                return True
            except sqlite3.Error as e:
                error(f"保存集合数据失败: {e}")
                return False

    def save_video(self, video: "VideoRecord"):
        """保存视频记录到数据库"""
        # 先保存作者信息（如果有）
        if video.author:
            self.save_author(video.author)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 开始事务
                conn.execute("BEGIN TRANSACTION")

                # 插入或替换视频数据
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO videos (
                        id, type, title, cover, url, url_type, description, status,
                        created_at, updated_at, comments_count, likes_count, collections_count,
                        processing_status, region, width, height, uid, is_locked,
                        holdview_amount, free_seconds, author_id, is_liked,
                        is_in_collection, is_favorite, shoot_period
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        video.id,
                        video.type,
                        video.title,
                        video.cover,
                        video.url,
                        video.url_type,
                        video.description,
                        video.status,
                        video.created_at,
                        video.updated_at,
                        video.comments_count,
                        video.likes_count,
                        video.collections_count,
                        video.processing_status,
                        video.region,
                        video.width,
                        video.height,
                        video.uid,
                        1 if video.is_locked else 0,
                        video.holdview_amount,
                        video.free_seconds,
                        video.author.id if video.author else None,
                        1 if video.is_liked else 0,
                        1 if video.is_in_collection else 0,
                        1 if video.is_favorite else 0,
                        video.shoot_period,
                    ),
                )

                # 保存标签
                # 先删除旧标签
                cursor.execute("DELETE FROM video_tags WHERE video_id = ?", (video.id,))
                # 插入新标签
                for tag in video.tags:
                    cursor.execute(
                        "INSERT OR REPLACE INTO video_tags (video_id, tag) VALUES (?, ?)",
                        (video.id, tag),
                    )

                # 提交事务
                conn.commit()
                return True
            except sqlite3.Error as e:
                error(f"保存视频数据失败: {e}")
                conn.rollback()
                return False

    def save_collection_videos(self, collection_id: str, video_ids: List[str]):
        """保存集合与视频的关联关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 开始事务
                conn.execute("BEGIN TRANSACTION")

                # 先删除旧的关联关系
                cursor.execute(
                    "DELETE FROM collection_videos WHERE collection_id = ?",
                    (collection_id,),
                )

                # 插入新的关联关系
                for idx, video_id in enumerate(video_ids):
                    cursor.execute(
                        "INSERT OR REPLACE INTO collection_videos (collection_id, video_id, sequence) VALUES (?, ?, ?)",
                        (collection_id, video_id, idx),
                    )

                # 提交事务
                conn.commit()
                return True
            except sqlite3.Error as e:
                error(f"保存集合视频关联失败: {e}")
                conn.rollback()
                return False

    def get_collection_videos_ids(self, collection_id: str) -> set:
        """从数据库获取集合的视频ID列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT video_id FROM collection_videos WHERE collection_id = ? ORDER BY sequence",
                    (collection_id,),
                )
                results = cursor.fetchall()
                # 返回视频ID的集合
                return {row["video_id"] for row in results}
            except sqlite3.Error as e:
                error(f"获取集合视频ID失败: {e}")
                return set()

    def save_feed(self, feed: "Feed"):
        """保存订阅信息到数据库"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 插入或替换订阅数据
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO feeds (
                        id, contents_count, total, page, size, pages
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        "default_feed",  # 固定使用'default_feed'作为ID
                        len(feed.items),
                        feed.total,
                        feed.page,
                        feed.size,
                        feed.pages,
                    ),
                )
                conn.commit()
                return True
            except sqlite3.Error as e:
                error(f"保存订阅信息失败: {e}")
                return False

    def save_feed_videos(self, feed_id: str, feed_items: List["FeedVideoItem"]):
        """保存订阅与视频的关联关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 开始事务
                conn.execute("BEGIN TRANSACTION")

                # 先删除旧的关联关系
                cursor.execute("DELETE FROM feed_videos WHERE feed_id = ?", (feed_id,))

                # 插入新的关联关系
                for idx, item in enumerate(feed_items):
                    cursor.execute(
                        "INSERT OR REPLACE INTO feed_videos (feed_id, video_id, sequence) VALUES (?, ?, ?)",
                        (feed_id, item.id, idx),
                    )

                # 提交事务
                conn.commit()
                return True
            except sqlite3.Error as e:
                error(f"保存订阅视频关联失败: {e}")
                conn.rollback()
                return False

    def get_feed_videos_ids(self, feed_id: str) -> set:
        """从数据库获取订阅的视频ID列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT video_id FROM feed_videos WHERE feed_id = ? ORDER BY sequence",
                    (feed_id,),
                )
                results = cursor.fetchall()
                # 返回视频ID的集合
                return {row["video_id"] for row in results}
            except sqlite3.Error as e:
                error(f"获取订阅视频ID失败: {e}")
                return set()


def make_api_request(
    url: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> Optional[Dict[str, Any]]:
    """
    向指定的API URL发送GET请求并返回响应结果

    Args:
        url (str): 请求的URL地址
        max_retries (int): 最大重试次数，默认为3次
        retry_delay (float): 初始重试延迟时间（秒），默认为1.0
        backoff_factor (float): 延迟时间递增因子，默认为2.0

    Returns:
        Optional[Dict[str, Any]]: API返回的JSON数据，如果请求失败则返回None
    """

    config = Config()

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                delay = retry_delay * (backoff_factor ** (attempt - 1))
                warning(f"⏳ API请求第 {attempt} 次重试，等待 {delay:.1f} 秒...")
                time.sleep(delay)

            info(f"🔄 API请求尝试 {attempt + 1}/{max_retries + 1}")

            # 发送GET请求，跳过SSL证书验证
            response = requests.get(url, verify=False, headers=config.DEFAULT_HEADERS)

            # 检查请求是否成功
            if response.status_code == 200:
                # 尝试解析JSON响应
                try:
                    data = response.json()
                    if attempt > 0:
                        info(f"✅ API请求重试成功！")
                    return data
                except json.JSONDecodeError:
                    error(f"请求成功，但返回的数据不是有效的JSON格式: {url}")
                    error(f"响应内容：{response.text[:100]}...")
                    if attempt < max_retries:
                        warning(f"⚠️ 准备重试...")
                        continue
                    return None
            else:
                error(f"请求失败，状态码：{response.status_code}，URL: {url}")
                error(f"错误信息：{response.text[:100]}...")
                if attempt < max_retries:
                    warning(f"⚠️ 准备重试...")
                    continue
                return None
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                error(f"❌ API请求异常: {e}，URL: {url}，准备重试...")
            else:
                error(f"❌ API请求失败，已重试 {max_retries} 次，最后错误: {e}")

    error(f"💥 API请求失败，已重试 {max_retries} 次")
    return None


def extract_title_from_description(description: str) -> str:
    """
    从description中提取视频标题
    处理多种标题格式：
    - 【0725-7】池騁抱大畏做體能訓練😂💙幕後花絮 逆愛 Revenged Love
    - 【果酱0725-7】池騁抱大畏做體能訓練😂💙幕後花絮 逆愛 Revenged Love
    - 【Revenged Love】0623 BTS Collection | 逆愛 0623 花絮合集
    - 【Revenged Love】0701 BTS Collection | 逆愛 0701 花絮合集
    """
    if not description:
        return "未获取到标题信息"

    # 方法1: 首先尝试直接提取【】中的内容作为标题
    bracket_pattern = r"【([^】]+)】"
    match = re.search(bracket_pattern, description)
    if match:
        bracket_content = match.group(1).strip()
        # 完整提取包括【】的标题
        full_title = match.group(0).strip()

        # 查找【】后面可能的内容，直到遇到标签或结束
        after_bracket = description[match.end() :].strip()
        if after_bracket:
            # 查找第一个标签的位置
            tag_match = re.search(r"#\w+", after_bracket)
            if tag_match:
                # 提取【】和标签之间的内容
                between_content = after_bracket[: tag_match.start()].strip()
                if between_content:
                    return full_title + between_content
            else:
                # 如果没有标签，返回【】内容加上后面的所有内容（限制长度）
                combined_title = full_title + after_bracket
                return combined_title[:150]  # 限制标题长度

        return full_title

    # 方法2: 检查是否包含标签部分（改进版，更灵活地匹配标签）
    # 匹配任何以#开头的标签，包括含有空格的英文标签
    hashtag_pattern = (
        r"#逆愛|#柴雞蛋|#郭城宇|#展軒|#姜小帅|#刘轩丞|#Revenged\s*Love|#BTS|#花絮|#合集"
    )
    match = re.search(hashtag_pattern, description, re.IGNORECASE)

    if match:
        # 提取标签前的部分作为标题
        title_part = description[: match.start()].strip()
        if title_part:
            return title_part

    # 方法3: 尝试提取开头到第一个|符号的内容
    pipe_pattern = r"^([^|]+?)\s*\|"
    match = re.search(pipe_pattern, description)
    if match:
        title_part = match.group(1).strip()
        if title_part:
            return title_part

    # 方法4: 如果没有找到特殊格式的标题，返回前100个字符作为标题（排除明显的标签内容）
    # 移除所有标签
    clean_description = re.sub(r"#\w+", "", description)
    clean_description = clean_description.strip()

    if clean_description:
        return clean_description[:100]  # 限制标题长度

    return "未获取到标题信息"


def extract_shoot_period(title: str) -> str:
    """
    从标题中提取视频的拍摄时期
    支持的格式：
    - 【0715-2】小帥把郭城宇迷得忘了詞💙幕後花絮 逆愛 Revenged Love -> 0715
    - 【果酱0725-7】池騁抱大畏做體能訓練😂💙幕後花絮 -> 0725
    - 【Revenged Love】0623 BTS Collection -> 0623
    - 对于无法提取的情况，返回'0000'
    """
    if not title:
        return "0000"

    # 模式1：【0715-2】格式，提取【】中的数字部分
    pattern1 = r"【(\d{4})[-_]\d+】"
    match = re.search(pattern1, title)
    if match:
        return match.group(1)

    # 模式2：【果酱0725-7】格式，提取【】中的数字部分
    pattern2 = r"【.*?(\d{4})[-_]\d+】"
    match = re.search(pattern2, title)
    if match:
        return match.group(1)

    # 模式3：【Revenged Love】0623 格式，提取后面的数字部分
    pattern3 = r"【.*?】\s*(\d{4})"
    match = re.search(pattern3, title)
    if match:
        return match.group(1)

    # 模式4：检查标题中是否有单独的4位数字（可能是日期）
    pattern4 = r"\b(\d{4})\b"
    matches = re.finditer(pattern4, title)
    for match in matches:
        # 检查是否符合月份和日期的范围（01-12月，01-31日）
        digits = match.group(1)
        if len(digits) == 4:
            month = int(digits[:2])
            day = int(digits[2:])
            if 1 <= month <= 12 and 1 <= day <= 31:
                return digits

    # 如果无法提取，返回默认值
    return "0000"


def get_video_record(video_id: str) -> Optional[VideoRecord]:
    """
    获取单个视频数据并创建VideoRecord实例
    """
    url = f"https://api.memefans.ai/v2/posts/videos/{video_id}"
    info(f"正在请求视频数据: {url}")

    # 发送API请求
    data = make_api_request(url)

    # print(f"请求到的视频数据: {data}")

    if data:
        try:
            # 处理嵌套的author对象
            author_data = data.get("author")
            author = Author(**author_data) if author_data else None

            # 创建数据副本并处理author字段
            data_copy = data.copy()
            if author_data:
                data_copy["author"] = author

            # 处理标题为空的情况
            title = data_copy.get("title", "")
            description = data_copy.get("description", "")

            if not title or title.strip() == "":
                warning(f"视频ID: {video_id} 的标题为空，尝试从description中提取")
                # 从description中提取标题
                extracted_title = extract_title_from_description(description)
                data_copy["title"] = extracted_title
                info(f"成功从description中提取标题: {extracted_title}")
            elif description and title in description:
                # 如果description中包含完整的标题，也尝试提取更完整的标题
                info(
                    f"视频ID: {video_id} 的标题可能不完整，尝试从description中提取更完整的标题"
                )
                extracted_title = extract_title_from_description(description)
                if (
                    extracted_title
                    and extracted_title != "未获取到标题信息"
                    and len(extracted_title) > len(title)
                ):
                    data_copy["title"] = extracted_title
                    info(f"成功从description中提取更完整的标题: {extracted_title}")

            # 从标题中提取拍摄时期
            current_title = data_copy.get("title", "")
            shoot_period = extract_shoot_period(current_title)
            data_copy["shoot_period"] = shoot_period
            info(f"视频ID: {video_id} 的拍摄时期: {shoot_period}")

            # 从description中只保留标签内容
            if description:
                # 匹配所有标签（以#开头的单词）
                hashtag_pattern = r"(#\S+)"
                hashtags = re.findall(hashtag_pattern, description)

                if hashtags:
                    # 组合所有标签，用空格分隔
                    cleaned_description = " ".join(hashtags)
                    data_copy["description"] = cleaned_description
                    info(f"视频ID: {video_id} 的description已只保留标签内容")

            # 过滤掉不在类字段中的键
            field_names = {f.name for f in VideoRecord.__dataclass_fields__.values()}
            filtered_data = {k: v for k, v in data_copy.items() if k in field_names}

            # 处理URL为空的情况
            url = filtered_data.get("url", "")
            uid = filtered_data.get("uid", "")
            if not url and uid:
                filtered_data["url"] = (
                    f"https://videodelivery.net/{uid}/manifest/video.m3u8"
                )
                info(
                    f"视频ID: {video_id} 的URL为空，使用UID合成URL: {filtered_data['url']}"
                )

            info(f"视频ID: {video_id} 的视频链接: {url if url else 'Null'}")
            # 从标题中提取拍摄日期
            video_date = extract_shoot_period(current_title)
            filtered_data["video_date"] = video_date
            # print(f"视频ID: {video_id} 的拍摄日期: {video_date}")

            # 创建并返回VideoRecord实例
            video_record = VideoRecord(**filtered_data)
            info(f"成功创建VideoRecord实例: {video_id}")
            return video_record
        except Exception as e:
            error(f"创建VideoRecord实例失败: {e}，视频ID: {video_id}")
            return None

    return None


def show_live_countdown(seconds):
    try:
        # 将print改为info日志
        info(f"下一次检查将在 {seconds} 秒后进行")

        # 显示倒计时
        for remaining in range(seconds, 0, -1):
            minutes, secs = divmod(remaining, 60)
            # 使用回车符覆盖当前行，实现动态更新效果
            # 对于这种实时更新的信息，我们仍使用print以便在控制台更好地显示
            print(f"剩余时间: {minutes}分{secs}秒", end="\r", flush=True)
            time.sleep(1)

        # 倒计时结束时清除这一行
        print(" " * 50, end="\r", flush=True)
    except KeyboardInterrupt:
        # 捕获键盘中断信号，确保输出正确的状态信息
        print(" " * 50, end="\r", flush=True)  # 保留这一行作为终端交互操作
        info("程序中断中...")
    except Exception as e:
        # 如果发生其他异常，确保不影响主程序
        # 仅在调试模式下记录错误信息
        # error(f"倒计时显示错误: {e}")
        pass


def show_latest_videos(db_manager):
    """
    显示最新的10条视频信息，包括ID、标题和链接可访问状态
    """
    try:
        info(f"📹 最新10条视频信息（按更新时间排序）：")
        info(f"{'-' * 80}")
        info(f"{'ID':<20} {'标题':<40} {'链接状态'}")
        info(f"{'-' * 80}")

        # 从数据库获取最新的10条视频记录
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            # 查询最新的10条视频记录，按updated_at降序排序
            cursor.execute(
                """SELECT id, title, url
                   FROM videos
                   ORDER BY updated_at DESC
                   LIMIT 20"""
            )
            results = cursor.fetchall()

            if results:
                for row in results:
                    video_id = row["id"]
                    title = row["title"]
                    url = row["url"]

                    # 检查链接是否可访问（简化检查，仅判断URL是否为空）
                    url_status = "✅ 可访问" if url else "❌ 不可访问（付费视频）"

                    # 截断过长的标题以保持表格整洁
                    truncated_title = (title[:37] + "...") if len(title) > 40 else title

                    info(f"{video_id:<20} {truncated_title:<40} {url_status}")
                info(f"{'-' * 80}")
            else:
                info("暂无视频数据")
    except Exception as e:
        error(f"显示最新视频信息时发生错误: {e}")


# 定时检查集合更新并下载新增视频的函数
def check_collection_updates(
    collection_url,
    db_manager,
    download_flag=False,
    interval=120,
    download_dir="./downloads",
):
    try:
        info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始检查集合更新...")

        # 显示最新10条视频信息
        show_latest_videos(db_manager)

        # 请求最新的集合数据
        data = make_api_request(collection_url)

        if data:
            # 从JSON数据创建CollectionData实例
            collection = CollectionData.from_json(data)

            # 提取当前集合的内容ID集合
            current_contents = set(collection.contents)

            # 从数据库获取上次保存的视频ID集合
            saved_contents = db_manager.get_collection_videos_ids(collection.id)

            # 如果数据库中没有保存过该集合的内容，或者集合内容为空，保存所有视频
            # if not saved_contents:
            info(f"集合包含 {len(current_contents)} 个视频")

            # 保存集合数据到数据库
            if db_manager.save_collection(collection):
                info(f"集合数据已保存到数据库")
            else:
                error(f"保存集合数据到数据库失败")

            # 保存集合视频关联关系到数据库
            if db_manager.save_collection_videos(collection.id, collection.contents):
                info(f"集合视频关联关系已保存到数据库")
            else:
                error(f"保存集合视频关联关系到数据库失败")

            # 如果启用了下载功能，下载所有视频
            process_and_download_videos(
                collection.contents[:5], db_manager, download_dir
            )
        else:
            error("获取集合数据失败")
    except Exception as e:
        error(f"检查集合更新时发生错误: {e}")

    try:
        # 启动一个线程来显示实时倒计时
        countdown_thread = threading.Thread(
            target=show_live_countdown, args=(interval,)
        )
        countdown_thread.daemon = True  # 设置为守护线程，这样主线程结束时它也会结束
        countdown_thread.start()

        # interval秒后再次执行
        timer = threading.Timer(
            interval,
            check_feed_updates,
            args=[feed_url, db_manager, download_flag, interval],
        )
        timer.daemon = True  # 设置为守护线程
        timer.start()
    except Exception as e:
        # 捕获线程创建过程中的异常
        error(f"创建线程时发生错误: {e}")


def check_feed_updates(
    feed_url,
    db_manager: SimpleDatabaseManager,
    download_flag=False,
    interval=120,
    download_dir="./downloads",
    num=5,
    local_json_file="./temp/feed.json",
    page=1,
):
    try:
        info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始检查订阅更新...")

        # 显示最新10条视频信息
        show_latest_videos(db_manager)
        feed_url = f"{feed_url}?page={page}&size={num}"

        # 请求最新的订阅数据
        data = make_api_request(feed_url)
        # data = None

        # if not data:
        #     error("从API响应创建Feed实例失败")
        #     try:
        #         feed= Feed.from_json_file(local_json_file)
        #     except Exception as e:
        #         error(f"从JSON文件创建Feed实例失败: {e}")
        #         return

        if data:
            # 从JSON数据创建Feed实例
            feed = Feed.from_api_response(data)

            # 提取当前订阅的视频ID集合
            current_contents = set([item.id for item in feed.items])

            # 从数据库获取上次保存的视频ID集合
            # saved_contents = db_manager.get_feed_videos_ids('default_feed')

            # 如果数据库中没有保存过该订阅的内容，或者订阅内容为空，保存所有视频
            # if not saved_contents:
            info(f"订阅包含 {len(current_contents)} 个视频")
            info(
                f"分页信息: total={feed.total}, page={feed.page}, size={feed.size}, pages={feed.pages}"
            )

            # 保存订阅数据到数据库
            if db_manager.save_feed(feed):
                info(f"订阅数据已保存到数据库")
            else:
                error(f"保存订阅数据到数据库失败")

            # 保存订阅视频关联关系到数据库
            if db_manager.save_feed_videos("default_feed", feed.items):
                info(f"订阅视频关联关系已保存到数据库")
            else:
                error(f"保存订阅视频关联关系到数据库失败")

            # 如果启用了下载功能，下载所有视频
            process_and_download_videos(
                feed.filter_by_author_id("BhhLJPlVvjU")[:num], db_manager, download_dir
            )
        else:
            error("获取订阅数据失败")
    except Exception as e:
        error(f"检查订阅更新时发生错误: {e}")

    try:
        # 启动一个线程来显示实时倒计时
        countdown_thread = threading.Thread(
            target=show_live_countdown, args=(interval,)
        )
        countdown_thread.daemon = True  # 设置为守护线程，这样主线程结束时它也会结束
        countdown_thread.start()

        # interval秒后再次执行
        timer = threading.Timer(
            interval,
            check_feed_updates,
            args=[feed_url, db_manager, download_flag, interval, download_dir, num],
        )
        timer.daemon = True  # 设置为守护线程
        timer.start()
    except Exception as e:
        # 捕获线程创建过程中的异常
        error(f"创建线程时发生错误: {e}")


# 处理并下载视频的函数
def process_and_download_videos(
    videos: list[FeedVideoItem],
    db_manager: SimpleDatabaseManager,
    download_dir="./downloads",
):
    # 创建存储JSON文件的目录
    json_dir = "data/video_jsons"
    os.makedirs(json_dir, exist_ok=True)

    # 创建下载管理器
    download_manager = DownloadManager()

    # 处理每个视频ID
    for video in videos:
        try:
            info(f"处理视频 {video.id}")
            video_record = get_video_record(video.id)

            if video_record:
                # 保存VideoRecord实例到文件
                video_file_path = f"{json_dir}/{video.id}.json"
                with open(video_file_path, "w", encoding="utf-8") as f:
                    json.dump(asdict(video_record), f, ensure_ascii=False, indent=2)
                info(f"视频数据已保存到文件：{video_file_path}")

                # 保存视频数据到数据库
                if db_manager.save_video(video_record):
                    info(f"视频数据已保存到数据库")
                else:
                    error(f"保存视频数据到数据库失败")

                # 清理标题作为安全的文件名
                safe_title = download_manager.sanitize_filename(video_record.title)
                safe_date = download_manager.sanitize_filename(video_record.video_date)

                # 构建下载路径
                date_folder = os.path.join(download_dir, safe_date)
                # 使用与download_video方法相同的扩展名格式，确保路径匹配
                output_filename = (
                    f"{safe_title}_{safe_date}.{download_manager.config.OUTPUT_FORMAT}"
                )
                output_path = os.path.join(date_folder, output_filename)

                # 转换为绝对路径以确保一致性
                output_path_abs = os.path.abspath(output_path)

                # 检查文件是否已存在
                file_exists = os.path.exists(output_path_abs)

                if file_exists:
                    info(f"📁 文件已存在，跳过: {video_record.title}")
                    continue

                # 下载视频
                info(f"开始下载视频: {video_record.title}")
                download_manager.download_video(video_record, download_dir)
                info(f"视频下载完成: {video_record.title}")
        except Exception as e:
            error(f"处理视频 {video.id} 时发生错误: {e}")
            # 继续处理下一个视频
            continue

    info(f"处理完成，成功处理{len(videos)}个视频")


def update_all_videos(db_manager: SimpleDatabaseManager, feed_url, download_dir="./downloads", pages=3):
    """
    更新所有视频数据，包括从API获取最新数据、保存到数据库和下载视频
    """
    try:
        for page in range(1, pages + 1):
            check_feed_updates(
                feed_url, db_manager, not args.no_download, args.interval, download_dir, num=50, page=page
            )


    except Exception as e:
        error(f"检查订阅更新时发生错误: {e}")


# 主函数入口
if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="M3U8视频下载工具")
    parser.add_argument("--no-download", action="store_true", help="禁用视频下载")
    parser.add_argument("--force", action="store_true", help="强制重新下载已存在的视频")
    parser.add_argument("--dir", type=str, default="downloads", help="下载目录")
    parser.add_argument(
        "--interval",
        type=int,
        default=120,
        help="检查更新的时间间隔（秒），默认为120秒（2分钟）",
    )
    args = parser.parse_args()

    # 运行测试
    # print("\n=== 运行URL合成功能测试 ===")
    # test_url_composition()

    # 运行description清理功能测试
    # test_description_cleanup()

    # 初始化数据库管理器
    db_manager = SimpleDatabaseManager()
    config = Config()
    # 集合URL
    # collection_url = "https://api.memefans.ai/v2/posts/collections/BhhNPqDl_yW"
    feed_url = "https://api.memefans.ai/v2/feed"

    info(f"M3U8视频下载工具启动")
    # print(f"集合URL: {collection_url}")
    info(f"订阅URL: {feed_url}")
    info(f"检查更新间隔: {args.interval}秒")
    info(f"下载功能: {'禁用' if args.no_download else '启用'}")
    info(f"按Ctrl+C停止程序...")

    # data = make_api_request(collection_url)

    # if data:
    #     # 从JSON数据创建CollectionData实例
    #     collection = CollectionData.from_json(data)

    #     # 提取当前集合的内容ID集合
    #     current_contents = set(collection.contents)

    #     # 从数据库获取上次保存的视频ID集合
    #     saved_contents = db_manager.get_collection_videos_ids(collection.id)

    #     print(f"首次运行或数据库中没有保存集合内容，集合包含 {len(current_contents)} 个视频")

    #     # 保存集合数据到数据库
    #     if db_manager.save_collection(collection):
    #         print(f"集合数据已保存到数据库")
    #     else:
    #         print(f"保存集合数据到数据库失败")

    #     # 保存集合视频关联关系到数据库
    #     if db_manager.save_collection_videos(collection.id, collection.contents):
    #         print(f"集合视频关联关系已保存到数据库")
    #     else:
    #         print(f"保存集合视频关联关系到数据库失败")

    #     process_and_download_videos(collection.contents[:5], db_manager, "./downloads")

    # else:
    #     print("获取集合数据失败")
    # update_all_videos(db_manager, feed_url,download_dir="./downloads",pages=3)

    # 开始定时检查订阅更新
    check_feed_updates(
        feed_url, db_manager, not args.no_download, args.interval, "./downloads", num=30, page=1
    )

    # 保持主程序运行
    try:
        while True:
            time.sleep(1)  # 减少睡眠时间，使程序能够更快响应中断
    except KeyboardInterrupt:
        info("接收到中断信号，正在停止程序...")
        # 清除倒计时显示行
        print(" " * 50, end="\r", flush=True)  # 保留这一行作为终端交互操作
        # 确保输出换行，使最终消息显示在新行
        info("程序已安全停止")
    except Exception as e:
        error(f"程序异常退出: {e}")
