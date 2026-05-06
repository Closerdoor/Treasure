# -*- coding: utf-8 -*-
"""
豆瓣爬虫模块
"""
import asyncio
import json
import random
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

import config
from utils import Logger


class DoubanCrawler:
    """豆瓣爬虫"""
    
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
            if config.USE_CHROME and hasattr(config, 'CHROME_PATH'):
                self.browser = await self.playwright.chromium.launch(
                    headless=config.HEADLESS,
                    slow_mo=config.SLOW_MO,
                    executable_path=config.CHROME_PATH
                )
            else:
                self.browser = await self.playwright.chromium.launch(
                    headless=config.HEADLESS,
                    slow_mo=config.SLOW_MO
                )
        except Exception as e:
            Logger.error(f"浏览器启动失败: {e}")
            raise
        
        user_agent = random.choice(config.USER_AGENTS)
        self.context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080}
        )
        
        self.page = await self.context.new_page()
        Logger.info(f"浏览器已启动")
        
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
        if await self.load_cookies():
            await self.page.goto(config.DOUBAN_BASE_URL, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            try:
                await self.page.wait_for_selector(".nav-user-account", timeout=5000)
                Logger.info("登录状态有效")
                return
            except:
                Logger.warning("Cookie 已过期，需要重新登录")
        
        print("\n" + "="*50)
        print("请在打开的浏览器中手动登录豆瓣")
        print("登录成功后，程序将自动检测...")
        print("="*50 + "\n")
        
        await self.page.goto(config.DOUBAN_LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
        
        # 自动检测登录状态
        max_wait = 300  # 5 分钟
        check_interval = 5
        waited = 0
        
        while waited < max_wait:
            await asyncio.sleep(check_interval)
            waited += check_interval
            
            try:
                # 检查是否登录成功
                current_url = self.page.url
                if "accounts.douban.com" not in current_url:
                    # 已经跳转离开登录页，检查登录状态
                    await self.page.goto(config.DOUBAN_BASE_URL, timeout=10000, wait_until="domcontentloaded")
                    await self.page.wait_for_selector(".nav-user-account", timeout=3000)
                    
                    # 登录成功
                    await self.save_cookies()
                    Logger.success("登录成功！")
                    return
            except:
                # 未登录，继续等待
                if waited % 30 == 0:
                    print(f"已等待 {waited} 秒，请继续登录...")
                continue
        
        raise Exception("登录超时，请重新运行程序")
        
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def crawl_detail(self, douban_id: str) -> Dict[str, Any]:
        """
        爬取电影详情页
        
        Args:
            douban_id: 豆瓣电影 ID
            
        Returns:
            电影详情数据
        """
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/"
        Logger.info(f"正在爬取详情页: {url}")
        
        try:
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            Logger.error(f"页面加载超时，重试: {e}")
            await asyncio.sleep(5)
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        content = await self.page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        result = {
            "douban_id": douban_id,
            "url": url,
            "source": "douban"
        }
        
        try:
            # 标题（只取中文部分）
            title_elem = soup.select_one("h1 span[property='v:itemreviewed']")
            full_title = title_elem.text.strip() if title_elem else ""
            # 分离中文和英文：中文标题通常是第一个部分
            # 例如 "星际穿越 Interstellar" -> "星际穿越"
            import re as re_module
            chinese_match = re_module.match(r'^([\u4e00-\u9fa5]+)', full_title)
            if chinese_match:
                result["title"] = chinese_match.group(1)
            else:
                result["title"] = full_title.split()[0] if full_title else ""
            
            # 年份
            year_elem = soup.select_one(".year")
            result["year"] = year_elem.text.strip("()") if year_elem else ""
            
            # 获取 info 区域
            info = soup.select_one("#info")
            
            # 原名：从豆瓣 info 区域获取
            if info:
                original_title_match = re.search(r"原名:</span>([^<]+)", str(info))
                if original_title_match:
                    result["original_title"] = original_title_match.group(1).strip()
                else:
                    # 如果没有原名字段，尝试从标题中提取英文部分
                    english_match = re_module.search(r'[A-Za-z].*', full_title)
                    if english_match:
                        result["original_title"] = english_match.group(0).strip()
            
            # 评分
            rating_elem = soup.select_one("strong.rating_num")
            result["rating"] = rating_elem.text.strip() if rating_elem else ""
            
            # 评价人数
            rating_count_elem = soup.select_one("span[property='v:votes']")
            result["rating_count"] = rating_count_elem.text.strip() if rating_count_elem else "0"
            
            # 主海报（封面）
            main_poster_elem = soup.select_one("#mainpic img")
            if main_poster_elem:
                main_poster_url = main_poster_elem.get("src", "")
                # 转换为原图 URL
                if main_poster_url:
                    main_poster_url = main_poster_url.replace("/m/", "/raw/").replace("/s/", "/raw/").replace("https://", "http://")
                result["main_poster_url"] = main_poster_url
            else:
                result["main_poster_url"] = ""
            
            # 导演
            directors = [a.text.strip() for a in soup.select("a[rel='v:directedBy']")]
            result["directors"] = directors
            
            # 编剧
            writers = []
            if info:
                writer_label = info.find(string=re.compile("编剧"))
                if writer_label:
                    writer_span = writer_label.find_next("span")
                    if writer_span:
                        writers = [a.text.strip() for a in writer_span.select("a")]
            result["writers"] = writers
            
            # 主演
            casts = [a.text.strip() for a in soup.select("a[rel='v:starring']")]
            result["casts"] = casts
            
            # 类型
            genres = [span.text.strip() for span in soup.select("span[property='v:genre']")]
            result["genres"] = genres
            
            # 制片国家/地区
            if info:
                countries_match = re.search(r"制片国家/地区:</span>([^<]+)", str(info))
                result["countries"] = countries_match.group(1).strip() if countries_match else ""
                
                # 语言
                lang_match = re.search(r"语言:</span>([^<]+)", str(info))
                result["languages"] = lang_match.group(1).strip() if lang_match else ""
                
                # 上映日期（全部）
                release_dates = []
                release_elems = soup.select("span[property='v:initialReleaseDate']")
                for elem in release_elems:
                    date_text = elem.text.strip()
                    # 解析格式：2014-11-12(美国) 或 2014-11-07
                    match = re.match(r"(\d{4}-\d{2}-\d{2})(?:\((.+)\))?", date_text)
                    if match:
                        release_dates.append({
                            "date": match.group(1),
                            "location": match.group(2) or ""
                        })
                result["release_dates"] = release_dates
                
                # 片长
                runtime_elem = soup.select_one("span[property='v:runtime']")
                runtime_text = runtime_elem.text.strip() if runtime_elem else ""
                # 提取数字
                runtime_match = re.search(r"(\d+)", runtime_text)
                result["runtime_minutes"] = int(runtime_match.group(1)) if runtime_match else 0
                
                # 又名
                aka_match = re.search(r"又名:</span>([^<]+)", str(info))
                if aka_match:
                    akas = [a.strip() for a in aka_match.group(1).split("/")]
                    result["aliases"] = akas
                else:
                    result["aliases"] = []
                    
                # IMDb ID
                imdb_match = re.search(r"IMDb:</span>([^<]+)", str(info))
                result["imdb_id"] = imdb_match.group(1).strip() if imdb_match else ""
                
                # 出品公司
                company_match = re.search(r"制片公司:</span>([^<]+)", str(info))
                if company_match:
                    companies = [c.strip() for c in company_match.group(1).split("/")]
                    result["production_companies"] = companies
                else:
                    result["production_companies"] = []
            
            # 简介（豆瓣剧情简介）
            summary_elem = soup.select_one("span[property='v:summary']")
            result["summary"] = summary_elem.text.strip() if summary_elem else ""
            
            # 剧情详解：不再从豆瓣获取，改为从 Wikipedia 获取
            # story_text 将在 Wikipedia 爬取中获取
            result["story"] = ""
            
            # 标签
            tags = []
            tags_elem = soup.select(".tags-body a")
            for tag_elem in tags_elem:
                tags.append(tag_elem.text.strip())
            result["tags"] = tags
            
            # 主海报
            poster_elem = soup.select_one("#mainpic img")
            result["poster"] = poster_elem["src"] if poster_elem else ""
            
            # 相关推荐
            recommendations = await self._get_recommendations(soup)
            result["recommendations"] = recommendations
            
            Logger.success(f"详情页爬取完成: {result.get('title', '')}")
            
        except Exception as e:
            Logger.error(f"解析详情页失败: {e}")
            import traceback
            traceback.print_exc()
            
        return result
        
    async def _get_full_story(self, soup: BeautifulSoup) -> str:
        """获取完整剧情（点击展开）"""
        try:
            # 尝试点击展开按钮
            expand_btn = await self.page.query_selector("a[style*='display: none'] + a")
            if expand_btn:
                await expand_btn.click()
                await asyncio.sleep(0.5)
                content = await self.page.content()
                soup = BeautifulSoup(content, "html.parser")
                
            # 获取剧情内容
            story_elem = soup.select_one("span.all.hidden")
            if story_elem:
                return story_elem.text.strip()
            
            # 如果没有展开按钮，直接获取
            summary_elem = soup.select_one("span[property='v:summary']")
            return summary_elem.text.strip() if summary_elem else ""
            
        except Exception as e:
            Logger.warning(f"获取完整剧情失败: {e}")
            summary_elem = soup.select_one("span[property='v:summary']")
            return summary_elem.text.strip() if summary_elem else ""
            
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
                    
                    # 尝试获取评分
                    rating_elem = dl.select_one(".rating")
                    rating = ""
                    if rating_elem:
                        rating_text = rating_elem.get("class", [])
                        for cls in rating_text:
                            if "allstar" in cls:
                                rating = cls.replace("allstar", "").replace("0", "")
                                break
                    
                    recommendations.append({
                        "title": title,
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
            douban_id: 豆瓣电影 ID
            count: 爬取数量
            
        Returns:
            短评列表
        """
        Logger.info(f"正在爬取短评: {douban_id}")
        
        comments = []
        
        # 先访问短评页面，点击"热门"排序
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/comments"
        await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        # 尝试点击"热门"排序
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
                    comment_id = item.get("data-cid", "")
                    
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
        爬取影评（按热度排序，获取完整内容）
        
        Args:
            douban_id: 豆瓣电影 ID
            count: 爬取数量
            
        Returns:
            影评列表
        """
        Logger.info(f"正在爬取影评: {douban_id}")
        
        reviews = []
        
        # 访问影评页面
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/reviews"
        await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        # 尝试按热度排序
        try:
            # 查找排序选项
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
            
            # 影评列表项
            items = soup.select(".review-list article")
            if not items:
                # 尝试其他选择器
                items = soup.select(".review-item")
            if not items:
                break
                
            for item in items:
                try:
                    # 影评标题和链接
                    title_elem = item.select_one("h2 a") or item.select_one(".review-title a")
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()
                    review_url = title_elem.get("href", "")
                    
                    if not review_url:
                        continue
                    
                    # 获取完整影评内容
                    full_content = await self._get_review_content(review_url)
                    
                    # 作者
                    author_elem = item.select_one(".author a") or item.select_one(".review-meta a")
                    author = author_elem.text.strip() if author_elem else ""
                    
                    # 时间
                    time_elem = item.select_one(".date") or item.select_one(".review-meta time")
                    review_time = time_elem.text.strip() if time_elem else ""
                    
                    # 有用数
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
                    Logger.warning(f"解析影评失败: {e}")
                    continue
                    
            start += 20
            await asyncio.sleep(config.PAGE_DELAY)
            
        reviews = reviews[:count]
        Logger.success(f"获取 {len(reviews)} 篇影评")
        return reviews
        
    async def _get_review_content(self, review_url: str) -> str:
        """获取影评完整内容"""
        try:
            # 在新标签页打开
            new_page = await self.context.new_page()
            await new_page.goto(review_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            content = await new_page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 获取影评正文
            review_body = soup.select_one(".review-content") or soup.select_one("#link-report")
            text = review_body.text.strip() if review_body else ""
            
            await new_page.close()
            return text
            
        except Exception as e:
            Logger.warning(f"获取影评内容失败: {e}")
            return ""
            
    async def crawl_images(self, douban_id: str) -> Dict[str, Any]:
        """
        爬取图片列表
        
        Args:
            douban_id: 豆瓣电影 ID
            
        Returns:
            图片数据
        """
        Logger.info(f"正在爬取图片: {douban_id}")
        
        result = {
            "posters": [],
            "stills": [],
            "posters_total": 0,
            "stills_total": 0
        }
        
        # 爬取海报页面
        poster_url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/photos?type=S"
        await self.page.goto(poster_url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        content = await self.page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        # 获取海报总数
        count_elem = soup.select_one(".count")
        if count_elem:
            count_text = count_elem.text.strip()
            count_match = re.search(r"共(\d+)张", count_text)
            if count_match:
                result["posters_total"] = int(count_match.group(1))
        
        # 获取海报列表
        items = soup.select(".cover a")
        for idx, item in enumerate(items):
            try:
                img_elem = item.select_one("img")
                if not img_elem:
                    continue
                    
                thumb_url = img_elem.get("src", "")
                if not thumb_url:
                    continue
                    
                # 转换为原图 URL（使用 HTTP 避免 SSL 问题）
                origin_url = thumb_url.replace("/m/", "/raw/").replace("https://", "http://")
                
                image_data = {
                    "thumb_url": thumb_url,
                    "origin_url": origin_url,
                    "type": "poster",
                    "index": idx + 1
                }
                
                result["posters"].append(image_data)
                    
            except Exception as e:
                continue
        
        # 爬取剧照页面
        still_url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/photos?type=T"
        await self.page.goto(still_url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        content = await self.page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        # 获取剧照总数
        count_elem = soup.select_one(".count")
        if count_elem:
            count_text = count_elem.text.strip()
            count_match = re.search(r"共(\d+)张", count_text)
            if count_match:
                result["stills_total"] = int(count_match.group(1))
        
        items = soup.select(".cover a")
        for idx, item in enumerate(items):
            try:
                img_elem = item.select_one("img")
                if not img_elem:
                    continue
                    
                thumb_url = img_elem.get("src", "")
                if not thumb_url:
                    continue
                    
                origin_url = thumb_url.replace("/m/", "/raw/").replace("https://", "http://")
                
                image_data = {
                    "thumb_url": thumb_url,
                    "origin_url": origin_url,
                    "type": "still",
                    "index": idx + 1
                }
                
                result["stills"].append(image_data)
                    
            except:
                continue
                
        Logger.success(f"获取海报 {len(result['posters'])} 张（共 {result['posters_total']} 张），剧照 {len(result['stills'])} 张（共 {result['stills_total']} 张）")
        return result
        
    async def crawl_top250(self) -> List[Dict[str, Any]]:
        """
        爬取豆瓣 TOP250 电影列表
        
        Returns:
            电影列表 [{douban_id, title, rank}, ...]
        """
        Logger.info("正在爬取豆瓣 TOP250")
        
        movies = []
        
        # TOP250 共 10 页，每页 25 部
        for start in [0, 25, 50, 75, 100, 125, 150, 175, 200, 225]:
            url = f"{config.DOUBAN_BASE_URL}/top250?start={start}"
            
            try:
                await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                
                content = await self.page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # 获取电影列表
                items = soup.select(".item")
                
                for item in items:
                    try:
                        # 排名
                        rank_elem = item.select_one(".pic em")
                        rank = int(rank_elem.text) if rank_elem else 0
                        
                        # 标题
                        title_elem = item.select_one(".title")
                        title = title_elem.text.strip() if title_elem else ""
                        
                        # 链接
                        link_elem = item.select_one("a")
                        href = link_elem.get("href", "") if link_elem else ""
                        
                        # 提取豆瓣 ID
                        douban_id = ""
                        if "/subject/" in href:
                            douban_id = href.split("/subject/")[1].rstrip("/")
                        
                        if douban_id and title:
                            movies.append({
                                "douban_id": douban_id,
                                "title": title,
                                "rank": rank
                            })
                            
                    except Exception as e:
                        Logger.warning(f"解析电影失败: {e}")
                        continue
                
                Logger.info(f"已获取 {len(movies)} 部电影")
                
                # 页面延迟
                await asyncio.sleep(config.PAGE_DELAY)
                
            except Exception as e:
                Logger.error(f"爬取 TOP250 页面失败 (start={start}): {e}")
                continue
        
        Logger.success(f"TOP250 爬取完成，共 {len(movies)} 部电影")
        return movies
        
    def _classify_image_by_ratio(self, url: str) -> str:
        """
        根据图片 URL 判断图片类型
        豆瓣图片 URL 包含尺寸信息，如 /m/ 表示中等尺寸
        海报通常是竖版（比例约 2:3），剧照通常是横版（比例约 16:9 或 4:3）
        """
        # 简单判断：海报 URL 通常包含 "poster" 或是竖版
        # 这里返回 "poster" 或 "still"，实际需要根据图片尺寸判断
        # 由于无法直接获取尺寸，暂时全部返回 poster，后续下载时再分类
        return "poster"
