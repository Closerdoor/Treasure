# -*- coding: utf-8 -*-
"""
中国图书网爬虫模块
"""
import asyncio
import random
import re
from typing import Optional, List, Dict, Any

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

import config
from utils import Logger


class BookChinaCrawler:
    """中国图书网爬虫"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    async def init_browser(self):
        """初始化浏览器"""
        Logger.info("正在启动中国图书网浏览器...")
        self.playwright = await async_playwright().start()
        
        try:
            launch_options = {
                "headless": config.HEADLESS,
                "slow_mo": config.SLOW_MO
            }
            
            if config.USE_CHROME and hasattr(config, 'CHROME_PATH'):
                launch_options["executable_path"] = config.CHROME_PATH
            
            self.browser = await self.playwright.chromium.launch(**launch_options)
        except Exception as e:
            Logger.error(f"浏览器启动失败: {e}")
            raise
        
        user_agent = random.choice(config.USER_AGENTS)
        
        context_options = {
            "user_agent": user_agent,
            "viewport": {"width": 1920, "height": 1080}
        }
        
        if config.PROXY_ENABLED and config.PROXY_URL:
            context_options["proxy"] = {"server": config.PROXY_URL}
        
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
        Logger.info("中国图书网浏览器已启动")
        
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def search(self, keyword: str) -> Optional[str]:
        """
        搜索书籍
        
        Args:
            keyword: 搜索关键词（ISBN 或书名）
            
        Returns:
            中国图书网书籍 URL 或 None
        """
        url = f"{config.BOOKCHINA_BASE_URL}/search.aspx?keyword={keyword}"
        
        try:
            Logger.info(f"中国图书网搜索: {keyword}")
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            first_result = soup.select_one("a.bookname") or soup.select_one("div.book-item a")
            if first_result:
                book_url = first_result.get("href", "")
                if book_url and not book_url.startswith("http"):
                    book_url = config.BOOKCHINA_BASE_URL + book_url
                Logger.success(f"中国图书网找到书籍: {book_url}")
                return book_url
            
            Logger.warning(f"中国图书网未找到: {keyword}")
            return None
            
        except Exception as e:
            Logger.error(f"中国图书网搜索失败: {e}")
            return None
            
    async def crawl_detail(self, book_url: str) -> Dict[str, Any]:
        """
        爬取书籍详情
        
        Args:
            book_url: 中国图书网书籍 URL
            
        Returns:
            书籍详情数据
        """
        result = {
            "source": "bookchina",
            "url": book_url
        }
        
        try:
            Logger.info(f"正在爬取中国图书网详情: {book_url}")
            await self.page.goto(book_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            book_id_match = re.search(r'/(\d+)\.html', book_url) or re.search(r'id=(\d+)', book_url)
            if book_id_match:
                result["bookchina_id"] = book_id_match.group(1)
            
            title_elem = soup.select_one("h1.book-title") or soup.select_one("div.book-info h1")
            result["title"] = title_elem.text.strip() if title_elem else ""
            
            authors = []
            author_elem = soup.select_one("div.author") or soup.select_one("span.author")
            if author_elem:
                author_text = author_elem.text.strip()
                author_text = author_text.replace("作者:", "").replace("作者：", "")
                for name in author_text.split("/"):
                    name = name.strip()
                    if name and name not in authors:
                        authors.append(name)
            result["authors"] = authors
            
            publisher_elem = soup.select_one("div.publisher a") or soup.select_one("span.publisher")
            result["publisher"] = publisher_elem.text.strip() if publisher_elem else ""
            
            price_elem = soup.select_one("span.price") or soup.select_one("div.price")
            if price_elem:
                price_text = price_elem.text.strip()
                price_match = re.search(r'[\d.]+', price_text)
                result["price"] = float(price_match.group(0)) if price_match else None
            
            detail_table = soup.select_one("table.book-detail") or soup.select_one("div.detail-table")
            if detail_table:
                rows = detail_table.select("tr")
                for row in rows:
                    cells = row.select("td")
                    if len(cells) >= 2:
                        label = cells[0].text.strip()
                        value = cells[1].text.strip()
                        
                        if "字数" in label:
                            word_match = re.search(r'(\d+)', value)
                            result["word_count"] = int(word_match.group(1)) if word_match else None
                            
                        elif "页数" in label:
                            pages_match = re.search(r'(\d+)', value)
                            result["pages"] = int(pages_match.group(1)) if pages_match else None
                            
                        elif "ISBN" in label:
                            isbn_match = re.search(r'[\d-]+', value)
                            result["isbn"] = isbn_match.group(0).replace("-", "") if isbn_match else ""
                            
                        elif "出版时间" in label or "出版日期" in label:
                            year_match = re.search(r'(\d{4})', value)
                            result["year"] = int(year_match.group(1)) if year_match else None
                            
                        elif "开本" in label:
                            result["format"] = value
                            
                        elif "装帧" in label:
                            result["binding"] = value
            
            info_items = soup.select("div.book-info li") or soup.select("ul.info-list li")
            for item in info_items:
                text = item.text.strip()
                
                if "字数" in text and "word_count" not in result:
                    word_match = re.search(r'(\d+)', text)
                    result["word_count"] = int(word_match.group(1)) if word_match else None
                    
                elif "页数" in text and "pages" not in result:
                    pages_match = re.search(r'(\d+)', text)
                    result["pages"] = int(pages_match.group(1)) if pages_match else None
                    
                elif "ISBN" in text and "isbn" not in result:
                    isbn_match = re.search(r'[\d-]+', text)
                    result["isbn"] = isbn_match.group(0).replace("-", "") if isbn_match else ""
            
            summary_elem = soup.select_one("div.summary") or soup.select_one("div.book-intro")
            if summary_elem:
                result["summary"] = summary_elem.text.strip()
            
            cover_elem = soup.select_one("div.cover img") or soup.select_one("img.book-cover")
            if cover_elem:
                cover_url = cover_elem.get("src", "") or cover_elem.get("data-src", "")
                if cover_url and not cover_url.startswith("http"):
                    cover_url = config.BOOKCHINA_BASE_URL + cover_url
                result["cover_url"] = cover_url
            
            Logger.success(f"中国图书网详情爬取完成: {result.get('title', '')}")
            
        except Exception as e:
            Logger.error(f"中国图书网详情爬取失败: {e}")
            import traceback
            traceback.print_exc()
            
        return result
        
    async def crawl(self, isbn: str = None, title: str = None) -> Dict[str, Any]:
        """
        爬取中国图书网数据
        
        Args:
            isbn: ISBN 号
            title: 书名
            
        Returns:
            完整数据
        """
        result = {
            "source": "bookchina",
            "detail": {}
        }
        
        book_url = None
        
        if isbn:
            book_url = await self.search(isbn)
            
        if not book_url and title:
            book_url = await self.search(title)
            
        if book_url:
            result["detail"] = await self.crawl_detail(book_url)
        else:
            Logger.warning("中国图书网未找到书籍")
            
        return result
