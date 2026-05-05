# -*- coding: utf-8 -*-
"""
烂番茄爬虫
"""
import asyncio
import random
import re
from typing import Dict, Any, Optional, List
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.async_api import Page

import config
from utils import Logger


class RottenTomatoesCrawler:
    """烂番茄爬虫"""
    
    def __init__(self, page: Page):
        self.page = page
        self.base_url = config.ROTTEN_TOMATOES_BASE_URL
        
    async def search(self, title: str, year: int = 0) -> Optional[str]:
        """
        搜索电影
        
        Args:
            title: 电影标题
            year: 年份
            
        Returns:
            电影 URL 或 None
        """
        Logger.info(f"正在搜索烂番茄: {title}")
        
        # 搜索 URL
        search_url = f"{self.base_url}/search?search={quote(title)}"
        
        try:
            await self.page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 查找搜索结果
            results = soup.select(".search-page-media-row")
            if not results:
                results = soup.select("search-page-media-row")
            
            for result in results:
                try:
                    # 获取标题
                    title_elem = result.select_one("a")
                    if not title_elem:
                        continue
                    
                    result_title = title_elem.text.strip()
                    href = title_elem.get("href", "")
                    
                    # 检查年份是否匹配
                    year_elem = result.select_one(".start-year")
                    if year_elem:
                        result_year = year_elem.text.strip("()")
                        if year and result_year != str(year):
                            continue
                    
                    # 检查是否是电影
                    type_elem = result.select_one(".media-type")
                    if type_elem and "movie" not in type_elem.text.lower():
                        continue
                    
                    if href:
                        url = f"{self.base_url}{href}" if href.startswith("/") else href
                        Logger.success(f"找到烂番茄电影: {url}")
                        return url
                        
                except:
                    continue
            
            Logger.warning(f"烂番茄未找到电影: {title}")
            return None
            
        except Exception as e:
            Logger.error(f"烂番茄搜索失败: {e}")
            return None
            
    async def get_ratings(self, url: str) -> Dict[str, Any]:
        """
        获取评分
        
        Args:
            url: 电影 URL
            
        Returns:
            评分数据
        """
        Logger.info(f"正在获取烂番茄评分: {url}")
        
        result = {
            "url": url,
            "source": "rotten_tomatoes"
        }
        
        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # Tomatometer（影评人评分）
            tomatometer_elem = soup.select_one("score-board[data-qa='score-board']")
            if tomatometer_elem:
                tomatometer = tomatometer_elem.get("tomatometerscore", "")
                audience = tomatometer_elem.get("audiencescore", "")
                
                if tomatometer:
                    tomatometer_value = int(tomatometer)
                    result["tomatometer"] = {
                        "value": tomatometer_value / 10,
                        "scale": 10,
                        "raw": tomatometer_value
                    }
                
                if audience:
                    audience_value = int(audience)
                    result["audience_score"] = {
                        "value": audience_value / 10,
                        "scale": 10,
                        "raw": audience_value
                    }
            
            Logger.success(f"烂番茄评分获取完成")
            
        except Exception as e:
            Logger.error(f"烂番茄评分获取失败: {e}")
            
        return result
        
    async def get_reviews(self, url: str, count: int = 20) -> List[Dict]:
        """
        获取评论
        
        Args:
            url: 电影 URL
            count: 评论数量
            
        Returns:
            评论列表
        """
        Logger.info(f"正在获取烂番茄评论: {url}")
        
        reviews = []
        
        try:
            reviews_url = f"{url}/reviews?type=top"
            await self.page.goto(reviews_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            review_items = soup.select("review-card-critic")
            
            for item in review_items[:count]:
                try:
                    author = ""
                    author_elem = item.select_one("rt-link[slot='name']")
                    if author_elem:
                        author = author_elem.text.strip()
                    
                    publication = ""
                    pub_elem = item.select_one("rt-link[slot='publication']")
                    if pub_elem:
                        publication = pub_elem.text.strip()
                    
                    review_content = ""
                    content_elem = item.select_one("div[slot='review']")
                    if content_elem:
                        review_content = content_elem.text.strip()
                    
                    date = ""
                    date_elem = item.select_one("span[slot='timestamp']")
                    if date_elem:
                        date = date_elem.text.strip()
                    
                    source = f"Rotten Tomatoes · {publication}" if publication else "Rotten Tomatoes"
                    
                    reviews.append({
                        "author": author,
                        "source": source,
                        "date": date,
                        "content": review_content,
                        "url": reviews_url,
                        "title": None
                    })
                    
                except Exception as e:
                    continue
            
            Logger.success(f"获取烂番茄评论 {len(reviews)} 条")
            
        except Exception as e:
            Logger.error(f"烂番茄评论获取失败: {e}")
            
        return reviews
        
    async def crawl(self, title: str, year: int = 0, review_count: int = 20) -> Dict[str, Any]:
        """
        完整爬取流程
        
        Args:
            title: 电影标题（英文原名优先）
            year: 年份
            review_count: 评论数量
            
        Returns:
            完整数据
        """
        result = {
            "title": title,
            "source": "rotten_tomatoes"
        }
        
        url = await self.search(title, year)
        if url:
            ratings = await self.get_ratings(url)
            result["ratings"] = ratings
            
            reviews = await self.get_reviews(url, review_count)
            result["reviews"] = reviews
            
        return result