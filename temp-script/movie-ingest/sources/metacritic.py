# -*- coding: utf-8 -*-
"""
Metacritic 爬虫
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


class MetacriticCrawler:
    """Metacritic 爬虫"""
    
    def __init__(self, page: Page):
        self.page = page
        self.base_url = config.METACRITIC_BASE_URL
        
    async def search(self, title: str, original_title: str = "", year: int = 0) -> Optional[str]:
        """
        搜索电影
        
        Args:
            title: 电影标题（中文）
            original_title: 电影原名（英文）
            year: 年份
            
        Returns:
            电影 URL 或 None
        """
        # Metacritic 是英文站点，优先使用英文原名搜索
        search_title = original_title if original_title else title
        
        Logger.info(f"正在搜索 Metacritic: {search_title}")
        
        # 搜索 URL
        search_url = f"{self.base_url}/search/{quote(search_title)}/?page=1"
        
        try:
            await self.page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 查找搜索结果
            results = soup.select(".c-finderProductCard")
            if not results:
                results = soup.select(".search-result")
            
            for result in results:
                try:
                    # 获取标题
                    title_elem = result.select_one(".c-finderProductCard_title") or result.select_one("h3")
                    if not title_elem:
                        continue
                    
                    result_title = title_elem.text.strip()
                    
                    # 检查年份是否匹配
                    year_elem = result.select_one(".c-finderProductCard_meta span")
                    if year_elem:
                        year_text = year_elem.text.strip()
                        year_match = re.search(r"\d{4}", year_text)
                        if year_match and year and year_match.group() != str(year):
                            continue
                    
                    # 检查是否是电影
                    type_elem = result.select_one(".c-finderProductCard_subtitle")
                    if type_elem and "movie" not in type_elem.text.lower():
                        continue
                    
                    # 获取链接
                    link_elem = result.select_one("a")
                    if link_elem:
                        href = link_elem.get("href", "")
                        if href:
                            url = f"{self.base_url}{href}" if href.startswith("/") else href
                            Logger.success(f"找到 Metacritic 电影: {url}")
                            return url
                            
                except:
                    continue
            
            Logger.warning(f"Metacritic 未找到电影: {search_title}")
            return None
            
        except Exception as e:
            Logger.error(f"Metacritic 搜索失败: {e}")
            return None
            
    async def get_rating(self, url: str) -> Dict[str, Any]:
        """
        获取评分
        
        Args:
            url: 电影 URL
            
        Returns:
            评分数据
        """
        Logger.info(f"正在获取 Metacritic 评分: {url}")
        
        result = {
            "url": url,
            "source": "metacritic"
        }
        
        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # Metascore
            metascore_elem = soup.select_one(".c-siteReviewScore_background span") or soup.select_one(".metascore_w")
            if metascore_elem:
                metascore_text = metascore_elem.text.strip()
                metascore_match = re.search(r"\d+", metascore_text)
                if metascore_match:
                    metascore = int(metascore_match.group())
                    result["metascore"] = {
                        "value": metascore / 10,
                        "scale": 10,
                        "raw": metascore
                    }
            
            # 用户评分
            user_score_elem = soup.select_one(".c-siteReviewScore_user span") or soup.select_one(".userscore_w")
            if user_score_elem:
                user_score_text = user_score_elem.text.strip()
                user_score_match = re.search(r"[\d.]+", user_score_text)
                if user_score_match:
                    user_score = float(user_score_match.group())
                    result["user_score"] = {
                        "value": user_score,
                        "scale": 10
                    }
            
            Logger.success(f"Metacritic 评分获取完成")
            
        except Exception as e:
            Logger.error(f"Metacritic 评分获取失败: {e}")
            
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
        Logger.info(f"正在获取 Metacritic 评论: {url}")
        
        reviews = []
        
        try:
            # 访问评论页面
            reviews_url = f"{url}/critic-reviews"
            await self.page.goto(reviews_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 获取评论
            review_items = soup.select(".c-siteReview")
            if not review_items:
                review_items = soup.select(".review")
            
            for item in review_items[:count]:
                try:
                    # 评论人
                    author_elem = item.select_one(".c-siteReview_header .c-siteReview_author") or item.select_one(".author")
                    author = author_elem.text.strip() if author_elem else ""
                    
                    # 媒体
                    publication_elem = item.select_one(".c-siteReview_header .c-siteReview_source") or item.select_one(".source")
                    publication = publication_elem.text.strip() if publication_elem else ""
                    
                    # 评论内容
                    content_elem = item.select_one(".c-siteReview_quote") or item.select_one(".review-body")
                    review_content = content_elem.text.strip() if content_elem else ""
                    
                    # 时间
                    date_elem = item.select_one(".c-siteReview_header .c-siteReview_date") or item.select_one(".date")
                    date = date_elem.text.strip() if date_elem else ""
                    
                    # 来源标识
                    source = f"Metacritic · {publication}" if publication else "Metacritic"
                    
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
            
            Logger.success(f"获取 Metacritic 评论 {len(reviews)} 条")
            
        except Exception as e:
            Logger.error(f"Metacritic 评论获取失败: {e}")
            
        return reviews
        
    async def crawl(self, title: str, original_title: str = "", year: int = 0, review_count: int = 20) -> Dict[str, Any]:
        """
        完整爬取流程
        
        Args:
            title: 电影标题（中文）
            original_title: 电影原名（英文）
            year: 年份
            review_count: 评论数量
            
        Returns:
            完整数据
        """
        result = {
            "title": title,
            "source": "metacritic"
        }
        
        url = await self.search(title, original_title, year)
        if url:
            rating = await self.get_rating(url)
            result["rating"] = rating
            
            reviews = await self.get_reviews(url, review_count)
            result["reviews"] = reviews
            
        return result