# -*- coding: utf-8 -*-
"""
图片下载模块
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


class ImageDownloader:
    """图片下载器"""
    
    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.downloaded_hashes: Set[str] = set()
        self.concurrency = config.IMAGE_DOWNLOAD_CONCURRENCY
        self.timeout = config.IMAGE_TIMEOUT
        self.proxy = config.PROXY_URL if config.PROXY_ENABLED else None
        self.headers = {
            "Referer": "https://movie.douban.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
    async def download_all(self, work_id: str, images_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        下载所有图片
        
        Args:
            work_id: 作品 ID
            images_data: 图片数据
            
        Returns:
            下载结果
        """
        Logger.info(f"正在下载图片: {work_id}")
        
        images_dir = self.output_dir / work_id / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        result = {
            "posters": [],
            "stills": []
        }
        
        # 收集所有图片 URL
        all_images = []
        
        # 豆瓣主海报（优先）
        douban_images = images_data.get("douban", {})
        main_poster_url = douban_images.get("main_poster_url", "")
        if main_poster_url:
            all_images.append({
                "url": main_poster_url,
                "type": "poster",
                "priority": 1  # 最高优先级
            })
        
        # 豆瓣图片列表
        for img in douban_images.get("posters", []):
            all_images.append({
                "url": img.get("origin_url", ""),
                "type": "poster",
                "priority": 2
            })
        for img in douban_images.get("stills", []):
            all_images.append({
                "url": img.get("origin_url", ""),
                "type": "still",
                "priority": 2
            })
        
        # TMDB 图片
        tmdb_images = images_data.get("tmdb", {})
        for img in tmdb_images.get("posters", []):
            all_images.append({
                "url": img.get("url", ""),
                "type": "poster",
                "priority": 3
            })
        for img in tmdb_images.get("backdrops", []):
            all_images.append({
                "url": img.get("url", ""),
                "type": "still",
                "priority": 3
            })
        
        # OMDb/IMDb 海报
        omdb_images = images_data.get("omdb", {})
        omdb_poster = omdb_images.get("poster", "")
        if omdb_poster and "media-amazon" in omdb_poster:
            # 转换为原图 URL（去掉尺寸限制）
            original_url = omdb_poster.replace("_V1_SX300.jpg", "_V1.jpg").replace("_V1_SX200.jpg", "_V1.jpg")
            all_images.append({
                "url": original_url,
                "type": "poster",
                "priority": 4
            })
        
        # 去重
        unique_images = []
        seen_urls = set()
        for img in all_images:
            url = img.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_images.append(img)
        
        # 按优先级排序（优先级高的先下载）
        unique_images.sort(key=lambda x: x.get("priority", 5))
        
        # 下载图片
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async def download_one(img_data: Dict, index: int) -> Optional[str]:
            async with semaphore:
                return await self._download_image(
                    img_data["url"],
                    images_dir,
                    img_data["type"],
                    index
                )
        
        tasks = []
        for idx, img in enumerate(unique_images):
            tasks.append(download_one(img, idx + 1))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理结果
        poster_idx = 1
        still_idx = 1
        
        for i, res in enumerate(results):
            if isinstance(res, str) and res:
                # 根据文件名判断类型（而不是原始类型）
                if res.startswith("poster"):
                    result["posters"].append(res)
                    poster_idx += 1
                else:
                    result["stills"].append(res)
                    still_idx += 1
        
        Logger.success(f"下载完成: 海报 {len(result['posters'])} 张，剧照 {len(result['stills'])} 张")
        return result
        
    async def _download_image(
        self,
        url: str,
        output_dir: Path,
        img_type: str,
        index: int
    ) -> Optional[str]:
        """
        下载单张图片
        
        Args:
            url: 图片 URL
            output_dir: 输出目录
            img_type: 图片类型
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
                    
                    # 计算哈希去重
                    content_hash = hashlib.md5(content).hexdigest()
                    if content_hash in self.downloaded_hashes:
                        return None
                    self.downloaded_hashes.add(content_hash)
                    
                    # 确定文件扩展名
                    ext = ".jpg"
                    content_type = response.headers.get("Content-Type", "")
                    if "png" in content_type:
                        ext = ".png"
                    elif "webp" in content_type:
                        ext = ".webp"
                    
                    # 根据图片比例确定类型
                    actual_type = self._classify_image(content)
                    
                    # 生成文件名（第一张海报命名为 poster-main）
                    if actual_type == "poster" and index == 1:
                        filename = f"poster-main{ext}"
                    elif actual_type == "poster":
                        filename = f"poster-{index:03d}{ext}"
                    else:
                        filename = f"still-{index:03d}{ext}"
                    
                    # 保存文件
                    filepath = output_dir / filename
                    filepath.write_bytes(content)
                    
                    return filename
                    
        except Exception as e:
            Logger.warning(f"下载图片失败: {url[:50]}... - {e}")
            return None
            
    def _classify_image(self, content: bytes) -> str:
        """
        根据图片内容判断类型
        
        Args:
            content: 图片内容
            
        Returns:
            图片类型（poster 或 still）
        """
        try:
            img = Image.open(io.BytesIO(content))
            width, height = img.size
            
            # 计算宽高比
            ratio = width / height
            
            # 海报通常是竖版（比例约 2:3，即 0.6-0.8）
            # 剧照通常是横版（比例约 16:9 或 4:3，即 1.2-1.8）
            if config.POSTER_RATIO_MIN <= ratio <= config.POSTER_RATIO_MAX:
                return "poster"
            else:
                return "still"
                
        except Exception as e:
            return "poster"  # 默认为海报
            
    async def download_poster(self, url: str, work_id: str) -> Optional[str]:
        """
        下载主海报
        
        Args:
            url: 图片 URL
            work_id: 作品 ID
            
        Returns:
            文件名或 None
        """
        images_dir = self.output_dir / work_id / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    content = await response.read()
                    
                    # 计算哈希去重
                    content_hash = hashlib.md5(content).hexdigest()
                    if content_hash in self.downloaded_hashes:
                        return None
                    self.downloaded_hashes.add(content_hash)
                    
                    # 保存文件
                    filename = "poster-main.jpg"
                    filepath = images_dir / filename
                    filepath.write_bytes(content)
                    
                    return filename
                    
        except Exception as e:
            Logger.warning(f"下载主海报失败: {e}")
            return None
            
    async def download_profile(self, url: str, person_code: str, work_id: str) -> Optional[str]:
        """
        下载人物头像
        
        Args:
            url: 图片 URL
            person_code: 人物编码
            work_id: 作品 ID
            
        Returns:
            文件名或 None
        """
        images_dir = self.output_dir / work_id / "images" / "people"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    content = await response.read()
                    
                    # 计算哈希去重
                    content_hash = hashlib.md5(content).hexdigest()
                    if content_hash in self.downloaded_hashes:
                        return None
                    self.downloaded_hashes.add(content_hash)
                    
                    # 保存文件
                    filename = f"{person_code}-avatar.jpg"
                    filepath = images_dir / filename
                    filepath.write_bytes(content)
                    
                    return filename
                    
        except Exception as e:
            Logger.warning(f"下载人物头像失败: {e}")
            return None
    
    async def download(self, url: str, output_path: str) -> bool:
        """
        下载单张图片到指定路径
        
        Args:
            url: 图片 URL
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                connector=connector,
                headers=self.headers
            ) as session:
                async with session.get(url, proxy=self.proxy) as response:
                    if response.status != 200:
                        return False
                    
                    content = await response.read()
                    
                    # 保存文件
                    Path(output_path).write_bytes(content)
                    
                    return True
                    
        except Exception as e:
            Logger.warning(f"下载图片失败: {url[:50]}... - {e}")
            return False