# -*- coding: utf-8 -*-
"""
豆瓣电影 TOP250 爬虫
功能：爬取 TOP250 电影的详情、短评、影评、图片

使用方法：
1. 安装依赖：pip install playwright beautifulsoup4 httpx pandas
2. 安装浏览器：playwright install chromium
3. 运行脚本：python main.py
4. 首次运行会打开浏览器，手动登录豆瓣后按回车继续
"""

import asyncio
import json
import random
import re
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

import config


class DoubanTop250Crawler:
    """豆瓣 TOP250 爬虫主类"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.progress: dict = {}
        self.movies: list = []
        self.comments: list = []
        self.reviews: list = []
        
    async def init_browser(self):
        """初始化浏览器"""
        print("正在启动浏览器...")
        self.playwright = await async_playwright().start()
        
        try:
            if config.USE_CHROME:
                self.browser = await self.playwright.chromium.launch(
                    headless=config.HEADLESS,
                    slow_mo=config.SLOW_MO,
                    channel="chrome"
                )
            else:
                self.browser = await self.playwright.chromium.launch(
                    headless=config.HEADLESS,
                    slow_mo=config.SLOW_MO
                )
        except Exception as e:
            print(f"浏览器启动失败: {e}")
            print("请确保已安装 Chrome 浏览器，或运行: playwright install chromium")
            raise
        
        user_agent = random.choice(config.USER_AGENTS)
        self.context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080}
        )
        
        self.page = await self.context.new_page()
        print(f"浏览器已启动，User-Agent: {user_agent[:50]}...")
        
    async def load_cookies(self) -> bool:
        """加载已保存的 Cookie"""
        cookie_path = Path(config.COOKIES_FILE)
        if cookie_path.exists():
            cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
            await self.context.add_cookies(cookies)
            print("已加载保存的 Cookie")
            return True
        return False
    
    async def save_cookies(self):
        """保存 Cookie"""
        cookies = await self.context.cookies()
        Path(config.COOKIES_FILE).write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print("Cookie 已保存")
        
    async def ensure_login(self):
        """确保已登录"""
        if await self.load_cookies():
            await self.page.goto(config.BASE_URL, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            try:
                await self.page.wait_for_selector(".nav-user-account", timeout=5000)
                print("登录状态有效")
                return
            except:
                print("Cookie 已过期，需要重新登录")
        
        print("\n" + "="*50)
        print("请在打开的浏览器中手动登录豆瓣")
        print("登录成功后，回到此终端按回车继续...")
        print("="*50 + "\n")
        
        await self.page.goto(config.LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
        input("按回车继续...")
        
        await self.save_cookies()
        print("登录成功！")
        
    def load_progress(self):
        """加载爬取进度"""
        progress_path = Path(config.PROGRESS_FILE)
        if progress_path.exists():
            self.progress = json.loads(progress_path.read_text(encoding="utf-8"))
            print(f"已加载进度：{len(self.progress.get('movies_completed', []))} 部电影已完成")
        else:
            self.progress = {
                "last_update": "",
                "movies_completed": [],
                "comments_completed": {},
                "reviews_completed": {},
                "images_completed": []
            }
            
    def save_progress(self):
        """保存爬取进度"""
        self.progress["last_update"] = datetime.now().isoformat()
        Path(config.PROGRESS_FILE).write_text(
            json.dumps(self.progress, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
    def load_existing_data(self):
        """加载已存在的数据"""
        movies_path = Path(config.MOVIES_JSON)
        if movies_path.exists():
            self.movies = json.loads(movies_path.read_text(encoding="utf-8"))
            print(f"已加载 {len(self.movies)} 部电影数据")
            
        comments_path = Path(config.COMMENTS_JSON)
        if comments_path.exists():
            self.comments = json.loads(comments_path.read_text(encoding="utf-8"))
            print(f"已加载 {len(self.comments)} 条短评数据")
            
        reviews_path = Path(config.REVIEWS_JSON)
        if reviews_path.exists():
            self.reviews = json.loads(reviews_path.read_text(encoding="utf-8"))
            print(f"已加载 {len(self.reviews)} 篇影评数据")
            
    async def crawl_top250_list(self) -> list:
        """爬取 TOP250 列表"""
        print("\n" + "="*50)
        print("Step 1: 爬取 TOP250 列表")
        print("="*50)
        
        movie_list = []
        
        for page_num in range(10):
            start = page_num * 25
            url = f"{config.TOP250_URL}?start={start}"
            
            print(f"正在爬取第 {page_num + 1}/10 页: {url}")
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            items = soup.select(".grid_view .item")
            for item in items:
                try:
                    rank = item.select_one(".pic em").text.strip()
                    title_elem = item.select_one(".hd a")
                    title = title_elem.select_one(".title").text.strip()
                    url = title_elem["href"]
                    movie_id = re.search(r"/subject/(\d+)", url).group(1)
                    
                    rating_elem = item.select_one(".rating_num")
                    rating = rating_elem.text.strip() if rating_elem else ""
                    
                    rating_count_elem = item.select_one(".star span:last-child")
                    rating_count = rating_count_elem.text.strip().replace("人评价", "") if rating_count_elem else "0"
                    
                    movie_list.append({
                        "id": movie_id,
                        "rank": int(rank),
                        "title": title,
                        "rating": rating,
                        "rating_count": rating_count,
                        "url": url
                    })
                except Exception as e:
                    print(f"解析电影条目失败: {e}")
                    continue
                    
            print(f"第 {page_num + 1} 页完成，已获取 {len(movie_list)} 部电影")
            
            if page_num < 9:
                await asyncio.sleep(config.PAGE_DELAY)
                
        print(f"\nTOP250 列表爬取完成，共 {len(movie_list)} 部电影")
        return movie_list
    
    async def crawl_movie_detail(self, movie: dict) -> dict:
        """爬取电影详情页"""
        movie_id = movie["id"]
        
        if movie_id in self.progress.get("movies_completed", []):
            print(f"跳过已完成: {movie['title']}")
            return None
            
        print(f"正在爬取详情: {movie['title']} (#{movie['rank']})")
        
        url = movie["url"]
        try:
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"页面加载超时，重试: {e}")
            await asyncio.sleep(5)
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        content = await self.page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        try:
            info = soup.select_one("#info")
            year_elem = soup.select_one(".year")
            year = year_elem.text.strip("()") if year_elem else ""
            
            summary_elem = soup.select_one("span[property='v:summary']")
            summary = summary_elem.text.strip() if summary_elem else ""
            
            poster_elem = soup.select_one("#mainpic img")
            poster = poster_elem["src"] if poster_elem else ""
            
            directors = [a.text.strip() for a in soup.select("a[rel='v:directedBy']")]
            
            writers = []
            writer_label = info.find(string=re.compile("编剧"))
            if writer_label:
                writer_span = writer_label.find_next("span")
                if writer_span:
                    writers = [a.text.strip() for a in writer_span.select("a")]
            
            casts = [a.text.strip() for a in soup.select("a[rel='v:starring']")]
            genres = [span.text.strip() for span in soup.select("span[property='v:genre']")]
            
            countries = ""
            countries_match = re.search(r"制片国家/地区:</span>([^<]+)", str(info))
            if countries_match:
                countries = countries_match.group(1).strip()
                
            languages = ""
            lang_match = re.search(r"语言:</span>([^<]+)", str(info))
            if lang_match:
                languages = lang_match.group(1).strip()
                
            release_date = ""
            date_elem = soup.select_one("span[property='v:initialReleaseDate']")
            if date_elem:
                release_date = date_elem.text.strip()
                
            runtime = ""
            runtime_elem = soup.select_one("span[property='v:runtime']")
            if runtime_elem:
                runtime = runtime_elem.text.strip()
                
            imdb_id = ""
            imdb_match = re.search(r"IMDb:</span>([^<]+)", str(info))
            if imdb_match:
                imdb_id = imdb_match.group(1).strip()
                
            detail = {
                **movie,
                "year": year,
                "directors": directors,
                "writers": writers,
                "casts": casts,
                "genres": genres,
                "countries": countries,
                "languages": languages,
                "release_date": release_date,
                "runtime": runtime,
                "imdb_id": imdb_id,
                "summary": summary,
                "poster": poster
            }
            
            self.progress["movies_completed"].append(movie_id)
            self.save_progress()
            
            return detail
            
        except Exception as e:
            print(f"解析详情页失败: {e}")
            return None
            
    async def crawl_comments(self, movie: dict) -> list:
        """爬取电影短评"""
        movie_id = movie["id"]
        
        if movie_id in self.progress.get("comments_completed", {}):
            count = self.progress["comments_completed"][movie_id]
            if count >= config.COMMENTS_PER_MOVIE:
                print(f"跳过已完成短评: {movie['title']}")
                return []
                
        print(f"正在爬取短评: {movie['title']}")
        
        comments = []
        start = 0
        
        while len(comments) < config.COMMENTS_PER_MOVIE:
            url = f"{config.BASE_URL}/subject/{movie_id}/comments?start={start}&limit=20&status=P"
            
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
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
                    user_url = user_elem["href"] if user_elem else ""
                    
                    rating_elem = item.select_one(".rating")
                    rating = ""
                    if rating_elem:
                        rating_class = rating_elem.get("class", [])
                        for cls in rating_class:
                            if "allstar" in cls:
                                rating = cls.replace("allstar", "").replace("0rating", "")
                                break
                                
                    votes_elem = item.select_one(".votes")
                    votes = votes_elem.text.strip() if votes_elem else "0"
                    
                    content_elem = item.select_one(".short")
                    comment_content = content_elem.text.strip() if content_elem else ""
                    
                    time_elem = item.select_one(".comment-time")
                    comment_time = time_elem.text.strip() if time_elem else ""
                    
                    comments.append({
                        "movie_id": movie_id,
                        "movie_title": movie["title"],
                        "comment_id": comment_id,
                        "user_name": user_name,
                        "user_url": user_url,
                        "rating": rating,
                        "votes": votes,
                        "content": comment_content,
                        "time": comment_time
                    })
                    
                except Exception as e:
                    continue
                    
            start += 20
            await asyncio.sleep(config.PAGE_DELAY)
            
        comments = comments[:config.COMMENTS_PER_MOVIE]
        
        self.progress["comments_completed"][movie_id] = len(comments)
        self.save_progress()
        
        print(f"获取 {len(comments)} 条短评")
        return comments
        
    async def crawl_reviews(self, movie: dict) -> list:
        """爬取电影影评"""
        movie_id = movie["id"]
        
        if movie_id in self.progress.get("reviews_completed", {}):
            count = self.progress["reviews_completed"][movie_id]
            if count >= config.REVIEWS_PER_MOVIE:
                print(f"跳过已完成影评: {movie['title']}")
                return []
                
        print(f"正在爬取影评: {movie['title']}")
        
        reviews = []
        start = 0
        
        while len(reviews) < config.REVIEWS_PER_MOVIE:
            url = f"{config.BASE_URL}/subject/{movie_id}/reviews?start={start}"
            
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            items = soup.select(".review-list > div")
            if not items:
                break
                
            for item in items:
                try:
                    review_elem = item.select_one("a[data-cid]")
                    if not review_elem:
                        continue
                        
                    review_id = review_elem.get("data-cid", "")
                    
                    title_elem = item.select_one("a[data-cid]")
                    title = title_elem.text.strip() if title_elem else ""
                    
                    user_elem = item.select_one(".name a")
                    user_name = user_elem.text.strip() if user_elem else ""
                    user_url = user_elem["href"] if user_elem else ""
                    
                    rating_elem = item.select_one(".main-title-rating")
                    rating = ""
                    if rating_elem:
                        rating_class = rating_elem.get("class", [])
                        for cls in rating_class:
                            if "allstar" in cls:
                                rating = cls.replace("allstar", "").replace("0", "")
                                break
                                
                    votes_elem = item.select_one(".action-btn.up span")
                    votes = votes_elem.text.strip() if votes_elem else "0"
                    
                    content_elem = item.select_one(".short-content")
                    review_content = content_elem.text.strip() if content_elem else ""
                    
                    time_elem = item.select_one(".main-meta")
                    review_time = time_elem.text.strip() if time_elem else ""
                    
                    reviews.append({
                        "movie_id": movie_id,
                        "movie_title": movie["title"],
                        "review_id": review_id,
                        "title": title,
                        "user_name": user_name,
                        "user_url": user_url,
                        "rating": rating,
                        "votes": votes,
                        "content": review_content,
                        "time": review_time
                    })
                    
                except Exception as e:
                    continue
                    
            start += 20
            await asyncio.sleep(config.PAGE_DELAY)
            
        reviews = reviews[:config.REVIEWS_PER_MOVIE]
        
        self.progress["reviews_completed"][movie_id] = len(reviews)
        self.save_progress()
        
        print(f"获取 {len(reviews)} 篇影评")
        return reviews
        
    async def crawl_images(self, movie: dict) -> list:
        """爬取电影图片"""
        movie_id = movie["id"]
        
        if movie_id in self.progress.get("images_completed", []):
            print(f"跳过已完成图片: {movie['title']}")
            return []
            
        print(f"正在爬取图片: {movie['title']}")
        
        url = f"{config.BASE_URL}/subject/{movie_id}/photos?type=S"
        
        await self.page.goto(url)
        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        content = await self.page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        images = []
        items = soup.select(".cover a")
        
        for idx, item in enumerate(items):
            try:
                img_elem = item.select_one("img")
                if not img_elem:
                    continue
                    
                thumb_url = img_elem.get("src", "")
                if not thumb_url:
                    continue
                    
                origin_url = thumb_url.replace("/m/", "/raw/")
                
                type_class = item.get("class", [])
                img_type = "other"
                for cls in type_class:
                    if "poster" in cls:
                        img_type = "poster"
                    elif "still" in cls:
                        img_type = "still"
                    elif "screenshot" in cls:
                        img_type = "screenshot"
                        
                images.append({
                    "movie_id": movie_id,
                    "movie_title": movie["title"],
                    "type": img_type,
                    "thumb_url": thumb_url,
                    "origin_url": origin_url,
                    "index": idx + 1
                })
                
            except Exception as e:
                continue
                
        self.progress["images_completed"].append(movie_id)
        self.save_progress()
        
        print(f"获取 {len(images)} 张图片")
        return images
        
    async def download_images(self, images: list):
        """异步下载图片"""
        if not images:
            return
            
        movie_id = images[0]["movie_id"]
        movie_dir = Path(config.IMAGES_DIR) / movie_id
        movie_dir.mkdir(parents=True, exist_ok=True)
        
        async with httpx.AsyncClient(timeout=30) as client:
            for img in images:
                try:
                    response = await client.get(img["origin_url"])
                    if response.status_code == 200:
                        filename = f"{img['type']}_{img['index']:03d}.jpg"
                        filepath = movie_dir / filename
                        filepath.write_bytes(response.content)
                except Exception as e:
                    print(f"下载图片失败: {e}")
                    continue
                    
    def save_to_json(self, data: list, filepath: str):
        """保存数据到 JSON"""
        Path(filepath).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
    def save_to_csv(self, data: list, filepath: str):
        """保存数据到 CSV"""
        if not data:
            return
            
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            
    async def run(self):
        """主运行流程"""
        print("\n" + "="*60)
        print("豆瓣电影 TOP250 爬虫")
        print("="*60)
        
        Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(config.IMAGES_DIR).mkdir(parents=True, exist_ok=True)
        
        self.load_progress()
        self.load_existing_data()
        
        await self.init_browser()
        
        try:
            await self.ensure_login()
            
            movie_list = await self.crawl_top250_list()
            
            print("\n" + "="*60)
            print("Step 2: 爬取电影详情")
            print("="*60)
            
            for i, movie in enumerate(movie_list):
                detail = await self.crawl_movie_detail(movie)
                if detail:
                    self.movies.append(detail)
                    self.save_to_json(self.movies, config.MOVIES_JSON)
                    self.save_to_csv(self.movies, config.MOVIES_CSV)
                    
                if (i + 1) % 10 == 0:
                    print(f"进度: {i + 1}/250")
                    await asyncio.sleep(config.BATCH_DELAY)
                    
            print("\n" + "="*60)
            print("Step 3: 爬取短评")
            print("="*60)
            
            for i, movie in enumerate(self.movies):
                comments = await self.crawl_comments(movie)
                self.comments.extend(comments)
                self.save_to_json(self.comments, config.COMMENTS_JSON)
                self.save_to_csv(self.comments, config.COMMENTS_CSV)
                
                if (i + 1) % 10 == 0:
                    print(f"进度: {i + 1}/250")
                    await asyncio.sleep(config.BATCH_DELAY)
                    
            print("\n" + "="*60)
            print("Step 4: 爬取影评")
            print("="*60)
            
            for i, movie in enumerate(self.movies):
                reviews = await self.crawl_reviews(movie)
                self.reviews.extend(reviews)
                self.save_to_json(self.reviews, config.REVIEWS_JSON)
                self.save_to_csv(self.reviews, config.REVIEWS_CSV)
                
                if (i + 1) % 10 == 0:
                    print(f"进度: {i + 1}/250")
                    await asyncio.sleep(config.BATCH_DELAY)
                    
            print("\n" + "="*60)
            print("Step 5: 下载图片")
            print("="*60)
            
            for i, movie in enumerate(self.movies):
                images = await self.crawl_images(movie)
                await self.download_images(images)
                
                if (i + 1) % 10 == 0:
                    print(f"进度: {i + 1}/250")
                    await asyncio.sleep(config.BATCH_DELAY)
                    
            print("\n" + "="*60)
            print("爬取完成！")
            print(f"电影: {len(self.movies)} 部")
            print(f"短评: {len(self.comments)} 条")
            print(f"影评: {len(self.reviews)} 篇")
            print("="*60)
            
        finally:
            await self.browser.close()


async def main():
    crawler = DoubanTop250Crawler()
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())
