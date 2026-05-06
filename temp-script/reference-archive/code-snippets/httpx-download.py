# -*- coding: utf-8 -*-
"""
httpx 图片下载（来自 douban-top250）

优势：
1. 更现代的 HTTP 客户端
2. 支持 HTTP/2
3. 更简洁的 API
4. 更好的异步支持

集成位置：movie-ingest/downloader.py 替换 aiohttp
"""

import asyncio
from pathlib import Path
from typing import List, Dict
import httpx


async def download_image_httpx(url: str, output_path: str, timeout: int = 30) -> bool:
    """
    使用 httpx 下载单张图片
    
    Args:
        url: 图片 URL
        output_path: 输出路径
        timeout: 超时时间（秒）
    
    Returns:
        是否成功
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                Path(output_path).write_bytes(response.content)
                return True
            else:
                print(f"下载失败: HTTP {response.status_code}")
                return False
                
    except Exception as e:
        print(f"下载失败: {e}")
        return False


async def download_images_batch_httpx(images: List[Dict], output_dir: str, max_concurrency: int = 5):
    """
    批量下载图片（使用 httpx）
    
    Args:
        images: 图片列表 [{"url": "...", "type": "poster", "index": 1}, ...]
        output_dir: 输出目录
        max_concurrency: 最大并发数
    
    示例：
        images = [
            {"url": "https://example.com/poster1.jpg", "type": "poster", "index": 1},
            {"url": "https://example.com/still1.jpg", "type": "still", "index": 1}
        ]
        await download_images_batch_httpx(images, "images/0101000001")
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def download_one(img: Dict):
        async with semaphore:
            url = img["url"]
            img_type = img.get("type", "other")
            index = img.get("index", 0)
            
            # 生成文件名
            ext = ".jpg"
            if ".png" in url:
                ext = ".png"
            elif ".webp" in url:
                ext = ".webp"
            
            filename = f"{img_type}_{index:03d}{ext}"
            output_path = f"{output_dir}/{filename}"
            
            success = await download_image_httpx(url, output_path)
            
            if success:
                return filename
            return None
    
    # 并发下载
    tasks = [download_one(img) for img in images]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 统计结果
    downloaded = [r for r in results if isinstance(r, str)]
    print(f"下载完成: {len(downloaded)}/{len(images)} 张")
    
    return downloaded


async def download_images_with_retry(images: List[Dict], output_dir: str, max_retries: int = 3):
    """
    带重试的图片下载
    
    Args:
        images: 图片列表
        output_dir: 输出目录
        max_retries: 最大重试次数
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    failed = []
    
    async with httpx.AsyncClient(timeout=30) as client:
        for img in images:
            url = img["url"]
            filename = f"{img['type']}_{img['index']:03d}.jpg"
            output_path = f"{output_dir}/{filename}"
            
            # 重试逻辑
            for attempt in range(max_retries):
                try:
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        Path(output_path).write_bytes(response.content)
                        print(f"✓ {filename}")
                        break
                    else:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2)
                            continue
                        failed.append(img)
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    failed.append(img)
                    print(f"✗ {filename}: {e}")
    
    if failed:
        print(f"\n失败 {len(failed)} 张")
    
    return failed


# 对比：aiohttp vs httpx
"""
aiohttp 方式（当前 movie-ingest 使用）:

    async with aiohttp.ClientSession() as session:
        async with session.get(url, proxy=proxy) as response:
            content = await response.read()

httpx 方式（更简洁）:

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        content = response.content

优势：
1. 不需要手动管理 connector
2. 响应内容直接可用（response.content）
3. 更好的错误处理
4. 支持 HTTP/2
"""


# 使用示例
if __name__ == "__main__":
    """
    集成到 movie-ingest/downloader.py:
    
    将 aiohttp 替换为 httpx:
    
    async def _download_image(self, url: str, output_dir: Path, img_type: str, index: int):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, proxy=self.proxy if self.proxy else None)
            
            if response.status_code != 200:
                return None
            
            content = response.content
            
            # ... 后续处理相同
    """
    pass
