# -*- coding: utf-8 -*-
"""
豆瓣读书爬虫模块
"""
import asyncio
import json
import random
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

import config
from utils import Logger


class DoubanBookCrawler:
    """豆瓣读书爬虫"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    async def init_browser(self):
        """初始化浏览器"""
        Logger.info("正在启动浏览器...")
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
            "viewport": {"width": 1920, "height": 1080},
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "geolocation": {"latitude": 39.9042, "longitude": 116.4074},
            "permissions": ["geolocation"],
        }
        
        if config.PROXY_ENABLED and config.PROXY_URL:
            context_options["proxy"] = {"server": config.PROXY_URL}
            Logger.info(f"使用代理: {config.PROXY_URL}")
        
        self.context = await self.browser.new_context(**context_options)
        
        # 注入脚本模拟真实浏览器行为
        await self.context.add_init_script("""
            // 隐藏 webdriver 标记
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // 模拟真实的 plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 模拟真实的 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
            
            // 隐藏自动化标记
            window.chrome = { runtime: {} };
        """)
        
        self.page = await self.context.new_page()
        Logger.info("浏览器已启动")
        
    async def load_cookies(self) -> bool:
        """加载已保存的 Cookie"""
        cookie_path = Path(config.COOKIES_FILE)
        if cookie_path.exists():
            cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
            await self.context.add_cookies(cookies)
            Logger.info("已加载保存的 Cookie")
            return True
        return False
    
    async def save_cookies(self):
        """保存 Cookie"""
        cookies = await self.context.cookies()
        Path(config.COOKIES_FILE).write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        Logger.info("Cookie 已保存")
        
    async def ensure_login(self):
        """确保已登录"""
        # 如果配置跳过登录，直接访问豆瓣验证
        if config.SKIP_LOGIN:
            Logger.info("跳过登录验证，直接访问豆瓣...")
            await self.page.goto(config.DOUBAN_BASE_URL, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            # 检查是否被重定向到反爬页面
            current_url = self.page.url
            if "sorry" in current_url or "misc" in current_url:
                Logger.warning("检测到反爬页面，尝试处理...")
                await self._handle_anti_crawl()
            else:
                Logger.info("豆瓣访问正常")
            return
        
        if await self.load_cookies():
            try:
                # 通过百度跳转访问豆瓣，避免直接访问触发反爬
                Logger.info("通过百度跳转验证登录状态...")
                await self.page.goto("https://www.baidu.com", timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(1)
                
                # 搜索豆瓣读书
                search_input = await self.page.query_selector('#kw')
                if search_input:
                    await search_input.fill('豆瓣读书')
                    search_btn = await self.page.query_selector('#su')
                    if search_btn:
                        await search_btn.click()
                        await asyncio.sleep(2)
                
                # 点击豆瓣链接
                douban_link = await self.page.query_selector('a[href*="book.douban.com"]')
                if douban_link:
                    await douban_link.click()
                    await asyncio.sleep(3)
                else:
                    # 直接访问
                    await self.page.goto(config.DOUBAN_BASE_URL, timeout=30000, wait_until="domcontentloaded")
                    await asyncio.sleep(2)
                
                # 检查是否被重定向到反爬页面
                current_url = self.page.url
                if "sorry" in current_url or "misc" in current_url:
                    Logger.warning("检测到反爬页面，需要手动处理")
                    await self._handle_anti_crawl()
                    return
                
                await self.page.wait_for_selector(".nav-user-account", timeout=10000)
                Logger.info("登录状态有效")
                return
            except Exception as e:
                Logger.warning(f"Cookie 验证失败: {e}")
        
        # 需要手动登录
        print("\n" + "="*60)
        print("请在打开的浏览器中手动登录豆瓣读书")
        print("如果出现验证码，请手动完成验证")
        print("登录成功后，程序将自动检测...")
        print("="*60 + "\n")
        
        await self.page.goto(config.DOUBAN_LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
        
        max_wait = 300
        check_interval = 5
        waited = 0
        
        while waited < max_wait:
            await asyncio.sleep(check_interval)
            waited += check_interval
            
            try:
                current_url = self.page.url
                
                # 检查是否还在登录页
                if "accounts.douban.com" in current_url:
                    if waited % 30 == 0:
                        print(f"已等待 {waited} 秒，请继续登录...")
                    continue
                
                # 检查是否被重定向到反爬页面
                if "sorry" in current_url or "misc" in current_url:
                    Logger.warning("检测到反爬页面，需要手动处理验证码")
                    await self._handle_anti_crawl()
                    return
                
                # 尝试访问读书首页验证登录状态
                await self.page.goto(config.DOUBAN_BASE_URL, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                
                await self.page.wait_for_selector(".nav-user-account", timeout=5000)
                
                await self.save_cookies()
                Logger.success("登录成功！")
                return
                
            except Exception as e:
                if waited % 30 == 0:
                    print(f"已等待 {waited} 秒，请继续登录...")
                continue
        
        raise Exception("登录超时，请重新运行程序")
    
    async def _handle_anti_crawl(self):
        """处理反爬页面（验证码等）"""
        print("\n" + "="*60)
        print("检测到反爬机制（验证码或限制页面）")
        print("请在浏览器中手动完成验证")
        print("完成后按回车继续...")
        print("="*60 + "\n")
        
        # 等待用户输入
        input("按回车键继续...")
        
        # 验证是否通过
        try:
            await self.page.goto(config.DOUBAN_BASE_URL, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            await self.page.wait_for_selector(".nav-user-account", timeout=5000)
            
            await self.save_cookies()
            Logger.success("验证通过！")
        except Exception as e:
            Logger.error(f"验证失败: {e}")
            raise Exception("反爬验证未通过，请重新运行程序")
        
    async def close(self):
        """关闭浏览器"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            Logger.warning(f"关闭浏览器时出错: {e}")
            
    async def crawl_detail(self, douban_id: str, expected_title: str = None, max_retries: int = 3) -> Dict[str, Any]:
        """
        爬取书籍详情页
        
        Args:
            douban_id: 豆瓣书籍 ID
            expected_title: 预期标题（用于搜索）
            max_retries: 最大重试次数
            
        Returns:
            书籍详情数据
        """
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/"
        
        retry_intervals = [5, 10, 30]
        
        for attempt in range(max_retries):
            try:
                Logger.info(f"正在爬取详情页: {url} (尝试 {attempt + 1}/{max_retries})")
                
                # 通过百度搜索跳转，模拟真实用户行为
                if expected_title:
                    search_url = f"https://www.baidu.com/s?wd={expected_title}+site%3Abook.douban.com"
                    Logger.info(f"通过百度搜索跳转: {search_url}")
                    await self.page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                    await asyncio.sleep(random.uniform(1, 2))
                    
                    # 查找豆瓣链接并点击
                    try:
                        # 查找包含 book.douban.com 的链接
                        douban_link = await self.page.query_selector(f'a[href*="book.douban.com/subject/{douban_id}"]')
                        if not douban_link:
                            # 尝试找任意豆瓣图书链接
                            douban_link = await self.page.query_selector('a[href*="book.douban.com/subject"]')
                        
                        if douban_link:
                            await douban_link.click()
                            await asyncio.sleep(random.uniform(2, 3))
                        else:
                            # 没找到链接，直接访问
                            Logger.warning("百度搜索未找到豆瓣链接，直接访问")
                            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    except Exception as e:
                        Logger.warning(f"点击搜索结果失败: {e}，直接访问")
                        await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                else:
                    await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                
                await asyncio.sleep(random.uniform(2, 4))
                
                # 检查是否被重定向到反爬页面
                current_url = self.page.url
                if "sorry" in current_url or "misc" in current_url:
                    Logger.warning("检测到反爬页面，需要手动处理")
                    await self._handle_anti_crawl()
                    # 重新尝试访问
                    await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                    current_url = self.page.url
                
                if "error" in current_url or "404" in current_url:
                    raise Exception(f"页面不存在或被重定向: {current_url}")
                
                content = await self.page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # 检查是否获取到有效数据
                title_elem = soup.select_one("h1 span[property='v:itemreviewed']")
                if not title_elem:
                    # 可能是页面结构不同，尝试其他选择器
                    title_elem = soup.select_one("h1")
                    if not title_elem:
                        raise Exception("未能获取到标题，页面可能未正确加载")
                
                # 验证标题是否匹配预期
                actual_title = title_elem.text.strip() if title_elem else ""
                if expected_title and expected_title not in actual_title and actual_title not in expected_title:
                    Logger.warning(f"标题不匹配！预期: {expected_title}, 实际: {actual_title}")
                    Logger.warning("可能被反爬重定向，等待手动处理...")
                    await self._handle_anti_crawl()
                    # 重新获取页面内容
                    await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                    content = await self.page.content()
                    soup = BeautifulSoup(content, "html.parser")
                    title_elem = soup.select_one("h1 span[property='v:itemreviewed']") or soup.select_one("h1")
                    actual_title = title_elem.text.strip() if title_elem else ""
                    if expected_title and expected_title not in actual_title and actual_title not in expected_title:
                        raise Exception(f"标题验证失败: 预期 '{expected_title}', 实际 '{actual_title}'")
                
                break
                
            except Exception as e:
                Logger.error(f"豆瓣爬取失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = retry_intervals[attempt]
                    Logger.info(f"等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    Logger.error(f"豆瓣爬取失败，已重试 {max_retries} 次")
                    raise Exception(f"豆瓣爬取失败: {douban_id} - {e}")
        
        result = {
            "douban_id": douban_id,
            "url": url,
            "source": "douban"
        }
        
        try:
            # 书名
            title_elem = soup.select_one("h1 span[property='v:itemreviewed']")
            if not title_elem:
                title_elem = soup.select_one("h1")
            full_title = title_elem.text.strip() if title_elem else ""
            chinese_match = re.match(r'^([\u4e00-\u9fa5]+)', full_title)
            if chinese_match:
                result["title"] = chinese_match.group(1)
            else:
                result["title"] = full_title.split()[0] if full_title else ""
            
            # 获取 info 区域
            info = soup.select_one("#info")
            
            # 原名
            if info:
                original_title_match = re.search(r"原名:</span>([^<]+)", str(info))
                if original_title_match:
                    result["title_original"] = original_title_match.group(1).strip()
            
            # 评分
            rating_elem = soup.select_one("strong.rating_num")
            result["rating"] = rating_elem.text.strip() if rating_elem else ""
            
            # 评价人数
            rating_count_elem = soup.select_one("span[property='v:votes']")
            result["rating_count"] = rating_count_elem.text.strip() if rating_count_elem else "0"
            
            # 主封面
            main_cover_elem = soup.select_one("#mainpic img")
            if main_cover_elem:
                cover_url = main_cover_elem.get("src", "")
                if cover_url:
                    cover_url = cover_url.replace("/m/", "/raw/").replace("/s/", "/raw/").replace("https://", "http://")
                result["main_cover_url"] = cover_url
            else:
                result["main_cover_url"] = ""
            
            # 作者
            authors = []
            if info:
                # 查找包含"作者"的 span.pl 标签
                author_pl = info.find("span", class_="pl", string=re.compile("作者"))
                if author_pl:
                    # 作者链接在父级 span 中
                    parent_span = author_pl.parent
                    if parent_span:
                        authors = [a.text.strip() for a in parent_span.select("a")]
            result["authors"] = authors
            
            # 译者
            translators = []
            if info:
                translator_pl = info.find("span", class_="pl", string=re.compile("译者"))
                if translator_pl:
                    parent_span = translator_pl.parent
                    if parent_span:
                        translators = [a.text.strip() for a in parent_span.select("a")]
            result["translators"] = translators
            
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
            recommendations = await self._get_recommendations(soup)
            result["recommendations"] = recommendations
            
            Logger.success(f"详情页爬取完成: {result.get('title', '')}")
            
        except Exception as e:
            Logger.error(f"解析详情页失败: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"豆瓣数据解析失败: {e}")
            
        return result
        
    async def _get_recommendations(self, soup: BeautifulSoup) -> List[Dict]:
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
                        "rating": rating
                    })
                except:
                    continue
        except Exception as e:
            Logger.warning(f"获取相关推荐失败: {e}")
        return recommendations
        
    async def crawl_comments(self, douban_id: str, count: int = 20) -> List[Dict]:
        """
        爬取短评（按热度排序）
        
        Args:
            douban_id: 豆瓣书籍 ID
            count: 爬取数量
            
        Returns:
            短评列表
        """
        Logger.info(f"正在爬取短评: {douban_id}")
        
        comments = []
        
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/comments"
        await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        # 检查反爬
        if "sorry" in self.page.url or "misc" in self.page.url:
            await self._handle_anti_crawl()
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        try:
            hot_sort_btn = await self.page.query_selector("a[href*='sort=new_score']")
            if hot_sort_btn:
                await hot_sort_btn.click()
                await asyncio.sleep(1)
        except:
            pass
        
        start = 0
        while len(comments) < count:
            page_url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/comments?start={start}&limit=20&sort=new_score&status=P"
            
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
                                
                    votes_elem = item.select_one(".votes.vote-count")
                    votes = votes_elem.text.strip() if votes_elem else "0"
                    
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
                        "votes": int(votes),
                        "url": None,
                        "title": None
                    })
                    
                except Exception as e:
                    continue
                    
            start += 20
            await asyncio.sleep(config.PAGE_DELAY)
            
        comments = comments[:count]
        Logger.success(f"获取 {len(comments)} 条短评")
        return comments
        
    async def crawl_reviews(self, douban_id: str, count: int = 20) -> List[Dict]:
        """
        爬取长评（按热度排序）
        
        Args:
            douban_id: 豆瓣书籍 ID
            count: 爬取数量
            
        Returns:
            长评列表
        """
        Logger.info(f"正在爬取长评: {douban_id}")
        
        reviews = []
        
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/reviews"
        await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        # 检查反爬
        if "sorry" in self.page.url or "misc" in self.page.url:
            await self._handle_anti_crawl()
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        try:
            sort_btn = await self.page.query_selector("a[href*='sort=hot']")
            if sort_btn:
                await sort_btn.click()
                await asyncio.sleep(1)
        except:
            pass
        
        start = 0
        while len(reviews) < count:
            page_url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/reviews?start={start}&sort=hot"
            
            await self.page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            items = soup.select(".review-list article")
            if not items:
                items = soup.select(".review-item")
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
                        "votes": int(votes) if votes.isdigit() else 0
                    })
                    
                    if len(reviews) >= count:
                        break
                        
                except Exception as e:
                    Logger.warning(f"解析长评失败: {e}")
                    continue
                    
            start += 20
            await asyncio.sleep(config.PAGE_DELAY)
            
        reviews = reviews[:count]
        Logger.success(f"获取 {len(reviews)} 篇长评")
        return reviews
        
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
            Logger.warning(f"获取长评内容失败: {e}")
            return ""
