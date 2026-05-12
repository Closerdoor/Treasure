# -*- coding: utf-8 -*-
"""
起点中文网爬虫（网络小说专用）
"""
import asyncio
import json
import random
import re
from typing import Dict, Any, Optional
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.async_api import Page, BrowserContext

import config
from utils import Logger


COOKIE_FILE = Path(__file__).parent.parent / "data" / "cookies" / "qidian.json"


class QidianCrawler:
    """起点中文网爬虫"""
    
    def __init__(self, page: Page = None):
        self.page = page
        self.base_url = "https://www.qidian.com"
        self.context: BrowserContext = None
        
    async def init_with_cookies(self, browser) -> Page:
        """使用 Cookie 初始化"""
        if COOKIE_FILE.exists():
            cookies = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
            self.context = await browser.new_context()
            await self.context.add_cookies(cookies)
            self.page = await self.context.new_page()
            Logger.info("已加载起点中文网 Cookie")
        else:
            Logger.warning(f"起点中文网 Cookie 文件不存在: {COOKIE_FILE}")
            self.context = await browser.new_context()
            self.page = await self.context.new_page()
        
        return self.page
    
    async def search(self, title: str, author: str = "") -> Optional[str]:
        """
        搜索小说
        
        Args:
            title: 小说名
            author: 作者名（可选，用于精确匹配）
            
        Returns:
            小说页面 URL 或 None
        """
        Logger.info(f"正在起点中文网搜索: {title}")
        
        search_url = f"https://www.qidian.com/so/{quote(title)}.html"
        
        try:
            await self.page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 查找搜索结果
            results = soup.select(".book-img-text ul li")
            
            for result in results:
                title_elem = result.select_one(".book-mid-info h4 a")
                author_elem = result.select_one(".book-mid-info .author a.name")
                
                if title_elem:
                    result_title = title_elem.text.strip()
                    result_author = author_elem.text.strip() if author_elem else ""
                    
                    # 匹配书名
                    if title in result_title or result_title in title:
                        # 如果有作者名，也匹配作者
                        if author and author not in result_author:
                            continue
                        
                        href = title_elem.get("href", "")
                        if href:
                            if href.startswith("//"):
                                href = "https:" + href
                            Logger.success(f"找到起点中文网小说: {href}")
                            return href
            
            Logger.warning(f"起点中文网未找到: {title}")
            return None
            
        except Exception as e:
            Logger.error(f"起点中文网搜索失败: {e}")
            return None
    
    async def get_detail(self, url: str) -> Dict[str, Any]:
        """
        获取小说详情
        
        Args:
            url: 小说页面 URL
            
        Returns:
            小说数据
        """
        Logger.info(f"正在获取起点中文网详情: {url}")
        
        result = {
            "url": url,
            "source": "qidian"
        }
        
        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 提取书名
            title_elem = soup.select_one(".book-info h1 em")
            if title_elem:
                result["title"] = title_elem.text.strip()
            
            # 提取作者
            author_elem = soup.select_one(".book-info .writer")
            if author_elem:
                result["author"] = author_elem.text.replace("作者:", "").strip()
            
            # 提取连载状态
            status_elem = soup.select_one(".book-info .tag")
            if status_elem:
                result["status"] = status_elem.text.strip()
            
            # 提取字数
            word_elem = soup.select_one(".book-info .total-count em")
            if word_elem:
                word_text = word_elem.text.strip()
                # 格式: "123.45万字"
                word_match = re.match(r"([\d.]+)\s*万", word_text)
                if word_match:
                    result["word_count"] = int(float(word_match.group(1)) * 10000)
            
            # 提取分类
            category_elem = soup.select_one(".book-info .type")
            if category_elem:
                result["category"] = category_elem.text.strip()
            
            # 提取简介
            intro_elem = soup.select_one(".book-info .intro")
            if intro_elem:
                result["summary"] = intro_elem.text.strip()
            
            # 提取封面
            cover_elem = soup.select_one(".book-img a img")
            if cover_elem:
                result["cover_url"] = cover_elem.get("src", "")
            
            # 连载平台
            result["platform"] = "起点中文网"
            
            Logger.success("起点中文网数据获取完成")
            
        except Exception as e:
            Logger.error(f"起点中文网解析失败: {e}")
        
        return result
    
    async def close(self):
        """关闭"""
        if self.context:
            await self.context.close()
