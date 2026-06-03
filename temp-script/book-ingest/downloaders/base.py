# -*- coding: utf-8 -*-
"""
基础下载器

提供通用的下载、去重、重试逻辑
"""
import asyncio
import hashlib
import aiohttp
from pathlib import Path
from typing import Optional, Dict, Set
from urllib.parse import urlparse

import sys
import os
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

import config
from utils import Logger


class BaseDownloader:
    """基础下载器"""
    
    def __init__(self, output_dir: Path = None):
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data" / "assets"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.downloaded_urls: Set[str] = set()
        self.downloaded_hashes: Set[str] = set()
        
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def init(self):
        """初始化 session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=config.IMAGE_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
    async def close(self):
        """关闭 session"""
        if self.session:
            await self.session.close()
            self.session = None
            
    def _get_url_hash(self, url: str) -> str:
        """计算 URL 的哈希值"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_content_hash(self, content: bytes) -> str:
        """计算内容的哈希值"""
        return hashlib.md5(content).hexdigest()

    def _looks_like_image(self, content: bytes, content_type: str = "") -> bool:
        """校验下载结果确实是图片，避免把反爬 HTML 保存成 jpg。"""
        if not content or len(content) < 128:
            return False
        if content_type and "image/" in content_type.lower():
            return True
        signatures = (
            b"\xff\xd8\xff",  # jpg
            b"\x89PNG\r\n\x1a\n",
            b"GIF87a",
            b"GIF89a",
            b"RIFF",  # webp starts with RIFF....WEBP
        )
        return content.startswith(signatures)
    
    def _get_filename_from_url(self, url: str) -> str:
        """从 URL 提取文件名"""
        parsed = urlparse(url)
        path = parsed.path
        filename = Path(path).name
        return filename if filename else "image.jpg"
    
    async def download(
        self, 
        url: str, 
        save_path: Path,
        headers: Dict = None,
        skip_if_exists: bool = True
    ) -> Optional[Path]:
        """
        下载文件
        
        Args:
            url: 下载地址
            save_path: 保存路径
            headers: 请求头
            skip_if_exists: 如果文件已存在则跳过
            
        Returns:
            保存路径，失败返回 None
        """
        if not url:
            return None
            
        await self.init()
        
        if skip_if_exists and save_path.exists():
            Logger.info(f"文件已存在，跳过: {save_path}")
            return save_path
            
        if url in self.downloaded_urls:
            Logger.info(f"URL 已下载，跳过: {url}")
            return None
            
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        }
        
        if headers:
            default_headers.update(headers)
            
        for attempt in range(config.MAX_RETRIES):
            try:
                async with self.session.get(url, headers=default_headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        content_type = response.headers.get("Content-Type", "")
                        if not self._looks_like_image(content, content_type):
                            Logger.warning(f"下载结果不是有效图片，跳过: {url}")
                            continue
                        
                        content_hash = self._get_content_hash(content)
                        if content_hash in self.downloaded_hashes:
                            Logger.info(f"内容已存在（哈希重复），跳过: {url}")
                            return None
                            
                        save_path.parent.mkdir(parents=True, exist_ok=True)
                        save_path.write_bytes(content)
                        
                        self.downloaded_urls.add(url)
                        self.downloaded_hashes.add(content_hash)
                        
                        Logger.success(f"下载成功: {save_path.name}")
                        return save_path
                    else:
                        Logger.warning(f"下载失败 (HTTP {response.status}): {url}")
                        
            except Exception as e:
                Logger.error(f"下载失败 (尝试 {attempt + 1}/{config.MAX_RETRIES}): {e}")
                if attempt < config.MAX_RETRIES - 1:
                    await asyncio.sleep(config.RETRY_DELAY)
                    
        return None
    
    async def download_with_referer(
        self,
        url: str,
        save_path: Path,
        referer: str,
        skip_if_exists: bool = True
    ) -> Optional[Path]:
        """
        带 Referer 的下载（用于豆瓣等网站）
        
        Args:
            url: 下载地址
            save_path: 保存路径
            referer: Referer 头
            skip_if_exists: 如果文件已存在则跳过
            
        Returns:
            保存路径，失败返回 None
        """
        headers = {'Referer': referer}
        return await self.download(url, save_path, headers, skip_if_exists)
