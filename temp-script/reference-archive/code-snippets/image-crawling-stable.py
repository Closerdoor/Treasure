# -*- coding: utf-8 -*-
"""
稳定的图片爬取方案（来自 douban-top250）

关键改进：
1. 直接访问豆瓣图片页面（/photos?type=S）
2. 正确的选择器：.cover a
3. URL 转换：/m/ → /raw/
4. 类型判断：根据 class 属性判断 poster/still/screenshot

集成位置：movie-ingest/sources/douban.py 的 crawl_images() 方法
"""

import asyncio
import random
from bs4 import BeautifulSoup


async def crawl_images_stable(page, movie_id: str, min_delay: float = 2.0, max_delay: float = 5.0) -> list:
    """
    稳定的图片爬取方案
    
    Args:
        page: Playwright page 对象
        movie_id: 豆瓣电影 ID
        min_delay: 最小延迟（秒）
        max_delay: 最大延迟（秒）
    
    Returns:
        图片列表 [{"type": "poster", "thumb_url": "...", "origin_url": "...", "index": 1}, ...]
    """
    url = f"https://movie.douban.com/subject/{movie_id}/photos?type=S"
    
    try:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(min_delay, max_delay))
        
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        images = []
        items = soup.select(".cover a")  # 关键选择器
        
        for idx, item in enumerate(items):
            try:
                img_elem = item.select_one("img")
                if not img_elem:
                    continue
                
                thumb_url = img_elem.get("src", "")
                if not thumb_url:
                    continue
                
                # 关键转换：缩略图 → 原图
                origin_url = thumb_url.replace("/m/", "/raw/").replace("/s/", "/raw/")
                
                # 类型判断（关键逻辑）
                type_class = item.get("class", [])
                img_type = "other"
                for cls in type_class:
                    if "poster" in cls:
                        img_type = "poster"
                    elif "still" in cls:
                        img_type = "still"
                    elif "screenshot" in cls:
                        img_type = "screenshot"
                
                images.append({
                    "type": img_type,
                    "thumb_url": thumb_url,
                    "origin_url": origin_url,
                    "index": idx + 1
                })
                
            except Exception as e:
                print(f"解析图片失败: {e}")
                continue
        
        print(f"获取 {len(images)} 张图片")
        return images
        
    except Exception as e:
        print(f"爬取图片页面失败: {e}")
        return []


async def crawl_all_image_types(page, movie_id: str) -> dict:
    """
    爬取所有类型的图片（海报、剧照、截图）
    
    Args:
        page: Playwright page 对象
        movie_id: 豆瓣电影 ID
    
    Returns:
        {"posters": [...], "stills": [...], "screenshots": [...]}
    """
    result = {
        "posters": [],
        "stills": [],
        "screenshots": []
    }
    
    # 海报 (type=S)
    posters = await crawl_images_stable(page, movie_id)
    for img in posters:
        if img["type"] == "poster":
            result["posters"].append(img)
    
    await asyncio.sleep(random.uniform(2, 5))
    
    # 剧照 (type=T)
    stills_url = f"https://movie.douban.com/subject/{movie_id}/photos?type=T"
    await page.goto(stills_url, timeout=60000)
    await asyncio.sleep(random.uniform(2, 5))
    
    content = await page.content()
    soup = BeautifulSoup(content, "html.parser")
    items = soup.select(".cover a")
    
    for idx, item in enumerate(items):
        img_elem = item.select_one("img")
        if img_elem:
            thumb_url = img_elem.get("src", "")
            origin_url = thumb_url.replace("/m/", "/raw/")
            result["stills"].append({
                "type": "still",
                "thumb_url": thumb_url,
                "origin_url": origin_url,
                "index": idx + 1
            })
    
    return result


# 使用示例
if __name__ == "__main__":
    """
    集成到 movie-ingest/sources/douban.py:
    
    async def crawl_images(self, douban_id: str) -> Dict[str, Any]:
        from .image_crawling_stable import crawl_all_image_types
        
        images = await crawl_all_image_types(self.page, douban_id)
        
        return {
            "posters": images["posters"],
            "stills": images["stills"],
            "posters_total": len(images["posters"]),
            "stills_total": len(images["stills"])
        }
    """
    pass
