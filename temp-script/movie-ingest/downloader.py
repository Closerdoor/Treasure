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
        
    async def download_all(self, work_id: str, images_data: Dict[str, Any]) -> Dict[str, Any]:
        """下载作品图片；封面主图按数据源单独保存到 cover/。"""
        Logger.info(f"正在下载图片: {work_id}")

        images_dir = self.output_dir / work_id / "images"
        cover_dir = self.output_dir / work_id / "cover"
        images_dir.mkdir(parents=True, exist_ok=True)
        cover_dir.mkdir(parents=True, exist_ok=True)

        result = {"covers": {}, "posters": [], "stills": [], "wallpapers": []}
        cover_images = []
        all_images = []

        douban_images = images_data.get("douban", {})
        if douban_images.get("main_poster_url"):
            cover_images.append({"url": douban_images["main_poster_url"], "source": "douban", "priority": 1})

        for img in douban_images.get("posters", []):
            all_images.append({"url": img.get("origin_url", ""), "type": "poster", "priority": 2})
        for img in douban_images.get("stills", []):
            all_images.append({"url": img.get("origin_url", ""), "type": "still", "priority": 2})
        for img in douban_images.get("wallpapers", []):
            all_images.append({"url": img.get("origin_url", ""), "type": "wallpaper", "priority": 2})

        tmdb_images = images_data.get("tmdb", {})
        if tmdb_images.get("main_poster_url"):
            cover_images.append({"url": tmdb_images["main_poster_url"], "source": "tmdb", "priority": 2})
        for img in tmdb_images.get("posters", []):
            all_images.append({"url": img.get("url", ""), "type": "poster", "priority": 3})
        for img in tmdb_images.get("backdrops", []):
            all_images.append({"url": img.get("url", ""), "type": "still", "priority": 3})

        omdb_poster = images_data.get("omdb", {}).get("poster", "")
        if omdb_poster:
            cover_images.append({"url": self._normalize_omdb_poster_url(omdb_poster), "source": "omdb", "priority": 3})

        rt_poster = images_data.get("rotten_tomatoes", {}).get("poster", "")
        if rt_poster:
            cover_images.append({"url": rt_poster, "source": "rottenTomatoes", "priority": 4})

        unique_images = []
        seen_urls = set()
        for img in all_images:
            url = img.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_images.append(img)

        cover_images.sort(key=lambda x: x.get("priority", 5))
        unique_images.sort(key=lambda x: x.get("priority", 5))

        semaphore = asyncio.Semaphore(self.concurrency)
        connector = aiohttp.TCPConnector(ssl=False, limit=max(self.concurrency * 2, 20))
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            connector=connector,
            headers=self.headers
        ) as session:
            async def download_cover(img_data: Dict) -> tuple:
                async with semaphore:
                    filename = await self._download_cover_image(
                        img_data["url"],
                        cover_dir,
                        img_data["source"],
                        session=session
                    )
                    return img_data["source"], filename

            async def download_one(img_data: Dict, index: int) -> Optional[str]:
                async with semaphore:
                    return await self._download_image(
                        img_data["url"],
                        images_dir,
                        img_data["type"],
                        index,
                        session=session
                    )

            cover_tasks = [download_cover(img) for img in cover_images]
            image_tasks = [download_one(img, idx + 1) for idx, img in enumerate(unique_images)]
            cover_results = await asyncio.gather(*cover_tasks, return_exceptions=True) if cover_tasks else []
            image_results = await asyncio.gather(*image_tasks, return_exceptions=True) if image_tasks else []

        for res in cover_results:
            if isinstance(res, tuple) and res[1]:
                result["covers"][res[0]] = f"cover/{res[1]}"

        for res in image_results:
            if isinstance(res, str) and res:
                if res.startswith("poster"):
                    result["posters"].append(res)
                elif res.startswith("wallpaper"):
                    result["wallpapers"].append(res)
                else:
                    result["stills"].append(res)

        Logger.success(
            f"下载完成: 封面 {len(result['covers'])} 张，"
            f"海报 {len(result['posters'])} 张，"
            f"剧照 {len(result['stills'])} 张，"
            f"壁纸 {len(result['wallpapers'])} 张"
        )
        return result

    def _normalize_omdb_poster_url(self, url: str) -> str:
        return url.replace("_V1_SX300.jpg", "_V1.jpg").replace("_V1_SX200.jpg", "_V1.jpg")

    async def _download_cover_image(
        self,
        url: str,
        output_dir: Path,
        source: str,
        session: aiohttp.ClientSession
    ) -> Optional[str]:
        if not url:
            return None

        filename_source = {
            "douban": "douban-main",
            "tmdb": "tmdb-main",
            "omdb": "omdb-main",
            "rottenTomatoes": "rotten-tomatoes-main",
        }.get(source, f"{source}-main")

        try:
            async with session.get(url, proxy=self.proxy) as response:
                if response.status != 200:
                    return None

                content = await response.read()
                ext = ".jpg"
                content_type = response.headers.get("Content-Type", "")
                if "png" in content_type:
                    ext = ".png"
                elif "webp" in content_type:
                    ext = ".webp"

                filename = f"{filename_source}{ext}"
                (output_dir / filename).write_bytes(content)
                return filename
        except Exception as e:
            Logger.warning(f"下载封面主图失败: {source} {url[:50]}... - {e}")
            return None

    async def download_video_thumbnails(self, work_id: str, videos: List[Dict[str, Any]]) -> Dict[str, str]:
        """并行下载视频封面，返回原 thumbnail URL 到本地文件名的映射。"""
        images_dir = self.output_dir / work_id / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        thumbnail_urls = []
        seen_urls = set()
        for video in videos or []:
            url = video.get("thumbnail") if isinstance(video, dict) else None
            if not url or not str(url).startswith(("http://", "https://")) or url in seen_urls:
                continue
            seen_urls.add(url)
            thumbnail_urls.append(url)

        if not thumbnail_urls:
            return {}

        Logger.info(f"正在并行下载视频封面: {len(thumbnail_urls)} 张")
        semaphore = asyncio.Semaphore(self.concurrency)
        connector = aiohttp.TCPConnector(ssl=False, limit=max(self.concurrency * 2, 20))
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            connector=connector,
            headers=self.headers
        ) as session:
            async def download_one(url: str, index: int):
                async with semaphore:
                    filename = await self._download_video_thumbnail(url, images_dir, index, session)
                    return url, filename

            tasks = [download_one(url, idx + 1) for idx, url in enumerate(thumbnail_urls)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        mapping = {}
        for result in results:
            if isinstance(result, tuple) and result[1]:
                mapping[result[0]] = result[1]

        Logger.success(f"视频封面下载完成: {len(mapping)}/{len(thumbnail_urls)} 张")
        return mapping

    async def _download_video_thumbnail(
        self,
        url: str,
        output_dir: Path,
        index: int,
        session: aiohttp.ClientSession
    ) -> Optional[str]:
        candidates = [url]
        if "img.youtube.com" in url and "maxresdefault" in url:
            candidates.append(url.replace("maxresdefault", "hqdefault"))

        for candidate_url in candidates:
            try:
                async with session.get(candidate_url, proxy=self.proxy) as response:
                    if response.status != 200:
                        continue

                    content = await response.read()
                    content_type = response.headers.get("Content-Type", "")
                    ext = ".jpg"
                    if "png" in content_type:
                        ext = ".png"
                    elif "webp" in content_type:
                        ext = ".webp"

                    filename = f"video-{index:03d}{ext}"
                    (output_dir / filename).write_bytes(content)
                    return filename
            except Exception as e:
                Logger.warning(f"下载视频封面失败: {candidate_url[:50]}... - {e}")

        return None
        
    async def _download_image(
        self,
        url: str,
        output_dir: Path,
        img_type: str,
        index: int,
        session: aiohttp.ClientSession = None
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
            if session is None:
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    connector=connector,
                    headers=self.headers
                ) as session:
                    return await self._download_image(
                        url,
                        output_dir,
                        img_type,
                        index,
                        session=session
                    )

            if session:
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
                    actual_type = "wallpaper" if img_type == "wallpaper" else self._classify_image(content)
                    
                    # 封面主图统一由 _download_cover_image 保存到 cover/；
                    # 普通海报图库只使用编号文件名，避免混出 poster-main。
                    if actual_type == "poster":
                        filename = f"poster-{index:03d}{ext}"
                    elif actual_type == "wallpaper":
                        filename = f"wallpaper-{index:03d}{ext}"
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
            
    async def download_profiles(self, work_id: str, people: List[Dict[str, Any]]) -> Dict[str, str]:
        """并行下载演职员头像，返回 {person_code: relative_path}。"""
        images_dir = self.output_dir / work_id / "images" / "people"
        images_dir.mkdir(parents=True, exist_ok=True)

        targets = []
        seen_codes = set()
        for person in people:
            avatar = person.get("avatar")
            person_code = self._person_code(person)
            if not avatar or not person_code or person_code in seen_codes:
                continue
            seen_codes.add(person_code)
            targets.append({"url": avatar, "person_code": person_code})

        if not targets:
            return {}

        Logger.info(f"正在并行下载演职员头像: {len(targets)} 张，并发 {self.concurrency}")
        semaphore = asyncio.Semaphore(self.concurrency)
        connector = aiohttp.TCPConnector(ssl=False, limit=max(self.concurrency * 2, 20))
        result = {}

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            connector=connector,
            headers=self.headers
        ) as session:
            async def download_one(item: Dict[str, str]) -> Optional[tuple]:
                async with semaphore:
                    filename = await self._download_profile_image(
                        item["url"],
                        item["person_code"],
                        images_dir,
                        session
                    )
                    if not filename:
                        return None
                    return item["person_code"], f"people/{filename}"

            downloaded = await asyncio.gather(
                *(download_one(item) for item in targets),
                return_exceptions=True
            )

        for item in downloaded:
            if isinstance(item, tuple):
                result[item[0]] = item[1]

        Logger.success(f"演职员头像下载完成: {len(result)}/{len(targets)} 张")
        return result

    def _person_code(self, person: Dict[str, Any]) -> Optional[str]:
        if person.get("tmdbId"):
            return f"tmdb-{person.get('tmdbId')}"
        if person.get("doubanId"):
            return f"p{person.get('doubanId')}"
        return None

    async def _download_profile_image(
        self,
        url: str,
        person_code: str,
        output_dir: Path,
        session: aiohttp.ClientSession
    ) -> Optional[str]:
        try:
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

                filename = f"{person_code}-avatar{ext}"
                (output_dir / filename).write_bytes(content)
                return filename
        except Exception as e:
            Logger.warning(f"下载演职员头像失败: {url[:50]}... - {e}")
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
