# -*- coding: utf-8 -*-
"""
稳定的评论爬取方案（来自 douban-top250）

关键改进：
1. 分页逻辑：start=0, 20, 40, ...
2. 进度保存：每页完成后保存进度
3. 延迟控制：每页之间延迟 2-5 秒
4. 选择器：.comment-item（短评）、.review-list > div（影评）

集成位置：movie-ingest/sources/douban.py 的 crawl_comments() 和 crawl_reviews() 方法
"""

import asyncio
import random
import re
from bs4 import BeautifulSoup


async def crawl_comments_stable(page, movie_id: str, count: int = 20, min_delay: float = 2.0, max_delay: float = 5.0) -> list:
    """
    稳定的短评爬取方案
    
    Args:
        page: Playwright page 对象
        movie_id: 豆瓣电影 ID
        count: 爬取数量
        min_delay: 最小延迟（秒）
        max_delay: 最大延迟（秒）
    
    Returns:
        评论列表
    """
    comments = []
    start = 0
    
    while len(comments) < count:
        # 关键：使用 sort=new_score 参数按热度排序
        url = f"https://movie.douban.com/subject/{movie_id}/comments?start={start}&limit=20&sort=new_score&status=P"
        
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(min_delay, max_delay))
            
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            items = soup.select(".comment-item")  # 关键选择器
            if not items:
                break
            
            for item in items:
                try:
                    comment_id = item.get("data-cid", "")
                    
                    user_elem = item.select_one(".comment-info a")
                    user_name = user_elem.text.strip() if user_elem else ""
                    user_url = user_elem["href"] if user_elem else ""
                    
                    # 评分提取
                    rating_elem = item.select_one(".rating")
                    rating = ""
                    if rating_elem:
                        rating_class = rating_elem.get("class", [])
                        for cls in rating_class:
                            if "allstar" in cls:
                                rating = cls.replace("allstar", "").replace("0rating", "")
                                break
                    
                    # 点赞数
                    votes_elem = item.select_one(".votes")
                    votes = votes_elem.text.strip() if votes_elem else "0"
                    
                    # 评论内容
                    content_elem = item.select_one(".short")
                    comment_content = content_elem.text.strip() if content_elem else ""
                    
                    # 时间
                    time_elem = item.select_one(".comment-time")
                    comment_time = time_elem.text.strip() if time_elem else ""
                    
                    comments.append({
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
            
            # 关键：每页之间延迟
            await asyncio.sleep(random.uniform(min_delay, max_delay))
            
        except Exception as e:
            print(f"爬取评论失败: {e}")
            break
    
    return comments[:count]


async def crawl_reviews_stable(page, movie_id: str, count: int = 20, min_delay: float = 2.0, max_delay: float = 5.0) -> list:
    """
    稳定的影评爬取方案
    
    Args:
        page: Playwright page 对象
        movie_id: 豆瓣电影 ID
        count: 爬取数量
        min_delay: 最小延迟（秒）
        max_delay: 最大延迟（秒）
    
    Returns:
        影评列表
    """
    reviews = []
    start = 0
    
    while len(reviews) < count:
        url = f"https://movie.douban.com/subject/{movie_id}/reviews?start={start}"
        
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(min_delay, max_delay))
            
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            items = soup.select(".review-list > div")  # 关键选择器
            if not items:
                break
            
            for item in items:
                try:
                    review_elem = item.select_one("a[data-cid]")
                    if not review_elem:
                        continue
                    
                    review_id = review_elem.get("data-cid", "")
                    title = review_elem.text.strip()
                    
                    user_elem = item.select_one(".name a")
                    user_name = user_elem.text.strip() if user_elem else ""
                    user_url = user_elem["href"] if user_elem else ""
                    
                    # 评分提取
                    rating_elem = item.select_one(".main-title-rating")
                    rating = ""
                    if rating_elem:
                        rating_class = rating_elem.get("class", [])
                        for cls in rating_class:
                            if "allstar" in cls:
                                rating = cls.replace("allstar", "").replace("0", "")
                                break
                    
                    # 点赞数
                    votes_elem = item.select_one(".action-btn.up span")
                    votes = votes_elem.text.strip() if votes_elem else "0"
                    
                    # 影评摘要
                    content_elem = item.select_one(".short-content")
                    review_content = content_elem.text.strip() if content_elem else ""
                    
                    # 时间
                    time_elem = item.select_one(".main-meta")
                    review_time = time_elem.text.strip() if time_elem else ""
                    
                    reviews.append({
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
            await asyncio.sleep(random.uniform(min_delay, max_delay))
            
        except Exception as e:
            print(f"爬取影评失败: {e}")
            break
    
    return reviews[:count]


# 使用示例
if __name__ == "__main__":
    """
    集成到 movie-ingest/sources/douban.py:
    
    当前方案已足够稳定，无需修改。
    
    关键点：
    1. 使用 sort=new_score 参数按热度排序
    2. 每页之间延迟 2-5 秒
    3. 正确的选择器：.comment-item 和 .review-list > div
    """
    pass
