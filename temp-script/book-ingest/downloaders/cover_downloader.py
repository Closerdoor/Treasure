# -*- coding: utf-8 -*-
"""
封面下载器

从各数据源下载书籍封面
"""
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from .base import BaseDownloader
from utils import Logger


class CoverDownloader(BaseDownloader):
    """封面下载器"""
    
    def __init__(self, output_dir: Path = None):
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data" / "assets"
        super().__init__(output_dir)
        
    async def download_cover(
        self,
        book_id: str,
        cover_url: str,
        source: str = "unknown",
        filename: str = "cover-main.jpg"
    ) -> Optional[Path]:
        """
        下载单张封面
        
        Args:
            book_id: 书籍 ID
            cover_url: 封面 URL
            source: 数据来源（用于设置 Referer）
            filename: 保存文件名
            
        Returns:
            保存路径
        """
        if not cover_url:
            return None
            
        save_dir = self.output_dir / book_id
        save_path = save_dir / filename
        
        referer = self._get_referer(source, cover_url)
        
        if referer:
            return await self.download_with_referer(cover_url, save_path, referer)
        else:
            return await self.download(cover_url, save_path)
    
    def _get_referer(self, source: str, url: str) -> Optional[str]:
        """根据来源获取 Referer"""
        referer_map = {
            "douban": "https://book.douban.com/",
            "dangdang": "http://www.dangdang.com/",
            "qidian": "https://www.qidian.com/",
            "openlibrary": "https://openlibrary.org/",
        }
        return referer_map.get(source)
    
    async def download_covers(
        self,
        book_id: str,
        cover_urls: Dict[str, str],
        main_source: str = "douban"
    ) -> Dict[str, str]:
        """
        下载多张封面
        
        Args:
            book_id: 书籍 ID
            cover_urls: {来源: URL} 字典
            main_source: 主封面来源
            
        Returns:
            {文件名: 来源} 字典
        """
        results = {}
        cover_index = 1
        
        for source, url in cover_urls.items():
            if not url:
                continue
                
            if source == main_source:
                filename = "cover-main.jpg"
            else:
                filename = f"cover-{cover_index:03d}.jpg"
                cover_index += 1
                
            result = await self.download_cover(book_id, url, source, filename)
            if result:
                results[filename] = source
                
        return results
    
    async def download_from_raw_data(
        self,
        book_id: str,
        raw_data: Dict
    ) -> Dict[str, str]:
        """
        从原始数据中提取并下载封面
        
        Args:
            book_id: 书籍 ID
            raw_data: 各数据源的原始数据
            
        Returns:
            {文件名: 来源} 字典
        """
        cover_urls = {}
        
        douban_data = raw_data.get("douban", {})
        if douban_data.get("main_cover_url"):
            cover_urls["douban"] = douban_data["main_cover_url"]
        if douban_data.get("cover_urls"):
            for i, url in enumerate(douban_data["cover_urls"][:3]):
                cover_urls[f"douban_{i}"] = url
                
        openlibrary_data = raw_data.get("openlibrary", {})
        if openlibrary_data.get("cover_url"):
            cover_urls["openlibrary"] = openlibrary_data["cover_url"]
            
        dangdang_data = raw_data.get("dangdang", {})
        if dangdang_data.get("cover_url"):
            cover_urls["dangdang"] = dangdang_data["cover_url"]
            
        qidian_data = raw_data.get("qidian", {})
        if qidian_data.get("cover_url"):
            cover_urls["qidian"] = qidian_data["cover_url"]
            
        return await self.download_covers(book_id, cover_urls)
