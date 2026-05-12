# -*- coding: utf-8 -*-
"""
当当网爬虫（书籍专用）
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


COOKIE_FILE = Path(__file__).parent.parent / "data" / "cookies" / "dangdang.json"


class DangdangCrawler:
    """当当网爬虫"""
    
    def __init__(self, page: Page = None):
        self.page = page
        self.base_url = "https://www.dangdang.com"
        self.context: BrowserContext = None
        
    async def init_with_cookies(self, browser) -> Page:
        """使用 Cookie 初始化"""
        if COOKIE_FILE.exists():
            cookies = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
            self.context = await browser.new_context()
            await self.context.add_cookies(cookies)
            self.page = await self.context.new_page()
            Logger.info("已加载当当网 Cookie")
        else:
            Logger.warning(f"当当网 Cookie 文件不存在: {COOKIE_FILE}")
            self.context = await browser.new_context()
            self.page = await self.context.new_page()
        
        return self.page
    
    async def search_by_isbn(self, isbn: str) -> Optional[str]:
        """
        通过 ISBN 搜索图书
        
        Args:
            isbn: ISBN 号
            
        Returns:
            图书页面 URL 或 None
        """
        Logger.info(f"正在当当网搜索 ISBN: {isbn}")
        
        search_url = f"https://search.dangdang.com/?key={isbn}&act=input"
        
        try:
            await self.page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 查找搜索结果
            result = soup.select_one(".shoplist li a")
            if result:
                href = result.get("href", "")
                if href:
                    # 处理相对协议 URL
                    if href.startswith("//"):
                        href = "https:" + href
                    Logger.success(f"找到当当网图书: {href}")
                    return href
            
            Logger.warning(f"当当网未找到 ISBN: {isbn}")
            return None
            
        except Exception as e:
            Logger.error(f"当当网搜索失败: {e}")
            return None
    
    async def search_by_title(self, title: str) -> Optional[str]:
        """
        通过书名搜索图书
        
        Args:
            title: 书名
            
        Returns:
            图书页面 URL 或 None
        """
        Logger.info(f"正在当当网搜索: {title}")
        
        search_url = f"https://search.dangdang.com/?key={quote(title)}&act=input"
        
        try:
            await self.page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 查找搜索结果
            results = soup.select(".shoplist li")
            for result in results:
                link = result.select_one("a")
                title_elem = result.select_one("a")
                
                if link and title_elem:
                    result_title = title_elem.get("title", "") or title_elem.text.strip()
                    # 简单匹配：书名在结果标题中
                    if title in result_title:
                        href = link.get("href", "")
                        if href:
                            # 处理相对协议 URL
                            if href.startswith("//"):
                                href = "https:" + href
                            Logger.success(f"找到当当网图书: {href}")
                            return href
            
            Logger.warning(f"当当网未找到: {title}")
            return None
            
        except Exception as e:
            Logger.error(f"当当网搜索失败: {e}")
            return None
    
    async def get_detail(self, url: str) -> Dict[str, Any]:
        """
        获取图书详情
        
        Args:
            url: 图书页面 URL
            
        Returns:
            图书数据
        """
        Logger.info(f"正在获取当当网详情: {url}")
        
        result = {
            "url": url,
            "source": "dangdang"
        }
        
        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 提取出版社（多种选择器）
            publisher_elem = (
                soup.select_one(".key a[dd_name='出版社']") or
                soup.select_one(".spc_info a[href*='pub_id']") or
                soup.select_one(".publisher_info a")
            )
            if publisher_elem:
                result["publisher"] = publisher_elem.text.strip()
            
            # 提取详细信息（遍历所有 .key 或 .spc_info 元素）
            info_items = soup.select(".key") or soup.select(".spc_info li")
            for item in info_items:
                text = item.text.strip()
                
                # ISBN
                if "ISBN" in text or "国际标准书号" in text:
                    isbn_match = re.search(r"[\d-]{10,}", text)
                    if isbn_match:
                        result["isbn"] = isbn_match.group().replace("-", "")
                
                # 页数
                if "页数" in text:
                    pages_match = re.search(r"(\d+)\s*页", text)
                    if pages_match:
                        result["pages"] = int(pages_match.group(1))
                
                # 装帧
                if "装帧" in text:
                    result["binding"] = text.replace("装帧", "").replace("：", "").strip()
                
                # 出版时间
                if "出版时间" in text or "出版日期" in text:
                    time_match = re.search(r"(\d{4})", text)
                    if time_match:
                        result["publish_year"] = int(time_match.group(1))
            
            # 提取价格
            price_elem = soup.select_one(".price_n") or soup.select_one(".price")
            if price_elem:
                price_text = price_elem.text.strip()
                price_match = re.search(r"[\d.]+", price_text)
                if price_match:
                    result["price"] = float(price_match.group())
            
            Logger.success("当当网数据获取完成")
            
        except Exception as e:
            Logger.error(f"当当网解析失败: {e}")
        
        return result
    
    async def close(self):
        """关闭"""
        if self.context:
            await self.context.close()
