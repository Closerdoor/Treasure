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
            # 使用系统 Chrome
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
        
        # 配置代理
        context_options = {
            "user_agent": user_agent,
            "viewport": {"width": 1920, "height": 1080}
        }
        
        if config.PROXY_ENABLED and config.PROXY_URL:
            context_options["proxy"] = {"server": config.PROXY_URL}
            Logger.info(f"使用代理: {config.PROXY_URL}")
        
        self.context = await self.browser.new_context(**context_options)
        
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
            try:
                await self.page.goto(config.DOUBAN_BASE_URL, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                
                await self.page.wait_for_selector(".nav-user-account", timeout=5000)
                Logger.info("登录状态有效")
                return
            except Exception as e:
                Logger.warning(f"Cookie 验证失败: {e}")
                # 检查浏览器是否还在运行
                if not self.browser or not self.page:
                    Logger.error("浏览器连接已断开，请重新运行")
                    raise Exception("浏览器连接已断开")
        
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
    
    async def search_douban_id(self, movie_name: str, year: int = None) -> Dict[str, Any]:
        """
        通过百度搜索获取豆瓣 ID
        
        Args:
            movie_name: 影片名称
            year: 年份（可选，用于验证）
            
        Returns:
            {
                'doubanId': '3205624',
                'doubanUrl': 'https://movie.douban.com/subject/3205624/',
                'title': '社交网络',
                'year': 2010,
                'source': 'baidu_search'
            }
        """
        Logger.info(f"正在通过百度搜索获取豆瓣 ID: {movie_name}")
        
        # 搜索百度
        search_query = f"{movie_name} 豆瓣"
        baidu_url = f"https://www.baidu.com/s?wd={search_query}"
        
        await self.page.goto(baidu_url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        # 提取搜索结果中的豆瓣链接
        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        candidates = []
        
        # 查找所有豆瓣电影链接（支持多种格式）
        # 格式1: movie.douban.com/subject/数字
        # 格式2: m.douban.com/movie/subject/数字
        for pattern in [
            r'movie\.douban\.com/subject/(\d+)',
            r'm\.douban\.com/movie/subject/(\d+)'
        ]:
            for match in re.finditer(pattern, content):
                douban_id = match.group(1)
                douban_url = f"https://movie.douban.com/subject/{douban_id}/"
                if douban_url not in [c['doubanUrl'] for c in candidates]:
                    candidates.append({
                        'doubanId': douban_id,
                        'doubanUrl': douban_url,
                        'title': None,
                        'year': None
                    })
        
        if not candidates:
            Logger.error(f"未找到豆瓣链接: {movie_name}")
            raise Exception(f"通过百度搜索未找到 {movie_name} 的豆瓣页面")
        
        Logger.info(f"找到 {len(candidates)} 个候选豆瓣链接")
        
        # 验证每个候选页面
        validated_candidates = []
        for candidate in candidates:
            try:
                validated = await self._validate_douban_page(candidate, movie_name, year)
                if validated:
                    validated_candidates.append(validated)
            except Exception as e:
                Logger.warning(f"验证失败 {candidate['doubanUrl']}: {e}")
                continue
        
        if not validated_candidates:
            Logger.error(f"所有候选页面验证失败")
            raise Exception(f"未找到匹配的豆瓣页面: {movie_name}")
        
        # 如果只有一个匹配，直接返回
        if len(validated_candidates) == 1:
            Logger.success(f"找到豆瓣页面: {validated_candidates[0]['title']} ({validated_candidates[0]['doubanId']})")
            return validated_candidates[0]
        
        # 多个匹配，选择第一个（年份最接近的）
        Logger.warning(f"找到多个匹配的豆瓣页面，选择第一个")
        for c in validated_candidates:
            Logger.info(f"  - {c['title']} ({c['year']}) - {c['doubanUrl']}")
        
        return validated_candidates[0]
    
    async def _validate_douban_page(self, candidate: Dict, expected_title: str, expected_year: int = None) -> Optional[Dict]:
        """
        验证豆瓣页面是否匹配
        
        Args:
            candidate: 候选信息 {'doubanId', 'doubanUrl'}
            expected_title: 期望的标题
            expected_year: 期望的年份（可选）
            
        Returns:
            验证通过返回完整信息，否则返回 None
        """
        Logger.info(f"验证豆瓣页面: {candidate['doubanUrl']}")
        
        await self.page.goto(candidate['doubanUrl'], timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        # 检查是否需要登录/验证码/反爬页面
        content = await self.page.content()
        current_url = self.page.url
        needs_user_action = False
        
        if "验证码" in content:
            needs_user_action = True
        elif "登录" in content and "movie.douban.com" not in current_url:
            needs_user_action = True
        elif "嗯…" in content or "页面不存在" in content:
            needs_user_action = True
        
        if needs_user_action:
            Logger.warning("页面需要登录/验证码，等待用户处理...")
            await self._wait_for_user_action()
            content = await self.page.content()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # 提取标题
        title_elem = soup.select_one('h1 span[property="v:itemreviewed"]')
        if not title_elem:
            title_elem = soup.select_one('h1')
        if not title_elem:
            return None
        
        page_title = title_elem.get_text(strip=True)
        
        # 提取年份
        year_elem = soup.select_one('.year')
        page_year = None
        if year_elem:
            year_match = re.search(r'(\d{4})', year_elem.get_text())
            if year_match:
                page_year = int(year_match.group(1))
        
        # 验证标题匹配
        if expected_title.lower() not in page_title.lower() and page_title.lower() not in expected_title.lower():
            Logger.warning(f"标题不匹配: 页面 '{page_title}' vs 期望 '{expected_title}'")
            return None
        
        # 验证年份（如果提供）
        if expected_year and page_year and page_year != expected_year:
            Logger.warning(f"年份不匹配: 页面 {page_year} vs 期望 {expected_year}")
            return None
        
        return {
            'doubanId': candidate['doubanId'],
            'doubanUrl': candidate['doubanUrl'],
            'title': page_title,
            'year': page_year,
            'source': 'baidu_search'
        }
    
    async def _wait_for_user_action(self, timeout: int = 300):
        """等待用户处理登录/验证码"""
        print("\n" + "=" * 50)
        print("请在浏览器中完成登录/验证码")
        print("完成后按回车继续...")
        print("=" * 50 + "\n")
        
        waited = 0
        while waited < timeout:
            await asyncio.sleep(1)
            waited += 1
            
            # 检查页面是否已经正常
            try:
                if not self.page or not self.browser:
                    Logger.warning("浏览器已断开，正在重新启动...")
                    await self.init_browser()
                    await self.load_cookies()
                    await self.page.goto(config.DOUBAN_BASE_URL, timeout=60000, wait_until="domcontentloaded")
                    await asyncio.sleep(2)
                    return
                
                url = self.page.url
                if "movie.douban.com/subject" in url:
                    content = await self.page.content()
                    if "验证码" not in content and "嗯…" not in content:
                        Logger.info("用户已完成验证")
                        return
            except Exception as e:
                Logger.warning(f"检查验证状态失败: {e}")
                try:
                    if not self.browser or not self.browser.is_connected():
                        Logger.warning("浏览器已断开，正在重新启动...")
                        await self.init_browser()
                        await self.load_cookies()
                        await self.page.goto(config.DOUBAN_BASE_URL, timeout=60000, wait_until="domcontentloaded")
                        await asyncio.sleep(2)
                        return
                except Exception as e2:
                    Logger.error(f"重新启动浏览器失败: {e2}")
                    raise Exception("浏览器无法恢复，请重新运行程序")
        
        raise Exception("等待用户操作超时")
        
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def crawl_detail(self, douban_id: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        爬取电影详情页
        
        豆瓣是中文信息最全面的来源，必须确保成功获取。
        如果失败，会进行重试，最多 3 次。
        
        Args:
            douban_id: 豆瓣电影 ID
            max_retries: 最大重试次数
            
        Returns:
            电影详情数据
            
        Raises:
            Exception: 如果重试后仍然失败，抛出异常，停止整个爬取流程
        """
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/"
        
        # 先访问豆瓣首页，建立会话后再跳转详情页
        Logger.info("先访问豆瓣首页建立会话...")
        await self.page.goto(config.DOUBAN_BASE_URL, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(3, 6))
        
        # 重试机制：5秒 -> 10秒 -> 30秒
        retry_intervals = [5, 10, 30]
        
        for attempt in range(max_retries):
            try:
                Logger.info(f"正在爬取详情页: {url} (尝试 {attempt + 1}/{max_retries})")
                
                await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                
                # 检查是否被重定向到错误页面
                current_url = self.page.url
                if "error" in current_url or "404" in current_url:
                    raise Exception(f"页面不存在或被重定向: {current_url}")
                
                content = await self.page.content()
                
                if "嗯…" in content or "验证码" in content:
                    Logger.warning("遇到反爬/验证码页面，等待用户处理...")
                    await self._wait_for_user_action()
                    content = await self.page.content()
                
                soup = BeautifulSoup(content, "html.parser")
                
                # 检查是否获取到有效数据
                title_elem = soup.select_one("h1 span[property='v:itemreviewed']")
                if not title_elem:
                    raise Exception("未能获取到标题，页面可能未正确加载")
                
                # 如果成功，跳出重试循环
                break
                
            except Exception as e:
                Logger.error(f"豆瓣爬取失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = retry_intervals[attempt]
                    Logger.info(f"等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    # 最后一次重试失败，抛出异常
                    Logger.error(f"豆瓣爬取失败，已重试 {max_retries} 次，停止爬取流程")
                    raise Exception(f"豆瓣爬取失败: {douban_id} - {e}")
        
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
            result["series"] = await self._get_series_subjects(soup, douban_id)
            
            Logger.success(f"详情页爬取完成: {result.get('title', '')}")
            
            # 验证数据完整性
            self._validate_douban_data(result)
            
        except Exception as e:
            Logger.error(f"解析详情页失败: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"豆瓣数据解析失败: {e}")
            
        return result
    
    def _validate_douban_data(self, data: Dict[str, Any]):
        """
        验证豆瓣数据完整性
        
        豆瓣是核心数据源，必须确保关键字段存在
        
        Args:
            data: 豆瓣数据
            
        Raises:
            Exception: 如果关键字段缺失
        """
        required_fields = ["title", "directors", "casts"]
        missing_fields = []
        
        for field in required_fields:
            if not data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            Logger.warning(f"豆瓣数据不完整，缺失字段: {missing_fields}")
            # 豆瓣数据不完整时，记录警告但不抛出异常
            # 因为有些电影可能确实没有某些信息（如纪录片可能没有演员）
        
        # 检查演员数量
        cast_count = len(data.get("casts", []))
        if cast_count == 0:
            Logger.warning(f"豆瓣演员列表为空")
        else:
            Logger.info(f"豆瓣演员数量: {cast_count}")
        
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
                    
                    # 从 URL 提取豆瓣 subject ID
                    # URL 格式: https://movie.douban.com/subject/1292052/
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

    async def _get_series_subjects(self, soup: BeautifulSoup, douban_id: str) -> List[Dict[str, Any]]:
        """提取详情页中明确属于系列/相关条目的豆瓣作品链接。"""
        series = []
        seen = set()
        section_keywords = ("系列", "续集", "前作", "后作", "相关电影", "相关影片", "相关作品")

        try:
            for header in soup.find_all(["h2", "h3"]):
                header_text = header.get_text(" ", strip=True)
                if not any(keyword in header_text for keyword in section_keywords):
                    continue

                section = header.find_parent(["section", "div"]) or header.parent
                for anchor in section.select("a[href*='/subject/']"):
                    href = anchor.get("href", "")
                    match = re.search(r"/subject/(\d+)", href)
                    if not match:
                        continue
                    source_id = match.group(1)
                    if source_id == str(douban_id) or source_id in seen:
                        continue

                    title = (
                        anchor.get("title")
                        or anchor.get_text(" ", strip=True)
                        or (anchor.select_one("img").get("alt", "").strip() if anchor.select_one("img") else "")
                    )
                    if not title:
                        continue

                    seen.add(source_id)
                    series.append({
                        "title": title,
                        "source": "douban",
                        "sourceId": source_id,
                        "url": urljoin(config.DOUBAN_BASE_URL, href),
                        "section": header_text
                    })

            Logger.info(f"豆瓣系列/相关作品 {len(series)} 条")
        except Exception as e:
            Logger.warning(f"获取豆瓣系列/相关作品失败: {e}")

        return series
    
    async def crawl_celebrities(self, douban_id: str) -> Dict[str, List[Dict]]:
        """
        爬取演职员页面（/celebrities）
        
        豆瓣演职员页面包含完整的演职员列表，包括：
        - 导演、编剧、主演、全部演员
        - 中英文名
        - 角色名（中英文）
        - 豆瓣人物 ID
        
        Args:
            douban_id: 豆瓣电影 ID
            
        Returns:
            演职员数据
        """
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/celebrities"
        Logger.info(f"正在爬取演职员页面: {url}")
        
        result = {
            "directors": [],
            "writers": [],
            "cast": [],
            "source": "douban",
            "source_url": url
        }
        
        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(5)  # 等待页面完全加载
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 查找演职员列表
            celebrities = soup.select(".celebrities-list .celebrity")
            
            if not celebrities:
                Logger.warning("未找到演职员列表")
                return result
            
            Logger.info(f"找到 {len(celebrities)} 个演职员")
            
            for celeb in celebrities:
                try:
                    # 类型（导演/编剧/演员）
                    role_elem = celeb.select_one(".role")
                    role_text = role_elem.text.strip() if role_elem else ""
                    
                    # 名字（中英文）
                    name_elem = celeb.select_one(".name a")
                    if not name_elem:
                        continue
                    
                    name_text = name_elem.text.strip()
                    
                    # 分离中英文名
                    # 豆瓣格式: "中文名 英文名" 或 "中文名"
                    # 如: "弗兰克·德拉邦特 Frank Darabont"
                    name_parts = name_text.split()
                    name_cn = name_parts[0] if name_parts else name_text
                    
                    # 英文名可能是多个单词（如 "Frank Darabont"）
                    name_en = None
                    if len(name_parts) > 1:
                        # 检查第一个部分是否是中文
                        first_part = name_parts[0]
                        if re.match(r'[\u4e00-\u9fa5]', first_part):
                            # 第一个是中文，剩余的是英文
                            name_en = ' '.join(name_parts[1:])
                        else:
                            # 全部是英文
                            name_en = name_text
                    
                    # 豆瓣人物 ID
                    href = name_elem.get("href", "")
                    douban_celeb_id = None
                    if href:
                        match = re.search(r"/celebrity/(\d+)", href)
                        if match:
                            douban_celeb_id = match.group(1)
                    
                    # 角色名（从 role_text 提取）
                    character = None
                    character_en = None
                    
                    if "演员" in role_text and "(" in role_text:
                        # 格式: 演员 (饰 角色名 CharacterName)
                        char_match = re.search(r"饰\s+([^)]+)", role_text)
                        if char_match:
                            char_text = char_match.group(1).strip()
                            # 分离中英文角色名
                            char_parts = re.split(r'\s+', char_text, maxsplit=1)
                            character = char_parts[0]
                            if len(char_parts) > 1:
                                character_en = char_parts[1]
                    
                    # 头像（豆瓣使用 background-image）
                    avatar_elem = celeb.select_one(".avatar")
                    avatar_url = None
                    if avatar_elem:
                        style = avatar_elem.get("style", "")
                        if style:
                            # 提取 background-image URL
                            match = re.search(r"url\(([^)]+)\)", style)
                            if match:
                                avatar_url = match.group(1)
                                # 转换为原图 URL
                                avatar_url = avatar_url.replace("/m/", "/raw/").replace("/s/", "/raw/")
                    
                    entry = {
                        "name": name_cn,
                        "nameEn": name_en,
                        "doubanId": douban_celeb_id,
                        "character": character,
                        "characterEn": character_en,
                        "avatar": avatar_url,
                        "role": role_text
                    }
                    
                    # 根据角色分类
                    if "导演" in role_text:
                        result["directors"].append(entry)
                    elif "编剧" in role_text:
                        result["writers"].append(entry)
                    elif "演员" in role_text:
                        result["cast"].append(entry)
                        
                except Exception as e:
                    Logger.warning(f"解析演职员失败: {e}")
                    continue
            
            Logger.success(f"演职员页面爬取完成: 导演 {len(result['directors'])} 人, "
                          f"编剧 {len(result['writers'])} 人, "
                          f"演员 {len(result['cast'])} 人")
            
        except Exception as e:
            Logger.error(f"演职员页面爬取失败: {e}")
        
        return result
        
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
            page_url = (
                f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/comments"
                f"?percent_type=h&limit=20&status=P&sort=new_score&start={start}"
            )
            
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
                    votes_num = int(re.sub(r"\D", "", votes) or 0)
                    
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
                        "votes": votes_num,
                        "url": page_url,
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
                    
                    # 列表页按 sort=hot 获取热度最高条目，正文进入详情页读取完整内容。
                    full_content = await self._get_review_content(review_url)
                    
                    # 作者
                    author_elem = (
                        item.select_one(".main-hd a.name")
                        or item.select_one(".author a")
                        or item.select_one(".review-meta a")
                        or item.select_one(".main-hd a")
                    )
                    author = author_elem.text.strip() if author_elem else ""
                    
                    # 时间
                    time_elem = (
                        item.select_one(".main-meta")
                        or item.select_one(".date")
                        or item.select_one(".review-meta time")
                    )
                    review_time = time_elem.text.strip() if time_elem else ""
                    
                    # 有用数
                    votes_elem = (
                        item.select_one(".action-btn.up span")
                        or item.select_one(".votes")
                        or item.select_one(".up span")
                    )
                    votes = "0"
                    if votes_elem:
                        votes = votes_elem.text.strip()
                    votes_num = int(re.sub(r"\D", "", votes) or 0)
                    
                    reviews.append({
                        "author": author,
                        "source": "豆瓣长评",
                        "date": review_time,
                        "content": full_content,
                        "url": review_url,
                        "title": title,
                        "votes": votes_num
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
        new_page = None
        try:
            # 在新标签页打开
            new_page = await self.context.new_page()
            await new_page.goto(review_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(0.5, 1.5))

            for text in ["展开", "更多", "显示全部"]:
                try:
                    locator = new_page.get_by_text(text, exact=False).first
                    if await locator.count():
                        await locator.click(timeout=1000)
                        await asyncio.sleep(0.3)
                except Exception:
                    pass
            
            content = await new_page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 获取影评正文
            review_body = (
                soup.select_one(".review-content span.all")
                or soup.select_one(".review-content .all")
                or soup.select_one(".review-content")
                or soup.select_one("#link-report")
            )
            text = review_body.text.strip() if review_body else ""
            
            return text
            
        except Exception as e:
            Logger.warning(f"获取影评内容失败: {e}")
            return ""
        finally:
            if new_page:
                await new_page.close()
            
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
            "all_photos_url": f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/all_photos",
            "all_photos_total": 0,
            "other_total": 0,
            "posters": [],
            "stills": [],
            "wallpapers": [],
            "posters_total": 0,
            "stills_total": 0,
            "wallpapers_total": 0
        }

        try:
            await self.page.goto(result["all_photos_url"], timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            await self._handle_douban_block_if_needed()
            content = await self.page.content()
            result["all_photos_total"] = self._extract_photo_count(BeautifulSoup(content, "html.parser"))
        except Exception as e:
            Logger.warning(f"访问图片总页失败: {e}")

        categories = {
            "stills": ("S", "still"),
            "posters": ("R", "poster"),
            "wallpapers": ("W", "wallpaper")
        }
        for key, (type_code, image_type) in categories.items():
            data = await self._crawl_photo_category(douban_id, type_code, image_type)
            result[key] = data["items"]
            result[f"{key}_total"] = data["total"]
            result[f"{key}_url"] = data["url"]

        category_total = result["stills_total"] + result["posters_total"] + result["wallpapers_total"]
        if result["all_photos_total"]:
            result["other_total"] = max(result["all_photos_total"] - category_total, 0)

        Logger.success(
            f"获取剧照 {len(result['stills'])}/{result['stills_total']} 张，"
            f"海报 {len(result['posters'])}/{result['posters_total']} 张，"
            f"壁纸 {len(result['wallpapers'])}/{result['wallpapers_total']} 张"
        )
        return result

    def _extract_photo_count(self, soup: BeautifulSoup) -> int:
        count_elem = soup.select_one(".count")
        if not count_elem:
            return 0
        count_match = re.search(r"共\s*(\d+)\s*张", count_elem.text.strip())
        return int(count_match.group(1)) if count_match else 0

    async def _crawl_photo_category(self, douban_id: str, type_code: str, image_type: str) -> Dict[str, Any]:
        """按豆瓣图片分类分页抓取；不设置人工数量上限，直到页面没有新图或达到总数。"""
        items = []
        seen = set()
        total = 0
        start = 0
        page_count = 0
        base_url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/photos?type={type_code}"

        while True:
            page_url = (
                f"{base_url}&start={start}&sortby=like&size=a&subtype=a"
                if start else base_url
            )
            await self.page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            await self._handle_douban_block_if_needed()
            page_count += 1

            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            if not total:
                total = self._extract_photo_count(soup)

            page_items = []
            for item in soup.select(".cover a"):
                img_elem = item.select_one("img")
                if not img_elem:
                    continue

                thumb_url = img_elem.get("src", "")
                if not thumb_url or thumb_url in seen:
                    continue

                seen.add(thumb_url)
                origin_url = self._normalize_douban_image_url(thumb_url)
                photo_url = urljoin(config.DOUBAN_BASE_URL, item.get("href", ""))
                page_items.append({
                    "thumb_url": thumb_url,
                    "origin_url": origin_url,
                    "photo_url": photo_url,
                    "title": img_elem.get("alt", "").strip(),
                    "type": image_type,
                    "index": len(items) + len(page_items) + 1
                })

            if not page_items:
                break

            items.extend(page_items)
            if page_count == 1 or page_count % 10 == 0:
                Logger.info(f"图片分类 {type_code} 已抓取 {len(items)}/{total or '?'} 张")
            if total and len(items) >= total:
                break

            start += len(page_items)

        return {"items": items, "total": total or len(items), "url": base_url}

    async def _handle_douban_block_if_needed(self):
        current_url = self.page.url
        content = await self.page.content()
        if "douban.com/misc/sorry" not in current_url and "证明你是人类" not in content and "像机器人程序" not in content:
            return

        Logger.warning("豆瓣触发机器人验证，请在浏览器中点击证明后继续")
        await self._wait_for_user_action()
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

    def _normalize_douban_image_url(self, thumb_url: str) -> str:
        """把豆瓣缩略图地址转换为原图候选地址。"""
        return (
            thumb_url
            .replace("/m/", "/raw/")
            .replace("/s/", "/raw/")
            .replace("https://", "http://")
        )

    async def crawl_trailers(self, douban_id: str) -> List[Dict[str, Any]]:
        """爬取豆瓣视频页中的预告片/视频条目。"""
        Logger.info(f"正在爬取视频: {douban_id}")
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/trailer"
        await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

        content = await self.page.content()
        soup = BeautifulSoup(content, "html.parser")
        trailers = []
        seen = set()

        for anchor in soup.select("a[href*='/trailer/']"):
            href = anchor.get("href", "")
            trailer_url = urljoin(config.DOUBAN_BASE_URL, href)
            trailer_id_match = re.search(r"/trailer/(\d+)", trailer_url)
            if not trailer_url or not trailer_id_match:
                continue
            trailer_id = trailer_id_match.group(1)
            if trailer_id in seen:
                continue
            if "#" in trailer_url and "#content" not in trailer_url:
                continue

            parent = anchor.find_parent(["li", "div", "article"]) or anchor
            img_elem = parent.select_one("img") or anchor.select_one("img")
            parent_text = " ".join(parent.get_text(" ", strip=True).split())
            title = (
                anchor.get("title")
                or (img_elem.get("alt") if img_elem else "")
                or anchor.get_text(" ", strip=True)
                or parent_text
            ).strip()
            duration_match = re.search(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", parent_text)
            if duration_match and title == duration_match.group(0):
                title = parent_text.replace(duration_match.group(0), "").strip() or title

            seen.add(trailer_id)
            trailers.append({
                "title": title,
                "url": trailer_url,
                "thumbnail": self._normalize_douban_image_url(img_elem.get("src", "")) if img_elem else "",
                "duration": duration_match.group(0) if duration_match else "",
                "source": "douban",
                "source_url": url,
                "trailerId": trailer_id
            })

        Logger.success(f"获取视频 {len(trailers)} 条")
        return trailers
        
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
        
    async def crawl_all(self, douban_id: str, comments_count: int = 20, reviews_count: int = 20) -> Dict[str, Any]:
        """
        一次性采集豆瓣所有数据（详情 + 演职员 + 视频 + 图片 + 短评 + 影评）
        
        在同一个浏览器会话中顺序访问各页面，避免重复登录。
        
        Args:
            douban_id: 豆瓣电影 ID
            comments_count: 短评数量
            reviews_count: 影评数量
            
        Returns:
            完整豆瓣数据
        """
        Logger.info(f"开始一次性采集豆瓣数据: {douban_id}")
        
        result = {
            "douban_id": douban_id,
            "source": "douban"
        }
        
        # 1. 详情页
        try:
            detail = await self.crawl_detail(douban_id)
            result["detail"] = detail
        except Exception as e:
            Logger.error(f"豆瓣详情爬取失败: {e}")
            result["detail"] = {}
        
        # 2. 演职员页面
        try:
            celebrities = await self.crawl_celebrities(douban_id)
            result["celebrities"] = celebrities
        except Exception as e:
            Logger.error(f"豆瓣演职员爬取失败: {e}")
            result["celebrities"] = {"directors": [], "writers": [], "cast": []}
        
        # 3. 短评
        try:
            comments = await self.crawl_comments(douban_id, comments_count)
            result["comments"] = comments
        except Exception as e:
            Logger.error(f"豆瓣短评爬取失败: {e}")
            result["comments"] = []
        
        # 4. 影评
        try:
            reviews = await self.crawl_reviews(douban_id, reviews_count)
            result["reviews"] = reviews
        except Exception as e:
            Logger.error(f"豆瓣影评爬取失败: {e}")
            result["reviews"] = []
        
        # 5. 视频
        try:
            trailers = await self.crawl_trailers(douban_id)
            result["trailers"] = trailers
        except Exception as e:
            Logger.error(f"豆瓣视频爬取失败: {e}")
            result["trailers"] = []

        # 6. 图片（剧照 + 海报 + 壁纸列表）
        try:
            images = await self.crawl_images(douban_id)
            result["images"] = images
        except Exception as e:
            Logger.error(f"豆瓣图片爬取失败: {e}")
            result["images"] = {
                "posters": [],
                "stills": [],
                "wallpapers": [],
                "posters_total": 0,
                "stills_total": 0,
                "wallpapers_total": 0
            }
        
        Logger.success(f"豆瓣数据采集完成: {douban_id}")
        return result
