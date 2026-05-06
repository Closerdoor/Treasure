# -*- coding: utf-8 -*-
"""
1905 电影网爬虫代码片段（来自 python-crawler-main）

1905 电影网特点：
1. 国内权威电影资料库
2. 访问速度快（国内服务器）
3. 数据质量高
4. 无需登录

集成位置：movie-ingest/sources/1905.py（新建）
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional


class M1905Crawler:
    """1905 电影网爬虫"""
    
    def __init__(self):
        self.base_url = "https://www.1905.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def search(self, title: str) -> Optional[str]:
        """
        搜索电影
        
        Args:
            title: 电影标题
        
        Returns:
            电影详情页 URL 或 None
        """
        # 1905 搜索 URL
        search_url = f"{self.base_url}/search/?q={title}"
        
        try:
            response = requests.get(search_url, headers=self.headers)
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 查找搜索结果
            results = soup.select('.search-result a')
            
            for result in results:
                href = result.get('href', '')
                if '/vod/' in href:
                    return href
            
            return None
            
        except Exception as e:
            print(f"1905 搜索失败: {e}")
            return None
    
    def get_detail(self, url: str) -> Dict:
        """
        获取电影详情
        
        Args:
            url: 电影详情页 URL
        
        Returns:
            电影数据
        """
        try:
            response = requests.get(url, headers=self.headers)
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 提取基本信息
            data = {
                "source": "1905",
                "url": url
            }
            
            # 标题
            title_elem = soup.select_one('h1')
            if title_elem:
                data["title"] = title_elem.text.strip()
            
            # 评分
            rating_elem = soup.select_one('.score')
            if rating_elem:
                data["rating"] = rating_elem.text.strip()
            
            # 导演
            director_elem = soup.select_one('.director a')
            if director_elem:
                data["director"] = director_elem.text.strip()
            
            # 演员
            actors = [a.text.strip() for a in soup.select('.actor a')]
            if actors:
                data["actors"] = actors
            
            # 类型
            genres = [a.text.strip() for a in soup.select('.type a')]
            if genres:
                data["genres"] = genres
            
            # 简介
            summary_elem = soup.select_one('.summary')
            if summary_elem:
                data["summary"] = summary_elem.text.strip()
            
            # 海报
            poster_elem = soup.select_one('.poster img')
            if poster_elem:
                data["poster"] = poster_elem.get('src', '')
            
            return data
            
        except Exception as e:
            print(f"1905 获取详情失败: {e}")
            return {}
    
    def get_top_movies(self, page: int = 1) -> List[Dict]:
        """
        获取热门电影列表
        
        Args:
            page: 页码（1-99）
        
        Returns:
            电影列表
        """
        url = f"{self.base_url}/vod/list/n_1/o3p{page}.html"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            movies = []
            items = soup.select('.grid-2x')
            
            for item in items:
                try:
                    # 标题
                    name_elem = item.select_one('a[title]')
                    title = name_elem['title'] if name_elem else ""
                    
                    # 链接
                    link_elem = item.select_one('a.pic-pack-outer')
                    url = link_elem['href'] if link_elem else ""
                    
                    # 评分
                    score_elem = item.select_one('i')
                    score = score_elem.text if score_elem else ""
                    
                    if title and url:
                        movies.append({
                            "title": title,
                            "url": url,
                            "score": score
                        })
                        
                except:
                    continue
            
            return movies
            
        except Exception as e:
            print(f"1905 获取列表失败: {e}")
            return []


# 使用示例
if __name__ == "__main__":
    """
    集成到 movie-ingest/sources/1905.py:
    
    from sources.1905 import M1905Crawler
    
    class MovieIngestPipeline:
        def __init__(self):
            self.m1905 = M1905Crawler()
        
        async def crawl_movie(self, douban_id: str, title: str):
            # ... 其他数据源
            
            # 1905 电影网
            try:
                m1905_url = self.m1905.search(title)
                if m1905_url:
                    m1905_data = self.m1905.get_detail(m1905_url)
                    raw_data["1905"] = m1905_data
            except Exception as e:
                Logger.error(f"1905 爬取失败: {e}")
    
    数据字段映射：
    - title → title（中文标题）
    - rating → ratings_json["1905"]
    - director → credits["directors"]
    - actors → credits["actors"]
    - genres → genres_json
    - summary → synopsis_text（补充）
    - poster → images_json（补充）
    """
    
    # 测试
    crawler = M1905Crawler()
    
    # 搜索电影
    url = crawler.search("星际穿越")
    print(f"搜索结果: {url}")
    
    if url:
        # 获取详情
        data = crawler.get_detail(url)
        print(f"详情: {data}")
