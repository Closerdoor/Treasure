# -*- coding: utf-8 -*-
"""
作者头像下载器

从各数据源下载作者头像
"""
import asyncio
from pathlib import Path
from typing import Dict, Optional

from .base import BaseDownloader
from utils import Logger


class AvatarDownloader(BaseDownloader):
    """作者头像下载器"""
    
    def __init__(self, output_dir: Path = None):
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data" / "assets" / "people"
        super().__init__(output_dir)
        
    async def download_avatar(
        self,
        person_id: str,
        avatar_url: str,
        source: str = "unknown",
        filename: str = None,
    ) -> Optional[Path]:
        """
        下载作者头像
        
        Args:
            person_id: 人物 ID
            avatar_url: 头像 URL
            source: 数据来源
            
        Returns:
            保存路径
        """
        if not avatar_url:
            return None
            
        filename = filename or f"{person_id}-avatar.jpg"
        save_path = self.output_dir / filename
        
        referer = self._get_referer(source)
        
        if referer:
            return await self.download_with_referer(avatar_url, save_path, referer)
        else:
            return await self.download(avatar_url, save_path)
    
    def _get_referer(self, source: str) -> Optional[str]:
        """根据来源获取 Referer"""
        referer_map = {
            "openlibrary": "https://openlibrary.org/",
            "douban": "https://book.douban.com/",
            "wikipedia": "https://zh.wikipedia.org/",
        }
        return referer_map.get(source)
    
    async def download_from_person_data(
        self,
        person_id: str,
        person_data: Dict
    ) -> Optional[Path]:
        """
        从人物数据中下载头像
        
        Args:
            person_id: 人物 ID
            person_data: 人物数据（含 avatar_url, avatar_source）
            
        Returns:
            保存路径
        """
        avatar_url = person_data.get("avatar_url")
        source = person_data.get("avatar_source", "unknown")
        
        return await self.download_avatar(person_id, avatar_url, source)
