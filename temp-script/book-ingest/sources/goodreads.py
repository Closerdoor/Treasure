# -*- coding: utf-8 -*-
"""
Goodreads 爬虫模块
"""
import asyncio
import random
import re
from typing import Optional, List, Dict, Any

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

import config
from utils import Logger


class GoodreadsCrawler:
    """Goodreads 爬虫"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    async def init_browser(self):
        """初始化浏览器"""
        Logger.info("正在启动 Goodreads 浏览器...")
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
            Logger.info(f"使用代理: {config.PROXY_URL}")
        
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
        Logger.info("Goodreads 浏览器已启动")
        
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def search_by_isbn(self, isbn: str) -> Optional[str]:
        """
        通过 ISBN 搜索书籍
        
        Args:
            isbn: ISBN 号
            
        Returns:
            Goodreads 书籍 URL 或 None
        """
        url = f"{config.GOODREADS_BASE_URL}/search?q={isbn}"
        
        try:
            Logger.info(f"Goodreads 搜索 ISBN: {isbn}")
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            current_url = self.page.url
            
            if "/book/show/" in current_url:
                Logger.success(f"Goodreads 找到书籍: {current_url}")
                return current_url
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            first_result = soup.select_one("a.bookTitle")
            if first_result:
                book_url = config.GOODREADS_BASE_URL + first_result.get("href", "")
                Logger.success(f"Goodreads 找到书籍: {book_url}")
                return book_url
            
            Logger.warning(f"Goodreads 未找到 ISBN: {isbn}")
            return None
            
        except Exception as e:
            Logger.error(f"Goodreads 搜索失败: {e}")
            return None
            
    async def search_by_title(self, title: str, author: str = "") -> Optional[str]:
        """
        通过书名搜索书籍
        
        Args:
            title: 书名
            author: 作者名（可选）
            
        Returns:
            Goodreads 书籍 URL 或 None
        """
        query = f"{title} {author}".strip()
        url = f"{config.GOODREADS_BASE_URL}/search?q={query}"
        
        try:
            Logger.info(f"Goodreads 搜索书名: {query}")
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            first_result = soup.select_one("a.bookTitle")
            if first_result:
                book_url = config.GOODREADS_BASE_URL + first_result.get("href", "")
                Logger.success(f"Goodreads 找到书籍: {book_url}")
                return book_url
            
            Logger.warning(f"Goodreads 未找到书名: {query}")
            return None
            
        except Exception as e:
            Logger.error(f"Goodreads 搜索失败: {e}")
            return None
            
    async def crawl_detail(self, book_url: str) -> Dict[str, Any]:
        """
        爬取书籍详情
        
        Args:
            book_url: Goodreads 书籍 URL
            
        Returns:
            书籍详情数据
        """
        result = {
            "source": "goodreads",
            "url": book_url
        }
        
        try:
            Logger.info(f"正在爬取 Goodreads 详情: {book_url}")
            await self.page.goto(book_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            goodreads_id_match = re.search(r'/book/show/(\d+)', book_url)
            if goodreads_id_match:
                result["goodreads_id"] = goodreads_id_match.group(1)
            
            title_elem = soup.select_one("h1[data-testid='bookTitle']") or soup.select_one("#bookTitle")
            result["title"] = title_elem.text.strip() if title_elem else ""
            
            authors = []
            author_elems = soup.select("a.authorName") or soup.select("span.ContributorLink__name")
            for author_elem in author_elems:
                author_name = author_elem.text.strip()
                if author_name:
                    authors.append(author_name)
            result["authors"] = authors
            
            rating_elem = soup.select_one("div.RatingStatistics__rating") or soup.select_one("span[itemprop='ratingValue']")
            if rating_elem:
                rating_text = rating_elem.text.strip()
                try:
                    rating = float(rating_text)
                    result["rating"] = rating * 2
                except:
                    result["rating"] = None
            else:
                result["rating"] = None
                
            rating_count_elem = soup.select_one("span[data-testid='ratingsCount']") or soup.select_one("meta[itemprop='ratingCount']")
            if rating_count_elem:
                count_text = rating_count_elem.text.strip() if rating_count_elem.name != "meta" else rating_count_elem.get("content", "")
                count_match = re.search(r'[\d,]+', count_text)
                result["rating_count"] = count_match.group(0).replace(",", "") if count_match else "0"
            else:
                result["rating_count"] = "0"
            
            description_elem = soup.select_one("div[data-testid='description']") or soup.select_one("#description")
            if description_elem:
                result["summary"] = description_elem.text.strip()
            
            series_elem = soup.select_one("a[href*='/series/']")
            if series_elem:
                series_name = series_elem.text.strip()
                series_url = config.GOODREADS_BASE_URL + series_elem.get("href", "")
                result["series"] = {
                    "name": series_name,
                    "url": series_url
                }
            
            awards = []
            awards_elem = soup.select_one("div[data-testid='awards']")
            if awards_elem:
                award_items = awards_elem.select("span")
                for item in award_items:
                    award_name = item.text.strip()
                    if award_name:
                        awards.append(award_name)
            result["awards"] = awards
            
            cover_elem = soup.select_one("img.ResponsiveImage") or soup.select_one("#coverImage")
            if cover_elem:
                cover_url = cover_elem.get("src", "") or cover_elem.get("data-src", "")
                result["cover_url"] = cover_url
            
            genres = []
            genre_elems = soup.select("a.BookPageTree__node") or soup.select("a[href*='/genres/']")
            for genre_elem in genre_elems[:5]:
                genre_name = genre_elem.text.strip()
                if genre_name and genre_name not in genres:
                    genres.append(genre_name)
            result["genres"] = genres
            
            isbn_elem = soup.select_one("div[data-testid='isbn13']") or soup.select_one("span[itemprop='isbn']")
            if isbn_elem:
                isbn_text = isbn_elem.text.strip()
                isbn_match = re.search(r'[\d-]+', isbn_text)
                result["isbn"] = isbn_match.group(0).replace("-", "") if isbn_match else ""
            
            pages_elem = soup.select_one("div[data-testid='pagesFormat']") or soup.select_one("span[itemprop='numberOfPages']")
            if pages_elem:
                pages_text = pages_elem.text.strip()
                pages_match = re.search(r'(\d+)', pages_text)
                result["pages"] = int(pages_match.group(1)) if pages_match else None
            
            publish_elem = soup.select_one("div[data-testid='publicationInfo']") or soup.select_one("nobr[itemprop='datePublished']")
            if publish_elem:
                pub_text = publish_elem.text.strip()
                year_match = re.search(r'(\d{4})', pub_text)
                result["year"] = int(year_match.group(1)) if year_match else None
            
            Logger.success(f"Goodreads 详情爬取完成: {result.get('title', '')}")
            
        except Exception as e:
            Logger.error(f"Goodreads 详情爬取失败: {e}")
            import traceback
            traceback.print_exc()
            
        return result
        
    async def crawl_reviews(self, book_url: str, count: int = 20) -> List[Dict]:
        """
        爬取书评
        
        Args:
            book_url: Goodreads 书籍 URL
            count: 爬取数量
            
        Returns:
            书评列表
        """
        Logger.info(f"正在爬取 Goodreads 书评: {book_url}")
        
        reviews = []
        
        try:
            reviews_url = book_url.rstrip("/") + "/reviews"
            await self.page.goto(reviews_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            review_items = soup.select("article.ReviewCard") or soup.select("div.review")
            
            for item in review_items[:count]:
                try:
                    author_elem = item.select_one("a.ReviewerProfile__name") or item.select_one("a.user")
                    author = author_elem.text.strip() if author_elem else ""
                    
                    rating_elem = item.select_one("span.RatingStars")
                    rating = ""
                    if rating_elem:
                        aria_label = rating_elem.get("aria-label", "")
                        rating_match = re.search(r'(\d+)', aria_label)
                        if rating_match:
                            rating = rating_match.group(1)
                    
                    content_elem = item.select_one("div.ReviewText") or item.select_one("div.reviewText")
                    review_content = content_elem.text.strip() if content_elem else ""
                    
                    date_elem = item.select_one("span.ReviewCard__pubDate") or item.select_one("a.reviewDate")
                    review_date = date_elem.text.strip() if date_elem else ""
                    
                    if review_content:
                        reviews.append({
                            "author": author,
                            "source": "Goodreads",
                            "date": review_date,
                            "content": review_content,
                            "rating": rating,
                            "votes": 0,
                            "url": book_url,
                            "title": None
                        })
                        
                except Exception as e:
                    Logger.warning(f"解析 Goodreads 书评失败: {e}")
                    continue
                    
        except Exception as e:
            Logger.error(f"Goodreads 书评爬取失败: {e}")
            
        Logger.success(f"获取 {len(reviews)} 条 Goodreads 书评")
        return reviews
        
    async def crawl(self, isbn: str = None, title: str = None, author: str = None) -> Dict[str, Any]:
        """
        爬取 Goodreads 数据
        
        Args:
            isbn: ISBN 号
            title: 书名
            author: 作者
            
        Returns:
            完整数据
        """
        result = {
            "source": "goodreads",
            "detail": {},
            "reviews": []
        }
        
        book_url = None
        
        if isbn:
            book_url = await self.search_by_isbn(isbn)
            
        if not book_url and title:
            book_url = await self.search_by_title(title, author)
            
        if book_url:
            result["detail"] = await self.crawl_detail(book_url)
            result["reviews"] = await self.crawl_reviews(book_url, config.REVIEWS_PER_SOURCE)
        else:
            Logger.warning("Goodreads 未找到书籍")
            
        return result
