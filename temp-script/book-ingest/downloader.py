# -*- coding: utf-8 -*-
"""
封面下载模块
"""
import asyncio
import aiohttp
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from PIL import Image
import io

import config
from utils import Logger


class CoverDownloader:
    """封面下载器"""
    
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = Path(__file__).parent / "data"
        self.output_dir = Path(output_dir)
        self.downloaded_hashes: Set[str] = set()
        self.concurrency = config.IMAGE_DOWNLOAD_CONCURRENCY
        self.timeout = config.IMAGE_TIMEOUT
        self.proxy = config.PROXY_URL if config.PROXY_ENABLED else None
        self.headers = {
            "Referer": "https://book.douban.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
    async def download_all(self, book_id: str, images_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        下载所有封面
        
        Args:
            book_id: 书籍 ID
            images_data: 图片数据
            
        Returns:
            下载结果
        """
        Logger.info(f"正在下载封面: {book_id}")
        
        images_dir = self.output_dir / book_id / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        result = {
            "covers": []
        }
        
        all_images = []
        
        # 豆瓣主封面
        douban_images = images_data.get("douban", {})
        main_cover_url = douban_images.get("main_cover_url", "")
        if main_cover_url:
            all_images.append({
                "url": main_cover_url,
                "priority": 1
            })
        
        # OpenLibrary 封面
        openlibrary_images = images_data.get("openlibrary", {})
        cover_urls = openlibrary_images.get("cover_urls", [])
        for url in cover_urls[:3]:
            all_images.append({
                "url": url,
                "priority": 2
            })
        
        # 去重
        unique_images = []
        seen_urls = set()
        for img in all_images:
            url = img.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_images.append(img)
        
        unique_images.sort(key=lambda x: x.get("priority", 3))
        
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async def download_one(img_data: Dict, index: int) -> Optional[str]:
            async with semaphore:
                return await self._download_image(
                    img_data["url"],
                    images_dir,
                    index
                )
        
        tasks = []
        for idx, img in enumerate(unique_images):
            tasks.append(download_one(img, idx + 1))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        cover_idx = 1
        for i, res in enumerate(results):
            if isinstance(res, str) and res:
                result["covers"].append(res)
                cover_idx += 1
        
        Logger.success(f"下载完成: 封面 {len(result['covers'])} 张")
        return result
        
    async def _download_image(
        self,
        url: str,
        output_dir: Path,
        index: int
    ) -> Optional[str]:
        """
        下载单张封面
        
        Args:
            url: 图片 URL
            output_dir: 输出目录
            index: 索引
            
        Returns:
            文件名或 None
        """
        if not url:
            return None
            
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                connector=connector,
                headers=self.headers
            ) as session:
                async with session.get(url, proxy=self.proxy) as response:
                    if response.status != 200:
                        return None
                    
                    content = await response.read()
                    
                    content_hash = hashlib.md5(content).hexdigest()
                    if content_hash in self.downloaded_hashes:
                        return None
                    self.downloaded_hashes.add(content_hash)
                    
                    ext = ".jpg"
                    content_type = response.headers.get("Content-Type", "")
                    if "png" in content_type:
                        ext = ".png"
                    elif "webp" in content_type:
                        ext = ".webp"
                    
                    if index == 1:
                        filename = f"cover-main{ext}"
                    else:
                        filename = f"cover-{index:03d}{ext}"
                    
                    filepath = output_dir / filename
                    filepath.write_bytes(content)
                    
                    return filename
                    
        except Exception as e:
            Logger.warning(f"下载封面失败: {url[:50]}... - {e}")
            return None
