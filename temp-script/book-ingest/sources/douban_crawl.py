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
- publisher, publish_date, year, pages, isbn, price, binding, series
- summary, tags
- recommendations
- comments (短评), reviews (长评), excerpts (原文摘录)
- reading_counts (想读/在读/读过)
"""
import asyncio
import json
import random
import re
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import config
from utils import Logger
from sources.base_crawler import BaseCrawler


class DoubanCrawler(BaseCrawler):

    def __init__(self):
        super().__init__(source_name="douban")
        self._logged_in = False
        self._cookie_state_file = Path(config.OUTPUT_DIR) / "cookies" / "douban.json"
        self._cookie_header_file = Path(config.OUTPUT_DIR) / "cookies" / "douban-cookie.txt"
        self._loaded_cookie_sources = set()

    async def _load_cookie_header_file(self) -> bool:
        """加载从浏览器 Network 面板复制的 Cookie 请求头。"""
        if not self.context:
            return False

        cookie_file = self._cookie_header_file
        if not cookie_file.exists():
            return False

        text = cookie_file.read_text(encoding="utf-8", errors="ignore").strip()
        if text.lower().startswith("cookie:"):
            text = text.split(":", 1)[1].strip()

        pairs = []
        for item in re.split(r";\s*", text):
            if "=" not in item:
                continue
            name, value = item.split("=", 1)
            name = name.strip()
            value = value.strip()
            if name and value:
                pairs.append((name, value))

        if not pairs:
            Logger.warning(f"[douban] Cookie 请求头为空或格式不正确: {cookie_file}")
            return False

        cookies = []
        for domain in [".douban.com", "book.douban.com"]:
            for name, value in pairs:
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": "/",
                    "sameSite": "Lax",
                })

        await self.context.add_cookies(cookies)
        self._loaded_cookie_sources.add(str(cookie_file))
        Logger.info(f"[douban] 已加载请求头 Cookie: {cookie_file} ({len(pairs)} 项)")
        return True

    async def _load_cookie_state_file(self) -> bool:
        """加载脚本上次成功访问后自动保存的 Playwright Cookie。"""
        if not self.context or not self._cookie_state_file.exists():
            return False
        loaded = await self.load_cookies(self._cookie_state_file)
        if loaded:
            self._loaded_cookie_sources.add(str(self._cookie_state_file))
        return loaded

    async def _load_available_cookies(self) -> bool:
        """
        合并加载可用 Cookie。

        douban-cookie.txt 是用户从浏览器 Network 复制的初始授权；
        douban.json 是脚本运行中自动续存的浏览器状态。两者都存在时，
        先加载较旧文件，再加载较新文件，让更新的 Cookie 覆盖旧值。
        """
        candidates = [
            (self._cookie_state_file, self._load_cookie_state_file),
            (self._cookie_header_file, self._load_cookie_header_file),
        ]
        candidates = [item for item in candidates if item[0].exists()]
        candidates.sort(key=lambda item: item[0].stat().st_mtime)

        loaded_any = False
        for _, loader in candidates:
            loaded_any = await loader() or loaded_any
        return loaded_any

    async def _persist_cookies(self, reason: str = ""):
        """把当前浏览器上下文里的 Cookie 自动续存，供下次采集复用。"""
        if not self.context:
            return
        try:
            await self.save_cookies(self._cookie_state_file)
            if reason:
                Logger.info(f"[douban] 已续存 Cookie 状态: {reason}")
        except Exception as e:
            Logger.warning(f"[douban] Cookie 状态续存失败: {e}")

    async def ensure_login(self):
        """确保已登录豆瓣"""
        await self._load_available_cookies()

        if config.SKIP_LOGIN:
            Logger.info("[douban] 跳过登录验证，直接访问豆瓣...")
            await self.page.goto(config.DOUBAN_BASE_URL, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            await self._handle_security_continue()

            current_url = self.page.url
            if "sorry" in current_url or "misc" in current_url:
                Logger.warning("[douban] 检到反爬页面，尝试处理...")
                await self._handle_anti_crawl()
            else:
                Logger.info("[douban] 豆瓣访问正常")
                await self._persist_cookies("启动验证通过")
            self._logged_in = True
            return

        if await self._load_cookie_state_file():
            try:
                await self.page.goto(config.DOUBAN_BASE_URL, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                await self.page.wait_for_selector(".nav-user-account", timeout=10000)
                Logger.info("[douban] 登录状态有效")
                await self._persist_cookies("登录状态验证通过")
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

                await self._persist_cookies("手动登录成功")
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
        await self._persist_cookies("触发反爬前保存现场")

        if config.HEADLESS or not sys.stdin.isatty():
            raise Exception(
                "[douban] 触发验证码/安全限制，当前为无交互采集环境，脚本无法代替用户完成验证。"
                "请稍后重试，或在浏览器中完成验证后更新 data/cookies/douban-cookie.txt。"
            )

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
            await self._persist_cookies("人工验证通过")
            Logger.success("[douban] 验证通过！")
        except Exception as e:
            Logger.error(f"[douban] 验证失败: {e}")
            raise Exception("[douban] 反爬验证未通过")

    def _is_anti_crawl_page(self) -> bool:
        current_url = self.page.url if self.page else ""
        return any(marker in current_url for marker in ["sorry", "misc", "sec.douban.com"])

    async def _remember_successful_page(self, label: str):
        """成功拿到正常页面后，及时续存当前 Cookie。"""
        current_url = self.page.url if self.page else ""
        if any(marker in current_url for marker in ["sorry", "misc", "sec.douban.com", "accounts.douban.com"]):
            return
        await self._persist_cookies(label)

    async def _handle_security_continue(self) -> bool:
        """处理豆瓣“点我继续浏览”的轻量安全页。"""
        try:
            content = await self.page.content()
        except Exception:
            return False

        if "点我继续浏览" not in content and 'id="sec"' not in content:
            return False

        Logger.info("[douban] 检测到安全继续页，自动点击继续浏览...")
        try:
            await self.page.click("#sub", timeout=5000)
            await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
            await asyncio.sleep(random.uniform(2, 4))
            await self._persist_cookies("自动通过安全继续页")
            return True
        except Exception as e:
            Logger.warning(f"[douban] 自动继续浏览失败: {e}")
            return False

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
        critical_errors = []
        noncritical_errors = []

        # 爬取短评
        try:
            comments = await self._crawl_comments(douban_id, config.REVIEWS_PER_SOURCE)
            detail["comments"] = comments
        except Exception as e:
            Logger.error(f"[douban] 短评爬取失败: {e}")
            critical_errors.append(f"comments: {e}")
            detail["comments"] = []

        # 爬取长评
        try:
            reviews = await self._crawl_reviews(douban_id, config.REVIEWS_PER_SOURCE)
            detail["reviews"] = reviews
        except Exception as e:
            Logger.error(f"[douban] 长评爬取失败: {e}")
            critical_errors.append(f"reviews: {e}")
            detail["reviews"] = []

        # 爬取原文摘录
        try:
            excerpts = await self._crawl_excerpts(douban_id, config.REVIEWS_PER_SOURCE)
            detail["excerpts"] = excerpts
        except Exception as e:
            Logger.error(f"[douban] 原文摘录爬取失败: {e}")
            critical_errors.append(f"excerpts: {e}")
            detail["excerpts"] = []

        # 爬取创作者信息
        try:
            person_links = detail.get("author_links", []) + detail.get("translator_links", [])
            if person_links:
                person_details = await self._crawl_persons(person_links)
                detail["person_details"] = person_details
        except Exception as e:
            Logger.error(f"[douban] 创作者信息爬取失败: {e}")
            noncritical_errors.append(f"person_details: {e}")
            detail["person_details"] = []

        if critical_errors:
            detail["_critical_errors"] = critical_errors
        if noncritical_errors:
            detail["_crawl_errors"] = noncritical_errors
        return detail

    async def _crawl_detail(self, douban_id: str, expected_title: str = None) -> Optional[Dict[str, Any]]:
        """爬取详情页"""
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/"

        for attempt in range(config.MAX_RETRIES):
            try:
                Logger.info(f"[douban] 爬取详情页: {url} (尝试 {attempt + 1}/{config.MAX_RETRIES})")

                await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(2, 4))
                await self._handle_security_continue()

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
                await self._remember_successful_page("详情页访问成功")
                soup = BeautifulSoup(content, "html.parser")

                title_elem = soup.select_one("h1 span[property='v:itemreviewed']") or soup.select_one("h1")
                if not title_elem:
                    if await self._handle_security_continue():
                        content = await self.page.content()
                        await self._remember_successful_page("安全继续页通过")
                        soup = BeautifulSoup(content, "html.parser")
                        title_elem = soup.select_one("h1 span[property='v:itemreviewed']") or soup.select_one("h1")
                    if not title_elem:
                        security_page = soup.select_one("form#sec") or soup.find(string=re.compile("点我继续浏览"))
                        if security_page:
                            raise Exception("豆瓣安全继续页未能自动通过")
                        raise Exception("未能获取到标题，页面可能未正确加载")

                actual_title = title_elem.text.strip()
                if actual_title in {"登录跳转", "豆瓣"} or "登录" in actual_title:
                    raise Exception("豆瓣返回登录/安全跳转页，未取得作品详情")
                if expected_title and expected_title not in actual_title and actual_title not in expected_title:
                    Logger.warning(f"[douban] 标题不匹配！预期: {expected_title}, 实际: {actual_title}")

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
            result["title"] = expected_title if expected_title and full_title and (
                expected_title in full_title or full_title in expected_title
            ) else full_title

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
                result["publish_date"] = year_text
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

                # 装帧
                binding_match = re.search(r"装帧:</span>([^<]+)", str(info))
                result["binding"] = binding_match.group(1).strip() if binding_match else ""

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

        if self._is_anti_crawl_page():
            await self._handle_anti_crawl()
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

        start = 0
        while len(comments) < count:
            page_url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/comments?start={start}&limit=20&sort=score&status=P"

            await self.page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            if self._is_anti_crawl_page():
                await self._handle_anti_crawl()

            content = await self.page.content()
            await self._remember_successful_page("短评页访问成功")
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

        if self._is_anti_crawl_page():
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

            if self._is_anti_crawl_page():
                await self._handle_anti_crawl()

            content = await self.page.content()
            await self._remember_successful_page("长评列表访问成功")
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
                    if not full_content:
                        continue

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
        """爬取原文摘录（列表页按热度排序，逐条进入详情页取原文内容）。"""
        Logger.info(f"[douban] 正在爬取原文摘录: {douban_id}")

        excerpts = []
        seen_urls = set()
        seen_contents = set()
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/blockquotes"

        await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

        if self._is_anti_crawl_page():
            await self._handle_anti_crawl()
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

        start = 0
        while len(excerpts) < count:
            page_url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/blockquotes?sort=score&start={start}"

            await self.page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            if self._is_anti_crawl_page():
                await self._handle_anti_crawl()

            content = await self.page.content()
            await self._remember_successful_page("摘录列表访问成功")
            soup = BeautifulSoup(content, "html.parser")

            items = soup.select("li figure")
            if not items:
                break

            for figure in items:
                try:
                    detail_url = self._find_excerpt_detail_url(figure)
                    note = self._extract_excerpt_note(figure)
                    votes = self._extract_excerpt_votes(figure)

                    if detail_url and detail_url in seen_urls:
                        continue

                    content_text = ""
                    if detail_url:
                        content_text = await self._get_excerpt_content(detail_url)

                    if not content_text:
                        content_text = self._clean_excerpt_text(figure.get_text(" ", strip=True), note)

                    if not content_text:
                        continue

                    content_key = re.sub(r"\s+", "", content_text)
                    if content_key in seen_contents:
                        continue

                    excerpts.append({
                        "content": content_text,
                        "note": note,
                        "votes": votes,
                        "url": detail_url,
                    })
                    if detail_url:
                        seen_urls.add(detail_url)
                    seen_contents.add(content_key)

                    if len(excerpts) >= count:
                        break

                except Exception:
                    continue

            start += 20
            await asyncio.sleep(config.PAGE_DELAY)

        excerpts = excerpts[:count]
        Logger.success(f"[douban] 获取 {len(excerpts)} 条原文摘录")
        return excerpts

    def _find_excerpt_detail_url(self, figure) -> Optional[str]:
        """从摘录列表项找到详情页链接。"""
        for link in figure.select("a[href]"):
            href = link.get("href", "")
            text = link.get_text(" ", strip=True)
            if not href:
                continue
            if "查看原文" in text or "/annotation/" in href or "/blockquotes/" in href:
                return urljoin(config.DOUBAN_BASE_URL, href)
        return None

    def _extract_excerpt_note(self, figure) -> str:
        """提取页码 / 章节备注，不混入 content。"""
        text = figure.get_text("\n", strip=True)
        match = re.search(r"(——\s*引自[^\n]+)", text)
        if match:
            return match.group(1).strip()
        for div in figure.select("div"):
            div_text = div.get_text(" ", strip=True)
            if "引自" in div_text:
                note_match = re.search(r"(——\s*引自.+)$", div_text)
                return (note_match.group(1) if note_match else div_text).strip()
        return ""

    def _extract_excerpt_votes(self, figure) -> int:
        text = figure.get_text(" ", strip=True)
        match = re.search(r"(\d+)\s*赞", text)
        return int(match.group(1)) if match else 0

    def _clean_excerpt_text(self, text: str, note: str = "") -> str:
        """只保留原文摘录本身，去掉用户、回复数、点赞数、日期和页码备注。"""
        if not text:
            return ""
        text = text.replace("查看原文", " ")
        if note:
            text = text.replace(note, " ")
        text = re.split(r"(?:——\s*)?引自", text, maxsplit=1)[0]
        text = re.split(r"\(?\)?\s*[^，。！？；：\n]{0,40}\d+\s*回复\s*\d+\s*赞\s*\d{4}-\d{2}-\d{2}", text, maxsplit=1)[0]
        text = re.sub(r"\b\d+\s*回复\b", " ", text)
        text = re.sub(r"\b\d+\s*赞\b", " ", text)
        text = re.sub(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", " ", text)
        text = re.sub(r"\(\s*\)", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def _get_excerpt_content(self, excerpt_url: str) -> str:
        """进入摘录详情页获取完整原文内容。"""
        try:
            new_page = await self.context.new_page()
            await new_page.goto(excerpt_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(0.5, 1.2))
            if any(marker in new_page.url for marker in ["sorry", "misc", "sec.douban.com", "accounts.douban.com"]):
                await self._persist_cookies("摘录详情触发限制前保存现场")
                raise Exception("摘录详情页触发豆瓣安全限制")

            content = await new_page.content()
            await self._persist_cookies("摘录详情访问成功")
            soup = BeautifulSoup(content, "html.parser")

            selectors = [
                ".blockquote-content",
                ".annotation",
                ".annotation-content",
                "#content figure",
                "#link-report",
                "figure",
                ".article",
            ]
            for selector in selectors:
                for elem in soup.select(selector):
                    text = self._clean_excerpt_text(elem.get_text(" ", strip=True))
                    if text and len(text) >= 8:
                        await new_page.close()
                        return text

            await new_page.close()
            return ""

        except Exception as e:
            Logger.warning(f"[douban] 获取摘录详情失败: {excerpt_url} - {e}")
            try:
                await new_page.close()
            except Exception:
                pass
            return ""

    async def _get_review_content(self, review_url: str) -> str:
        """获取长评完整内容"""
        try:
            new_page = await self.context.new_page()
            await new_page.goto(review_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(0.5, 1.5))
            if any(marker in new_page.url for marker in ["sorry", "misc", "sec.douban.com", "accounts.douban.com"]):
                await self._persist_cookies("长评详情触发限制前保存现场")
                raise Exception("长评详情页触发豆瓣安全限制")

            content = await new_page.content()
            await self._persist_cookies("长评详情访问成功")
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
            if any(marker in new_page.url for marker in ["sorry", "misc", "sec.douban.com", "accounts.douban.com"]):
                await self._persist_cookies("作者页触发限制前保存现场")
                raise Exception("作者页触发豆瓣安全限制")
            
            final_url = new_page.url
            
            content = await new_page.content()
            await self._persist_cookies("作者页访问成功")
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
                if summary_text and "登录/注册" not in summary_text and "下载豆瓣客户端" not in summary_text:
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
