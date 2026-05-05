# -*- coding: utf-8 -*-
"""
Wikipedia 爬虫
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


class WikipediaCrawler:
    """Wikipedia 爬虫"""
    
    def __init__(self, page: Page):
        self.page = page
        self.base_url = config.WIKIPEDIA_BASE_URL
        
    async def search(self, title: str, original_title: str = "") -> Optional[str]:
        """
        搜索词条
        
        Args:
            title: 电影标题（中文）
            original_title: 电影原名（英文）
            
        Returns:
            词条 URL 或 None
        """
        Logger.info(f"正在搜索 Wikipedia: {title}")
        
        # 先尝试用中文名搜索
        encoded_title = quote(title)
        url = f"{self.base_url}/wiki/{encoded_title}"
        
        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            # 检查是否跳转到搜索页面
            current_url = self.page.url
            if "search" in current_url or "Special:" in current_url:
                # 在搜索结果中查找
                content = await self.page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # 查找第一个搜索结果
                first_result = soup.select_one(".mw-search-result-heading a")
                if first_result:
                    href = first_result.get("href", "")
                    if href:
                        url = f"{self.base_url}{href}" if href.startswith("/") else href
                        await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                else:
                    Logger.warning(f"Wikipedia 未找到词条: {title}")
                    return None
            
            Logger.success(f"找到 Wikipedia 词条: {url}")
            return url
            
        except Exception as e:
            Logger.error(f"Wikipedia 搜索失败: {e}")
            return None
            
    async def get_detail(self, url: str) -> Dict[str, Any]:
        """
        获取词条内容
        
        Args:
            url: 词条 URL
            
        Returns:
            词条数据
        """
        Logger.info(f"正在获取 Wikipedia 内容: {url}")
        
        result = {
            "url": url,
            "source": "wikipedia"
        }
        
        try:
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 词条名
            title_elem = soup.select_one("#firstHeading") or soup.select_one("h1")
            title_text = title_elem.text.strip() if title_elem else ""
            # 去除"[编辑]"等后缀
            title_text = re.sub(r'\[编辑\]$', '', title_text)
            result["title"] = title_text
            
            # 词条 ID（从 URL 提取）
            match = re.search(r"/wiki/(.+)$", url)
            if match:
                # URL 解码
                from urllib.parse import unquote
                wiki_id = unquote(match.group(1))
                result["wikipedia_id"] = wiki_id
            
            # 摘要（第一段）
            first_para = soup.select_one("#mw-content-text p")
            result["summary"] = first_para.text.strip() if first_para else ""
            
            # 信息框
            infobox = soup.select_one(".infobox") or soup.select_one(".vevent")
            if infobox:
                rows = infobox.select("tr")
                for row in rows:
                    try:
                        th = row.select_one("th")
                        td = row.select_one("td")
                        if th and td:
                            key = th.text.strip()
                            value = td.text.strip()
                            result[key] = value
                    except:
                        continue
            
            # 获奖（查找获奖段落）
            awards = []
            award_heading = soup.find(string=re.compile("获奖|奖项|荣誉"))
            if award_heading:
                award_section = award_heading.find_parent(["h2", "h3"])
                if award_section:
                    next_elem = award_section.find_next_sibling()
                    while next_elem and next_elem.name not in ["h2", "h3"]:
                        if next_elem.name == "ul":
                            for li in next_elem.select("li"):
                                awards.append(li.text.strip())
                        next_elem = next_elem.find_next_sibling()
            result["awards"] = awards
            
            # 名言名句（查找引言段落）
            quotes = []
            quote_elems = soup.select("blockquote")
            for quote_elem in quote_elems:
                quote_text = quote_elem.text.strip()
                if quote_text:
                    quotes.append({
                        "text": quote_text,
                        "source": "wikipedia"
                    })
            result["quotes"] = quotes
            
            Logger.success(f"Wikipedia 内容获取完成")
            
        except Exception as e:
            Logger.error(f"Wikipedia 内容获取失败: {e}")
            
        return result
        
    async def crawl(self, title: str, original_title: str = "") -> Dict[str, Any]:
        """
        完整爬取流程
        
        Args:
            title: 电影标题（中文）
            original_title: 电影原名（英文）
            
        Returns:
            完整数据
        """
        result = {
            "title": title,
            "source": "wikipedia"
        }
        
        url = await self.search(title, original_title)
        if url:
            result = await self.get_detail(url)
            
        return result