# -*- coding: utf-8 -*-
"""
Goodreads 爬虫 - 独立脚本

一次性获取全部信息：搜索 + 详情 + 书评 + 封面URL
独立浏览器实例

输出字段：
- goodreads_id, url, title, authors[{name, url}]
- rating, summary, cover_url
- series, genres, isbn, pages, year
- translators[{name}], publisher
- similar_books (相似推荐)
- reviews (书评)

不采集：rating_count, rating_distribution, awards
"""
import asyncio
import random
import re
from typing import Optional, List, Dict, Any

from bs4 import BeautifulSoup

import config
from utils import Logger
from sources.base_crawler import BaseCrawler


class GoodreadsCrawler(BaseCrawler):

    def __init__(self):
        super().__init__(source_name="goodreads")

    async def crawl(self, isbn: str = None, title: str = None, author: str = None) -> Optional[Dict[str, Any]]:
        """
        一次性获取 Goodreads 全部信息

        Args:
            isbn: ISBN 号（优先）
            title: 书名
            author: 作者

        Returns:
            完整的 Goodreads 数据字典
        """
        if not self.page:
            await self.init_browser()

        book_url = None

        if isbn:
            book_url = await self._search_by_isbn(isbn)

        if not book_url and title:
            book_url = await self._search_by_title(title, author)

        if not book_url:
            Logger.warning("[goodreads] 未找到书籍")
            return None

        detail = await self._crawl_detail(book_url)

        reviews = []
        try:
            reviews = await self._crawl_reviews(book_url, config.REVIEWS_PER_SOURCE)
        except Exception as e:
            Logger.error(f"[goodreads] 书评爬取失败: {e}")

        return {
            "detail": detail,
            "reviews": reviews,
        }

    async def _search_by_isbn(self, isbn: str) -> Optional[str]:
        url = f"{config.GOODREADS_BASE_URL}/search?q={isbn}"
        try:
            Logger.info(f"[goodreads] 搜索 ISBN: {isbn}")
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            current_url = self.page.url
            if "/book/show/" in current_url:
                return current_url

            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            first_result = soup.select_one("a.bookTitle")
            if first_result:
                return config.GOODREADS_BASE_URL + first_result.get("href", "")

            return None
        except Exception as e:
            Logger.error(f"[goodreads] 搜索失败: {e}")
            return None

    async def _search_by_title(self, title: str, author: str = "") -> Optional[str]:
        query = f"{title} {author}".strip()
        url = f"{config.GOODREADS_BASE_URL}/search?q={query}"
        try:
            Logger.info(f"[goodreads] 搜索书名: {query}")
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            first_result = soup.select_one("a.bookTitle")
            if first_result:
                return config.GOODREADS_BASE_URL + first_result.get("href", "")

            return None
        except Exception as e:
            Logger.error(f"[goodreads] 搜索失败: {e}")
            return None

    async def _crawl_detail(self, book_url: str) -> Dict[str, Any]:
        """爬取详情页"""
        result = {"source": "goodreads", "url": book_url}

        try:
            Logger.info(f"[goodreads] 爬取详情: {book_url}")
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
            author_elems = soup.select("a.ContributorLink") or soup.select("a.authorName")
            for author_elem in author_elems:
                name_elem = author_elem.select_one("span.ContributorLink__name") or author_elem
                author_name = name_elem.text.strip()
                author_url = author_elem.get("href", "")
                if author_url and not author_url.startswith("http"):
                    author_url = config.GOODREADS_BASE_URL + author_url
                if author_name:
                    authors.append({"name": author_name, "url": author_url})
            result["authors"] = authors

            # 译者（Goodreads 新版在 ContributorLink 中 role=translator）
            translators = []
            translator_sections = soup.select("div[data-testid='authorsList']")
            for section in translator_sections:
                role_label = section.select_one("span.ContributorLinksList__roleLabel")
                if role_label and "translator" in role_label.text.lower():
                    for link in section.select("a.ContributorLink"):
                        name_elem = link.select_one("span.ContributorLink__name") or link
                        t_name = name_elem.text.strip()
                        if t_name:
                            translators.append({"name": t_name})
            if not translators:
                for link in soup.select("a.ContributorLink"):
                    role = link.select_one("span.ContributorLinksList__roleLabel")
                    if role and "translator" in role.text.lower():
                        name_elem = link.select_one("span.ContributorLink__name") or link
                        t_name = name_elem.text.strip()
                        if t_name:
                            translators.append({"name": t_name})
            result["translators"] = translators

            # 评分
            rating_elem = soup.select_one("div.RatingStatistics__rating") or soup.select_one("span[itemprop='ratingValue']")
            if rating_elem:
                rating_text = rating_elem.text.strip()
                try:
                    result["rating"] = round(float(rating_text) * 2, 1)
                except ValueError:
                    result["rating"] = None
            else:
                result["rating"] = None

            # 简介
            description_elem = soup.select_one("div[data-testid='description']") or soup.select_one("#description")
            if description_elem:
                result["summary"] = description_elem.text.strip()

            # 系列
            series_elem = soup.select_one("a[href*='/series/']")
            if series_elem:
                result["series"] = {"name": series_elem.text.strip(), "url": config.GOODREADS_BASE_URL + series_elem.get("href", "")}

            # 封面
            cover_elem = soup.select_one("img.ResponsiveImage") or soup.select_one("#coverImage")
            if cover_elem:
                result["cover_url"] = cover_elem.get("src", "") or cover_elem.get("data-src", "")

            # 类型
            genres = []
            genre_elems = soup.select("a.BookPageTree__node") or soup.select("a[href*='/genres/']")
            for genre_elem in genre_elems[:5]:
                genre_name = genre_elem.text.strip()
                if genre_name and genre_name not in genres:
                    genres.append(genre_name)
            result["genres"] = genres

            # ISBN
            isbn_elem = soup.select_one("div[data-testid='isbn13']") or soup.select_one("span[itemprop='isbn']")
            if isbn_elem:
                isbn_text = isbn_elem.text.strip()
                isbn_match = re.search(r'[\d-]+', isbn_text)
                result["isbn"] = isbn_match.group(0).replace("-", "") if isbn_match else ""

            # 页数
            pages_elem = soup.select_one("div[data-testid='pagesFormat']") or soup.select_one("span[itemprop='numberOfPages']")
            if pages_elem:
                pages_text = pages_elem.text.strip()
                pages_match = re.search(r'(\d+)', pages_text)
                result["pages"] = int(pages_match.group(1)) if pages_match else None

            # 出版年
            publish_elem = soup.select_one("div[data-testid='publicationInfo']") or soup.select_one("nobr[itemprop='datePublished']")
            if publish_elem:
                pub_text = publish_elem.text.strip()
                year_match = re.search(r'(\d{4})', pub_text)
                result["year"] = int(year_match.group(1)) if year_match else None

            # 出版社
            publisher_elem = soup.select_one("div[data-testid='publisherInfo']")
            if publisher_elem:
                pub_text = publisher_elem.text.strip()
                pub_match = re.search(r'by\s+(.+?)(?:\s*\(|$)', pub_text)
                if pub_match:
                    result["publisher"] = pub_match.group(1).strip()
                else:
                    result["publisher"] = pub_text.replace("by ", "").strip()

            # 相似推荐
            similar_books = []
            try:
                similar_section = soup.select(".BookListItem__title a") or soup.select(".CarouselItem a")
                for elem in similar_section[:5]:
                    book_title = elem.text.strip()
                    if book_title:
                        similar_books.append({"title": book_title})
            except Exception:
                pass
            result["similar_books"] = similar_books

            Logger.success(f"[goodreads] 详情爬取完成: {result.get('title', '')}")

        except Exception as e:
            Logger.error(f"[goodreads] 详情爬取失败: {e}")

        return result

    async def _crawl_reviews(self, book_url: str, count: int = 20) -> List[Dict]:
        """爬取书评"""
        Logger.info(f"[goodreads] 正在爬取书评: {book_url}")

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
                            "title": None,
                        })
                except Exception:
                    continue

        except Exception as e:
            Logger.error(f"[goodreads] 书评爬取失败: {e}")

        Logger.success(f"[goodreads] 获取 {len(reviews)} 条书评")
        return reviews