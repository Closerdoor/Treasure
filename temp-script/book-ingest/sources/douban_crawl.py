# -*- coding: utf-8 -*-
"""
豆瓣读书爬虫 - 独立脚本

一次性获取全部信息：详情页 + 短评 + 长评 + 原文摘录 + 封面URL + 推荐书目
不再通过百度搜索跳转，改为直接访问 + Cookie 登录

输出字段：
- douban_id, url, title, title_original
- rating, rating_count, rating_distribution
- main_cover_url, cover_urls
- authors, translators
- publisher, year, pages, isbn, price, series
- summary, tags
- recommendations
- comments (短评), reviews (长评), excerpts (原文摘录)
- reading_counts (想读/在读/读过)
"""
import asyncio
import json
import random
import re
from typing import Optional, List, Dict, Any

from bs4 import BeautifulSoup

import config
from utils import Logger
from sources.base_crawler import BaseCrawler


class DoubanCrawler(BaseCrawler):

    def __init__(self):
        super().__init__(source_name="douban")
        self._logged_in = False

    async def ensure_login(self):
        """确保已登录豆瓣"""
        if config.SKIP_LOGIN:
            Logger.info("[douban] 跳过登录验证，直接访问豆瓣...")
            await self.page.goto(config.DOUBAN_BASE_URL, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            current_url = self.page.url
            if "sorry" in current_url or "misc" in current_url:
                Logger.warning("[douban] 检到反爬页面，尝试处理...")
                await self._handle_anti_crawl()
            else:
                Logger.info("[douban] 豆瓣访问正常")
            self._logged_in = True
            return

        cookie_file = Path(config.OUTPUT_DIR) / "cookies" / "douban.json"
        if await self.load_cookies(cookie_file):
            try:
                await self.page.goto(config.DOUBAN_BASE_URL, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                await self.page.wait_for_selector(".nav-user-account", timeout=10000)
                Logger.info("[douban] 登录状态有效")
                self._logged_in = True
                return
            except Exception:
                Logger.warning("[douban] Cookie 验证失败")

        print("\n" + "=" * 60)
        print("请在打开的浏览器中手动登录豆瓣读书")
        print("登录成功后，程序将自动检测...")
        print("=" * 60 + "\n")

        await self.page.goto(config.DOUBAN_LOGIN_URL, timeout=60000, wait_until="domcontentloaded")

        max_wait = 300
        check_interval = 5
        waited = 0

        while waited < max_wait:
            await asyncio.sleep(check_interval)
            waited += check_interval

            try:
                current_url = self.page.url
                if "accounts.douban.com" in current_url:
                    if waited % 30 == 0:
                        print(f"已等待 {waited} 秒，请继续登录...")
                    continue

                if "sorry" in current_url or "misc" in current_url:
                    await self._handle_anti_crawl()
                    self._logged_in = True
                    return

                await self.page.goto(config.DOUBAN_BASE_URL, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                await self.page.wait_for_selector(".nav-user-account", timeout=5000)

                await self.save_cookies(cookie_file)
                Logger.success("[douban] 登录成功！")
                self._logged_in = True
                return

            except Exception:
                if waited % 30 == 0:
                    print(f"已等待 {waited} 秒，请继续登录...")
                continue

        raise Exception("[douban] 登录超时")

    async def _handle_anti_crawl(self):
        """处理反爬页面"""
        print("\n" + "=" * 60)
        print("检测到反爬机制（验证码或限制页面）")
        print("请在浏览器中手动完成验证")
        print("完成后按回车继续...")
        print("=" * 60 + "\n")
        input("按回车键继续...")

        try:
            await self.page.goto(config.DOUBAN_BASE_URL, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            await self.page.wait_for_selector(".nav-user-account", timeout=5000)
            cookie_file = Path(config.OUTPUT_DIR) / "cookies" / "douban.json"
            await self.save_cookies(cookie_file)
            Logger.success("[douban] 验证通过！")
        except Exception as e:
            Logger.error(f"[douban] 验证失败: {e}")
            raise Exception("[douban] 反爬验证未通过")

    async def crawl(self, douban_id: str, expected_title: str = None) -> Optional[Dict[str, Any]]:
        """
        一次性爬取豆瓣全部信息：详情 + 短评 + 长评 + 封面URL + 推荐

        Args:
            douban_id: 豆瓣书籍 ID
            expected_title: 预期标题

        Returns:
            完整的豆瓣数据字典
        """
        if not self.page:
            await self.init_browser()
            await self.ensure_login()

        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/"

        # 爬取详情页
        detail = await self._crawl_detail(douban_id, expected_title)
        if not detail:
            return None

        # 爬取短评
        try:
            comments = await self._crawl_comments(douban_id, config.REVIEWS_PER_SOURCE)
            detail["comments"] = comments
        except Exception as e:
            Logger.error(f"[douban] 短评爬取失败: {e}")
            detail["comments"] = []

        # 爬取长评
        try:
            reviews = await self._crawl_reviews(douban_id, config.REVIEWS_PER_SOURCE)
            detail["reviews"] = reviews
        except Exception as e:
            Logger.error(f"[douban] 长评爬取失败: {e}")
            detail["reviews"] = []

        # 爬取原文摘录
        try:
            excerpts = await self._crawl_excerpts(douban_id, config.REVIEWS_PER_SOURCE)
            detail["excerpts"] = excerpts
        except Exception as e:
            Logger.error(f"[douban] 原文摘录爬取失败: {e}")
            detail["excerpts"] = []

        # 爬取创作者信息
        try:
            person_links = detail.get("author_links", []) + detail.get("translator_links", [])
            if person_links:
                person_details = await self._crawl_persons(person_links)
                detail["person_details"] = person_details
        except Exception as e:
            Logger.error(f"[douban] 创作者信息爬取失败: {e}")
            detail["person_details"] = []

        return detail

    async def _crawl_detail(self, douban_id: str, expected_title: str = None) -> Optional[Dict[str, Any]]:
        """爬取详情页"""
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/"

        for attempt in range(config.MAX_RETRIES):
            try:
                Logger.info(f"[douban] 爬取详情页: {url} (尝试 {attempt + 1}/{config.MAX_RETRIES})")

                await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(2, 4))

                current_url = self.page.url
                if "sorry" in current_url or "misc" in current_url:
                    Logger.warning("[douban] 检测到反爬页面")
                    await self._handle_anti_crawl()
                    await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                    current_url = self.page.url

                if "error" in current_url or "404" in current_url:
                    raise Exception(f"页面不存在或被重定向: {current_url}")

                content = await self.page.content()
                soup = BeautifulSoup(content, "html.parser")

                title_elem = soup.select_one("h1 span[property='v:itemreviewed']") or soup.select_one("h1")
                if not title_elem:
                    raise Exception("未能获取到标题，页面可能未正确加载")

                actual_title = title_elem.text.strip()
                if expected_title and expected_title not in actual_title and actual_title not in expected_title:
                    Logger.warning(f"[douban] 标题不匹配！预期: {expected_title}, 实际: {actual_title}")
                    await self._handle_anti_crawl()
                    await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                    content = await self.page.content()
                    soup = BeautifulSoup(content, "html.parser")

                break

            except Exception as e:
                Logger.error(f"[douban] 爬取失败 (尝试 {attempt + 1}/{config.MAX_RETRIES}): {e}")
                if attempt < config.MAX_RETRIES - 1:
                    await asyncio.sleep([5, 10, 30][attempt])
                else:
                    raise

        result = {
            "douban_id": douban_id,
            "url": url,
            "source": "douban",
        }

        try:
            # 书名
            title_elem = soup.select_one("h1 span[property='v:itemreviewed']") or soup.select_one("h1")
            full_title = title_elem.text.strip() if title_elem else ""
            chinese_match = re.match(r'^([\u4e00-\u9fa5]+)', full_title)
            result["title"] = chinese_match.group(1) if chinese_match else (full_title.split()[0] if full_title else "")

            # info 区域
            info = soup.select_one("#info")

            # 原名
            if info:
                original_title_match = re.search(r"原名:</span>([^<]+)", str(info))
                if original_title_match:
                    result["title_original"] = original_title_match.group(1).strip()

            # 评分
            rating_elem = soup.select_one("strong.rating_num")
            result["rating"] = rating_elem.text.strip() if rating_elem else ""

            # 主封面
            main_cover_elem = soup.select_one("#mainpic img")
            main_cover_link = soup.select_one("#mainpic a")
            cover_url = ""
            if main_cover_link:
                href = main_cover_link.get("href", "")
                if href and "doubanio.com" in href:
                    cover_url = href
            if not cover_url and main_cover_elem:
                cover_url = main_cover_elem.get("src", "")
            if cover_url:
                cover_url = cover_url.replace("/s/", "/raw/").replace("/m/", "/raw/").replace("/l/", "/raw/")
            result["main_cover_url"] = cover_url

            # 其他封面 URL
            cover_urls = []
            try:
                other_covers = soup.select(".cover-list img") or soup.select("#mainpic .more-covers img")
                for img in other_covers[:5]:
                    src = img.get("src", "")
                    if src:
                        src = src.replace("/s/", "/raw/").replace("/m/", "/raw/").replace("/l/", "/raw/")
                        cover_urls.append(src)
            except Exception:
                pass
            result["cover_urls"] = cover_urls

            # 作者（含链接URL）
            authors = []
            author_links = []
            if info:
                author_pl = info.find("span", class_="pl", string=re.compile("作者"))
                if author_pl:
                    parent_span = author_pl.parent
                    if parent_span:
                        for a in parent_span.select("a"):
                            name = a.text.strip()
                            href = a.get("href", "")
                            authors.append(name)
                            if href:
                                if href.startswith("/"):
                                    href = config.DOUBAN_BASE_URL + href
                                author_links.append({"name": name, "url": href})
            result["authors"] = authors
            result["author_links"] = author_links

            # 译者（含链接URL）
            translators = []
            translator_links = []
            if info:
                translator_pl = info.find("span", class_="pl", string=re.compile("译者"))
                if translator_pl:
                    parent_span = translator_pl.parent
                    if parent_span:
                        for a in parent_span.select("a"):
                            name = a.text.strip()
                            href = a.get("href", "")
                            translators.append(name)
                            if href:
                                if href.startswith("/"):
                                    href = config.DOUBAN_BASE_URL + href
                                translator_links.append({"name": name, "url": href})
            result["translators"] = translators
            result["translator_links"] = translator_links

            # 出版社
            if info:
                publisher_match = re.search(r"出版社:</span>([^<]+)", str(info))
                result["publisher"] = publisher_match.group(1).strip() if publisher_match else ""

                # 出版年
                year_match = re.search(r"出版年:</span>([^<]+)", str(info))
                year_text = year_match.group(1).strip() if year_match else ""
                year_num = re.search(r"(\d{4})", year_text)
                result["year"] = int(year_num.group(1)) if year_num else None

                # 页数
                pages_match = re.search(r"页数:</span>([^<]+)", str(info))
                result["pages"] = pages_match.group(1).strip() if pages_match else ""

                # ISBN
                isbn_match = re.search(r"ISBN:</span>([^<]+)", str(info))
                result["isbn"] = isbn_match.group(1).strip() if isbn_match else ""

                # 定价
                price_match = re.search(r"定价:</span>([^<]+)", str(info))
                result["price"] = price_match.group(1).strip() if price_match else ""

                # 丛书
                series_match = re.search(r"丛书:</span>.*?<a[^>]*>([^<]+)</a>", str(info), re.DOTALL)
                result["series"] = series_match.group(1).strip() if series_match else ""

            # 简介
            summary_elem = soup.select_one("span[property='v:summary']")
            result["summary"] = summary_elem.text.strip() if summary_elem else ""

            # 标签
            tags = []
            tags_elem = soup.select(".tags-body a")
            for tag_elem in tags_elem:
                tags.append(tag_elem.text.strip())
            result["tags"] = tags

            # 相关推荐
            result["recommendations"] = self._get_recommendations(soup)

            Logger.success(f"[douban] 详情页爬取完成: {result.get('title', '')}")

        except Exception as e:
            Logger.error(f"[douban] 解析详情页失败: {e}")
            import traceback
            traceback.print_exc()
            raise

        return result

    def _get_recommendations(self, soup: BeautifulSoup) -> List[Dict]:
        """获取相关推荐"""
        recommendations = []
        try:
            rec_elems = soup.select(".recommendations-bd dl")
            for dl in rec_elems:
                try:
                    title_elem = dl.select_one("dd a")
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()
                    url = title_elem.get("href", "")

                    rating_elem = dl.select_one(".rating")
                    rating = ""
                    if rating_elem:
                        rating_text = rating_elem.get("class", [])
                        for cls in rating_text:
                            if "allstar" in cls:
                                rating = cls.replace("allstar", "").replace("0", "")
                                break

                    source_id = ""
                    if url:
                        match = re.search(r'/subject/(\d+)/', url)
                        if match:
                            source_id = match.group(1)

                    recommendations.append({
                        "title": title,
                        "source": "douban",
                        "sourceId": source_id,
                        "url": url,
                        "rating": rating,
                    })
                except Exception:
                    continue
        except Exception as e:
            Logger.warning(f"[douban] 获取相关推荐失败: {e}")
        return recommendations

    async def _crawl_comments(self, douban_id: str, count: int = 20) -> List[Dict]:
        """爬取短评（按热度排序）"""
        Logger.info(f"[douban] 正在爬取短评: {douban_id}")

        comments = []
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/comments"

        await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

        if "sorry" in self.page.url or "misc" in self.page.url:
            await self._handle_anti_crawl()
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

        start = 0
        while len(comments) < count:
            page_url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/comments?start={start}&limit=20&sort=score&status=P"

            await self.page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            items = soup.select(".comment-item")
            if not items:
                break

            for item in items:
                try:
                    user_elem = item.select_one(".comment-info a")
                    user_name = user_elem.text.strip() if user_elem else ""

                    rating_elem = item.select_one(".rating")
                    rating = ""
                    if rating_elem:
                        rating_class = rating_elem.get("class", [])
                        for cls in rating_class:
                            if "allstar" in cls:
                                rating = cls.replace("allstar", "").replace("0rating", "")
                                break

                    votes = 0
                    h3_elem = item.select_one("h3")
                    if h3_elem:
                        votes_match = re.search(r"(\d+)\s*有用", h3_elem.text)
                        if votes_match:
                            votes = int(votes_match.group(1))
                    else:
                        votes_elem = item.select_one(".votes.vote-count")
                        if votes_elem:
                            try:
                                votes = int(votes_elem.text.strip())
                            except ValueError:
                                votes = 0

                    content_elem = item.select_one(".short")
                    comment_content = content_elem.text.strip() if content_elem else ""

                    time_elem = item.select_one(".comment-time")
                    comment_time = time_elem.text.strip() if time_elem else ""

                    comments.append({
                        "author": user_name,
                        "source": "豆瓣短评",
                        "date": comment_time,
                        "content": comment_content,
                        "rating": rating,
                        "votes": votes,
                        "url": None,
                        "title": None,
                    })
                except Exception:
                    continue

            start += 20
            await asyncio.sleep(config.PAGE_DELAY)

        comments = comments[:count]
        Logger.success(f"[douban] 获取 {len(comments)} 条短评")
        return comments

    async def _crawl_reviews(self, douban_id: str, count: int = 20) -> List[Dict]:
        """爬取长评（按热度排序）"""
        Logger.info(f"[douban] 正在爬取长评: {douban_id}")

        reviews = []
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/reviews"

        await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

        if "sorry" in self.page.url or "misc" in self.page.url:
            await self._handle_anti_crawl()
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

        try:
            sort_btn = await self.page.query_selector("a[href*='sort=hot']")
            if sort_btn:
                await sort_btn.click()
                await asyncio.sleep(1)
        except Exception:
            pass

        start = 0
        while len(reviews) < count:
            page_url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/reviews?start={start}&sort=hot"

            await self.page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            items = soup.select(".review-list article") or soup.select(".review-item")
            if not items:
                break

            for item in items:
                try:
                    title_elem = item.select_one("h2 a") or item.select_one(".review-title a")
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()
                    review_url = title_elem.get("href", "")
                    if not review_url:
                        continue

                    full_content = await self._get_review_content(review_url)

                    author_elem = item.select_one(".author a") or item.select_one(".review-meta a")
                    author = author_elem.text.strip() if author_elem else ""

                    time_elem = item.select_one(".date") or item.select_one(".review-meta time")
                    review_time = time_elem.text.strip() if time_elem else ""

                    votes_elem = item.select_one(".action-btn.up span") or item.select_one(".votes")
                    votes = "0"
                    if votes_elem:
                        votes = votes_elem.text.strip()

                    reviews.append({
                        "author": author,
                        "source": "豆瓣长评",
                        "date": review_time,
                        "content": full_content,
                        "url": review_url,
                        "title": title,
                        "votes": int(votes) if votes.isdigit() else 0,
                    })

                    if len(reviews) >= count:
                        break

                except Exception as e:
                    Logger.warning(f"[douban] 解析长评失败: {e}")
                    continue

            start += 20
            await asyncio.sleep(config.PAGE_DELAY)

        reviews = reviews[:count]
        Logger.success(f"[douban] 获取 {len(reviews)} 篇长评")
        return reviews

    async def _crawl_excerpts(self, douban_id: str, count: int = 20) -> List[Dict]:
        """爬取原文摘录（按热度排序）"""
        Logger.info(f"[douban] 正在爬取原文摘录: {douban_id}")

        excerpts = []
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/blockquotes"

        await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

        if "sorry" in self.page.url or "misc" in self.page.url:
            await self._handle_anti_crawl()
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

        start = 0
        while len(excerpts) < count:
            page_url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/blockquotes?sort=score&start={start}"

            await self.page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            items = soup.select("li figure")
            if not items:
                break

            for figure in items:
                try:
                    content_text = ""
                    for child in figure.children:
                        if isinstance(child, str):
                            content_text += child.strip()
                        elif hasattr(child, 'name'):
                            if child.name == "a" and "查看原文" in child.text:
                                continue
                            content_text += child.get_text(strip=True)

                    content_text = content_text.strip()
                    if not content_text:
                        continue

                    note = ""
                    note_elem = figure.select_one("div[class*='引自']")
                    if note_elem:
                        note = note_elem.text.strip()
                    else:
                        for div in figure.select("div"):
                            div_text = div.text.strip()
                            if div_text.startswith("——"):
                                note = div_text
                                break
                            elif "引自" in div_text:
                                note = div_text
                                break

                    votes = 0
                    info_div = figure.select_one("div")
                    if info_div:
                        votes_match = re.search(r"(\d+)\s*赞", info_div.text)
                        if votes_match:
                            votes = int(votes_match.group(1))

                    excerpts.append({
                        "content": content_text,
                        "note": note,
                        "votes": votes,
                    })

                    if len(excerpts) >= count:
                        break

                except Exception:
                    continue

            start += 20
            await asyncio.sleep(config.PAGE_DELAY)

        excerpts = excerpts[:count]
        Logger.success(f"[douban] 获取 {len(excerpts)} 条原文摘录")
        return excerpts

    async def _get_review_content(self, review_url: str) -> str:
        """获取长评完整内容"""
        try:
            new_page = await self.context.new_page()
            await new_page.goto(review_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(0.5, 1.5))

            content = await new_page.content()
            soup = BeautifulSoup(content, "html.parser")

            review_body = soup.select_one(".review-content") or soup.select_one("#link-report")
            text = review_body.text.strip() if review_body else ""

            await new_page.close()
            return text

        except Exception as e:
            Logger.warning(f"[douban] 获取长评内容失败: {e}")
            return ""

    async def _crawl_persons(self, person_links: List[Dict]) -> List[Dict]:
        """
        爬取创作者人物页信息
        
        从豆瓣 personage 页面获取：头像URL、中文名、外文名、简介、性别、出生日期等
        
        Args:
            person_links: [{"name": "钱锺书", "url": "https://book.douban.com/author/4502389/"}]
            
        Returns:
            创作者信息列表
        """
        Logger.info(f"[douban] 正在爬取 {len(person_links)} 位创作者信息")
        
        person_details = []
        seen_urls = set()
        
        for link in person_links:
            url = link.get("url", "")
            name = link.get("name", "")
            
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            
            try:
                detail = await self._crawl_person_page(url, name)
                if detail:
                    person_details.append(detail)
            except Exception as e:
                Logger.warning(f"[douban] 创作者信息爬取失败: {name} - {e}")
            
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        Logger.success(f"[douban] 获取 {len(person_details)} 位创作者信息")
        return person_details

    async def _crawl_person_page(self, url: str, name: str) -> Optional[Dict[str, Any]]:
        """爬取单个创作者的人物页"""
        try:
            Logger.info(f"[douban] 爬取创作者: {name} ({url})")
            
            new_page = await self.context.new_page()
            await new_page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(1, 2))
            
            final_url = new_page.url
            
            content = await new_page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            result = {
                "name": name,
                "source": "douban",
                "personage_url": final_url,
            }
            
            # 人物页 ID
            personage_match = re.search(r'/personage/(\d+)/', final_url)
            if personage_match:
                result["douban_personage_id"] = personage_match.group(1)
            
            # 头像
            avatar_elem = soup.select_one(".info img") or soup.select_one("#content img[src*='celebrity']")
            if avatar_elem:
                avatar_src = avatar_elem.get("src", "")
                if avatar_src and "default" not in avatar_src:
                    avatar_src = avatar_src.replace("/s/", "/raw/").replace("/m/", "/raw/")
                    result["avatar_url"] = avatar_src
            
            # 标题行（含中文名和外文名）
            title_elem = soup.select_one("h1")
            if title_elem:
                title_text = title_elem.text.strip()
                parts = title_text.split()
                result["name"] = parts[0] if parts else title_text
                if len(parts) > 1:
                    result["name_en"] = " ".join(parts[1:])
            
            # 基本信息（性别、出生日期、出生地等）
            info_list = soup.select(".info li")
            for li in info_list:
                text = li.text.strip()
                if "性别:" in text:
                    result["gender"] = text.replace("性别:", "").replace("性别：", "").strip()
                elif "出生日期:" in text or "出生日期：" in text:
                    result["birth_date"] = text.replace("出生日期:", "").replace("出生日期：", "").strip()
                elif "去世日期:" in text or "去世日期：" in text:
                    result["death_date"] = text.replace("去世日期:", "").replace("去世日期：", "").strip()
                elif "出生地:" in text or "出生地：" in text:
                    result["birth_place"] = text.replace("出生地:", "").replace("出生地：", "").strip()
                elif "更多中文名:" in text or "更多中文名：" in text:
                    result["more_names_cn"] = text.replace("更多中文名:", "").replace("更多中文名：", "").strip()
                elif "更多外文名:" in text or "更多外文名：" in text:
                    result["more_names_en"] = text.replace("更多外文名:", "").replace("更多外文名：", "").strip()
                elif "家庭成员:" in text or "家庭成员：" in text:
                    result["family"] = text.replace("家庭成员:", "").replace("家庭成员：", "").strip()
                elif "IMDb编号:" in text or "IMDb编号：" in text:
                    imdb = text.replace("IMDb编号:", "").replace("IMDb编号：", "").strip()
                    result["imdb_id"] = imdb
                elif "职业:" in text or "职业：" in text:
                    result["occupation"] = text.replace("职业:", "").replace("职业：", "").strip()
            
            # 简介
            summary_elem = soup.select_one("#intro") or soup.select_one(".bd")
            if summary_elem:
                summary_text = summary_elem.text.strip()
                if summary_text:
                    result["intro"] = summary_text
            
            await new_page.close()
            Logger.success(f"[douban] 创作者信息获取完成: {name}")
            return result
            
        except Exception as e:
            Logger.warning(f"[douban] 创作者页面爬取失败: {name} - {e}")
            try:
                await new_page.close()
            except Exception:
                pass
            return None