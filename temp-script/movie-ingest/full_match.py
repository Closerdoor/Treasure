# -*- coding: utf-8 -*-
"""
全量人物匹配脚本

功能：
1. 通过作品关联匹配（TMDB credits）
2. TMDB 搜索 API 匹配
3. 百度百科辅助匹配（中国人物）
4. 标记无法匹配的人物

策略：
- 第一层：作品关联匹配（通过作品的 TMDB credits 直接匹配）
- 第二层：TMDB 搜索 API（对未匹配的人物搜索）
- 第三层：百度百科辅助（对中国人物）
"""
import os
import sys

if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

import asyncio
import aiohttp
import json
import sqlite3
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from difflib import SequenceMatcher

import config
from utils import Logger


class FullMatcher:
    """全量人物匹配器"""
    
    def __init__(self):
        self.db_path = config.DB_PATH
        self.avatar_dir = config.PEOPLE_ASSETS_DIR
        self.conn = None
        
        self.tmdb_api_key = config.TMDB_API_KEY
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.proxy = config.PROXY_URL if config.PROXY_ENABLED else None
        
        # 缓存
        self.movie_tmdb_map = {}  # work_id -> tmdb_id
        self.tmdb_credits_cache = {}  # tmdb_id -> credits_data
        self.person_match_cache = {}  # person_db_id -> tmdb_id
        
        # 统计
        self.stats = {
            'total_missing': 0,
            'layer1_matched': 0,  # 作品关联匹配
            'layer2_matched': 0,  # TMDB 搜索匹配
            'layer3_matched': 0,  # 百度百科匹配
            'no_match': 0,        # 无法匹配
            'api_calls': 0,
            'errors': 0,
        }
        
        # API 速率控制
        self.api_semaphore = asyncio.Semaphore(5)  # 最大并发 5
        self.last_api_call = 0
        self.api_min_interval = 0.25  # 最小间隔 250ms
        
    def connect(self):
        if not self.conn:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            Logger.info(f"数据库已连接: {self.db_path}")
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
    
    # ========================================
    # 数据库查询
    # ========================================
    
    def get_movies_with_tmdb(self) -> Dict[str, str]:
        """获取所有电影的 TMDB ID 映射"""
        self.connect()
        
        cursor = self.conn.execute("""
            SELECT id, title, external_source 
            FROM works 
            WHERE submodule = 'movie'
        """)
        
        movies = {}
        for row in cursor.fetchall():
            movie = dict(row)
            if movie['external_source']:
                sources = json.loads(movie['external_source'])
                tmdb_source = next((s for s in sources if s['name'] == 'TMDB'), None)
                if tmdb_source:
                    movies[movie['id']] = tmdb_source['id']
        
        Logger.info(f"有 TMDB ID 的电影: {len(movies)} 部")
        self.movie_tmdb_map = movies
        return movies
    
    def get_missing_persons(self) -> List[Dict]:
        """获取所有缺少 source_ids 的人物（正确 JOIN）"""
        self.connect()
        
        cursor = self.conn.execute("""
            SELECT DISTINCT p.id, p.person_id, p.name, p.name_en, p.source_ids
            FROM person p
            JOIN work_person wp ON p.id = wp.person_id
            WHERE p.source_ids IS NULL
            ORDER BY p.id
        """)
        
        persons = [dict(row) for row in cursor.fetchall()]
        Logger.info(f"缺少 source_ids 的人物: {len(persons)} 人")
        self.stats['total_missing'] = len(persons)
        return persons
    
    def get_person_works(self, person_db_id: int) -> List[Dict]:
        """获取人物参与的作品"""
        self.connect()
        
        cursor = self.conn.execute("""
            SELECT w.id, w.title, wp.role, w.external_source
            FROM work_person wp
            JOIN works w ON wp.work_id = w.id
            WHERE wp.person_id = ?
            ORDER BY w.id
        """, (person_db_id,))
        
        works = []
        for row in cursor.fetchall():
            work = dict(row)
            if work['external_source']:
                sources = json.loads(work['external_source'])
                tmdb_source = next((s for s in sources if s['name'] == 'TMDB'), None)
                if tmdb_source:
                    work['tmdb_id'] = tmdb_source['id']
            works.append(work)
        
        return works
    
    def update_person_source(self, person_db_id: int, tmdb_id: str, tmdb_name: str = None):
        """更新人物的 source_ids"""
        self.connect()
        
        source_ids = {'tmdb': tmdb_id}
        tmdb_avatar_path = f"tmdb-{tmdb_id}-avatar.jpg"
        
        self.conn.execute("""
            UPDATE person 
            SET source_ids = ?,
                tmdb_avatar_path = ?,
                avatar_path = COALESCE(avatar_path, ?)
            WHERE id = ?
        """, (json.dumps(source_ids), tmdb_avatar_path, tmdb_avatar_path, person_db_id))
        
        self.conn.commit()
    
    def mark_person_no_match(self, person_db_id: int):
        """标记人物为无 TMDB 记录"""
        self.connect()
        
        source_ids = {'tmdb': 'NO_MATCH'}
        
        self.conn.execute("""
            UPDATE person 
            SET source_ids = ?
            WHERE id = ?
        """, (json.dumps(source_ids), person_db_id))
        
        self.conn.commit()
    
    # ========================================
    # API 调用（带速率控制）
    # ========================================
    
    async def api_call(self, url: str, params: Dict) -> Optional[Dict]:
        """带速率控制的 API 调用"""
        async with self.api_semaphore:
            # 确保最小间隔
            now = time.time()
            elapsed = now - self.last_api_call
            if elapsed < self.api_min_interval:
                await asyncio.sleep(self.api_min_interval - elapsed)
            
            self.last_api_call = time.time()
            self.stats['api_calls'] += 1
            
            try:
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(
                        url, 
                        params=params, 
                        proxy=self.proxy,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            Logger.warning("API 速率限制，等待 10 秒")
                            await asyncio.sleep(10)
                            return await self.api_call(url, params)
                        else:
                            Logger.warning(f"API 返回 {response.status}: {url}")
                            return None
            except asyncio.TimeoutError:
                Logger.warning(f"API 超时: {url}")
                self.stats['errors'] += 1
                return None
            except Exception as e:
                Logger.warning(f"API 错误: {e}")
                self.stats['errors'] += 1
                return None
    
    async def fetch_tmdb_credits(self, tmdb_movie_id: str) -> Optional[Dict]:
        """获取电影演职员数据"""
        if tmdb_movie_id in self.tmdb_credits_cache:
            return self.tmdb_credits_cache[tmdb_movie_id]
        
        url = f"{self.tmdb_base_url}/movie/{tmdb_movie_id}/credits"
        params = {'api_key': self.tmdb_api_key}
        
        data = await self.api_call(url, params)
        
        if data:
            self.tmdb_credits_cache[tmdb_movie_id] = data
        
        return data
    
    async def search_tmdb_person(self, name: str) -> Optional[List[Dict]]:
        """搜索 TMDB 人物"""
        url = f"{self.tmdb_base_url}/search/person"
        params = {
            'api_key': self.tmdb_api_key,
            'query': name,
            'page': 1,
        }
        
        data = await self.api_call(url, params)
        
        if data and 'results' in data:
            return data['results']
        
        return None
    
    async def fetch_tmdb_person_detail(self, tmdb_id: str) -> Optional[Dict]:
        """获取人物详情"""
        url = f"{self.tmdb_base_url}/person/{tmdb_id}"
        params = {'api_key': self.tmdb_api_key}
        
        return await self.api_call(url, params)
    
    # ========================================
    # 名字匹配工具
    # ========================================
    
    def normalize_name(self, name: str) -> str:
        """标准化名字"""
        if not name:
            return ""
        # 小写，去除多余空格
        name = name.lower().strip()
        # 去除中间名缩写点
        name = re.sub(r'\.', '', name)
        return name
    
    def name_similarity(self, name1: str, name2: str) -> float:
        """计算名字相似度"""
        n1 = self.normalize_name(name1)
        n2 = self.normalize_name(name2)
        
        if n1 == n2:
            return 1.0
        
        # 使用 SequenceMatcher
        return SequenceMatcher(None, n1, n2).ratio()
    
    def match_name_in_credits(self, name_en: str, credits: Dict) -> Optional[Dict]:
        """在 credits 中匹配人物"""
        best_match = None
        best_score = 0.8  # 最低匹配阈值
        
        # 检查 cast
        for person in credits.get('cast', []):
            tmdb_name = person.get('name', '')
            score = self.name_similarity(name_en, tmdb_name)
            
            if score >= best_score:
                if score > best_score or best_match is None:
                    best_score = score
                    best_match = person
        
        # 检查 crew
        for person in credits.get('crew', []):
            tmdb_name = person.get('name', '')
            score = self.name_similarity(name_en, tmdb_name)
            
            if score >= best_score:
                if score > best_score or best_match is None:
                    best_score = score
                    best_match = person
        
        return best_match
    
    def is_chinese_name(self, name: str) -> bool:
        """判断是否为中文名"""
        return bool(re.search(r'[\u4e00-\u9fa5]', name))
    
    # ========================================
    # 第一层：作品关联匹配
    # ========================================
    
    async def layer1_match(self, person: Dict) -> Optional[str]:
        """通过作品关联匹配"""
        person_db_id = person['id']
        name_en = person['name_en']
        
        if not name_en:
            return None
        
        # 获取人物参与的作品
        works = self.get_person_works(person_db_id)
        
        for work in works:
            if 'tmdb_id' not in work:
                continue
            
            tmdb_id = work['tmdb_id']
            credits = await self.fetch_tmdb_credits(tmdb_id)
            
            if not credits:
                continue
            
            # 在 credits 中匹配
            match = self.match_name_in_credits(name_en, credits)
            
            if match:
                tmdb_person_id = str(match['id'])
                return tmdb_person_id
        
        return None
    
    # ========================================
    # 第二层：TMDB 搜索匹配
    # ========================================
    
    async def layer2_match(self, person: Dict) -> Optional[str]:
        """通过 TMDB 搜索 API 匹配"""
        name_en = person['name_en']
        
        if not name_en:
            return None
        
        # 搜索人物
        results = await self.search_tmdb_person(name_en)
        
        if not results:
            return None
        
        # 获取人物的作品用于验证
        works = self.get_person_works(person['id'])
        work_titles = [w['title'] for w in works]
        
        # 检查搜索结果
        for result in results[:5]:  # 只检查前 5 个结果
            tmdb_id = str(result['id'])
            tmdb_name = result.get('name', '')
            
            # 名字相似度检查
            if self.name_similarity(name_en, tmdb_name) >= 0.85:
                # 获取人物详情验证作品
                detail = await self.fetch_tmdb_person_detail(tmdb_id)
                
                if detail:
                    # 检查 known_for
                    known_for = detail.get('known_for', [])
                    for movie in known_for:
                        movie_title = movie.get('title', '')
                        # 检查是否有共同作品
                        for work_title in work_titles:
                            if self.name_similarity(movie_title, work_title) >= 0.7:
                                return tmdb_id
                
                # 如果没有 known_for，直接返回第一个高相似度匹配
                if self.name_similarity(name_en, tmdb_name) >= 0.95:
                    return tmdb_id
        
        return None
    
    # ========================================
    # 第三层：百度百科匹配（中国人物）
    # ========================================
    
    async def layer3_match(self, person: Dict) -> Optional[str]:
        """通过百度百科辅助匹配"""
        name = person['name']
        
        if not self.is_chinese_name(name):
            return None
        
        # 百度百科搜索
        # TODO: 实现百度百科 API 调用
        # 目前先跳过，后续可以添加
        
        return None
    
    # ========================================
    # 主流程
    # ========================================
    
    async def match_person(self, person: Dict) -> Tuple[Optional[str], str]:
        """匹配单个人物"""
        person_db_id = person['id']
        name = person['name']
        name_en = person['name_en']
        
        Logger.info(f"[{person_db_id}] {name} ({name_en})")
        
        # 第一层：作品关联匹配
        tmdb_id = await self.layer1_match(person)
        if tmdb_id:
            self.stats['layer1_matched'] += 1
            Logger.success(f"  作品关联匹配: tmdb:{tmdb_id}")
            return tmdb_id, 'layer1'
        
        # 第二层：TMDB 搜索匹配
        tmdb_id = await self.layer2_match(person)
        if tmdb_id:
            self.stats['layer2_matched'] += 1
            Logger.success(f"  TMDB 搜索匹配: tmdb:{tmdb_id}")
            return tmdb_id, 'layer2'
        
        # 第三层：百度百科匹配（仅中国人物）
        if self.is_chinese_name(name):
            tmdb_id = await self.layer3_match(person)
            if tmdb_id:
                self.stats['layer3_matched'] += 1
                Logger.success(f"  百度百科匹配: tmdb:{tmdb_id}")
                return tmdb_id, 'layer3'
        
        # 无法匹配
        self.stats['no_match'] += 1
        Logger.warning(f"  无法匹配")
        return None, 'no_match'
    
    async def run(self):
        """执行全量匹配"""
        Logger.info("=== 开始全量人物匹配 ===")
        
        # 获取电影 TMDB 映射
        self.get_movies_with_tmdb()
        
        # 获取缺失人物
        persons = self.get_missing_persons()
        
        # 预加载所有电影的 credits（提高效率）
        Logger.info("预加载电影 credits...")
        for work_id, tmdb_id in self.movie_tmdb_map.items():
            await self.fetch_tmdb_credits(tmdb_id)
            await asyncio.sleep(0.1)
        
        Logger.info(f"Credits 缓存: {len(self.tmdb_credits_cache)} 部电影")
        
        # 匹配每个人物
        for i, person in enumerate(persons):
            Logger.info(f"[{i+1}/{len(persons)}]")
            
            tmdb_id, method = await self.match_person(person)
            
            if tmdb_id:
                self.update_person_source(person['id'], tmdb_id)
            else:
                self.mark_person_no_match(person['id'])
            
            # 进度报告
            if (i + 1) % 100 == 0:
                Logger.info(f"进度: {i+1}/{len(persons)}")
                Logger.info(f"  已匹配: {self.stats['layer1_matched'] + self.stats['layer2_matched'] + self.stats['layer3_matched']}")
                Logger.info(f"  未匹配: {self.stats['no_match']}")
        
        # 输出统计
        Logger.info("=== 匹配完成 ===")
        Logger.info(f"总缺失人物: {self.stats['total_missing']}")
        Logger.info(f"作品关联匹配: {self.stats['layer1_matched']}")
        Logger.info(f"TMDB 搜索匹配: {self.stats['layer2_matched']}")
        Logger.info(f"百度百科匹配: {self.stats['layer3_matched']}")
        Logger.info(f"无法匹配: {self.stats['no_match']}")
        Logger.info(f"API 调用: {self.stats['api_calls']}")
        Logger.info(f"错误: {self.stats['errors']}")
        
        self.close()


async def main():
    matcher = FullMatcher()
    await matcher.run()


if __name__ == '__main__':
    asyncio.run(main())