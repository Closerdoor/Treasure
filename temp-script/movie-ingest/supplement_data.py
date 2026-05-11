# -*- coding: utf-8 -*-
"""
补充缺失数据

功能：
1. 补充有 source_ids 但缺少头像文件的人物（109 个）
2. 尝试为没有 source_ids 的人物匹配 TMDB ID（4,724 个）
3. 利用孤儿头像文件匹配数据库人物（534 个）
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
from pathlib import Path
from typing import Dict, List, Optional, Set

import config
from utils import Logger


class DataSupplementer:
    """数据补充器"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent / ".local" / "treasure.db"
        self.avatar_dir = Path(__file__).parent.parent.parent / ".local" / "assets" / "people"
        self.conn = None
        
        self.tmdb_api_key = config.TMDB_API_KEY
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.proxy = config.PROXY_URL if config.PROXY_ENABLED else None
        
        # 统计
        self.stats = {
            'missing_avatar_found': 0,
            'missing_avatar_downloaded': 0,
            'no_source_matched': 0,
            'orphan_matched': 0,
        }
    
    def connect(self):
        if not self.conn:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_existing_avatars(self) -> Set[str]:
        """获取已存在的头像文件"""
        avatars = set()
        if self.avatar_dir.exists():
            for f in self.avatar_dir.iterdir():
                avatars.add(f.name)
        return avatars
    
    # ========================================
    # 任务 1：补充缺失的头像
    # ========================================
    
    def get_persons_missing_avatar(self) -> List[Dict]:
        """获取有 source_ids 但缺少头像文件的人物"""
        self.connect()
        
        cursor = self.conn.execute("""
            SELECT id, person_id, name, name_en, source_ids, tmdb_avatar_path
            FROM person
            WHERE source_ids IS NOT NULL AND tmdb_avatar_path IS NOT NULL
        """)
        
        existing_avatars = self.get_existing_avatars()
        missing = []
        
        for row in cursor.fetchall():
            person = dict(row)
            if person['tmdb_avatar_path']:
                filename = person['tmdb_avatar_path'].split('/')[-1]
                if filename not in existing_avatars:
                    missing.append(person)
        
        return missing
    
    async def download_avatar(self, tmdb_id: str, person_name: str) -> bool:
        """下载单个头像"""
        url = f"https://image.tmdb.org/t/p/original"
        
        # 先获取人物详情获取 profile_path
        person_url = f"{self.tmdb_base_url}/person/{tmdb_id}"
        params = {'api_key': self.tmdb_api_key}
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(person_url, params=params, proxy=self.proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        return False
                    
                    data = await response.json()
                    profile_path = data.get('profile_path')
                    
                    if not profile_path:
                        return False
                    
                    # 下载头像
                    avatar_url = f"https://image.tmdb.org/t/p/original{profile_path}"
                    filename = f"tmdb-{tmdb_id}-avatar.jpg"
                    filepath = self.avatar_dir / filename
                    
                    headers = {
                        'Referer': 'https://www.themoviedb.org/',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    async with session.get(avatar_url, headers=headers, proxy=self.proxy, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            with open(filepath, 'wb') as f:
                                f.write(content)
                            return True
            
        except Exception as e:
            Logger.warning(f"下载头像失败 ({person_name}): {e}")
            return False
        
        return False
    
    async def supplement_missing_avatars(self):
        """补充缺失的头像"""
        Logger.info("=== 任务 1：补充缺失的头像 ===")
        
        persons = self.get_persons_missing_avatar()
        Logger.info(f"需要补充头像: {len(persons)} 人")
        
        if not persons:
            return
        
        for i, person in enumerate(persons):
            source_ids = json.loads(person['source_ids'])
            tmdb_id = source_ids.get('tmdb')
            
            if not tmdb_id:
                continue
            
            Logger.info(f"[{i+1}/{len(persons)}] {person['name']} (tmdb: {tmdb_id})")
            
            success = await self.download_avatar(tmdb_id, person['name'])
            
            if success:
                self.stats['missing_avatar_downloaded'] += 1
                Logger.success(f"  头像下载成功")
            else:
                Logger.warning(f"  头像下载失败")
            
            await asyncio.sleep(0.3)
    
    # ========================================
    # 任务 2：为没有 source_ids 的人物匹配 TMDB
    # ========================================
    
    def get_persons_no_source_ids(self) -> List[Dict]:
        """获取没有 source_ids 的人物"""
        self.connect()
        
        cursor = self.conn.execute("""
            SELECT id, person_id, name, name_en
            FROM person
            WHERE source_ids IS NULL
            ORDER BY id
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_movies_for_person(self, person_db_id: int) -> List[Dict]:
        """获取人物参与的电影"""
        cursor = self.conn.execute("""
            SELECT w.id, w.title, w.external_source
            FROM work_person wp
            JOIN works w ON wp.work_id = w.id
            WHERE wp.person_id = ?
            LIMIT 5
        """, (person_db_id,))
        
        movies = []
        for row in cursor.fetchall():
            movie = dict(row)
            if movie['external_source']:
                sources = json.loads(movie['external_source'])
                tmdb = next((s for s in sources if s['name'] == 'TMDB'), None)
                if tmdb:
                    movie['tmdb_id'] = tmdb['id']
                    movies.append(movie)
        
        return movies
    
    async def search_tmdb_person(self, name_en: str) -> Optional[Dict]:
        """搜索 TMDB 人物"""
        url = f"{self.tmdb_base_url}/search/person"
        params = {'api_key': self.tmdb_api_key, 'query': name_en}
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params, proxy=self.proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        if results:
                            return results[0]
        except Exception as e:
            pass
        
        return None
    
    async def match_person_via_movie(self, person: Dict, movie: Dict) -> Optional[str]:
        """通过电影匹配人物"""
        tmdb_movie_id = movie.get('tmdb_id')
        if not tmdb_movie_id:
            return None
        
        # 获取电影演职员
        url = f"{self.tmdb_base_url}/movie/{tmdb_movie_id}/credits"
        params = {'api_key': self.tmdb_api_key}
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params, proxy=self.proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    name_en = person.get('name_en', '').lower().strip()
                    
                    # 在 cast 和 crew 中查找
                    for c in data.get('cast', []):
                        if c.get('name', '').lower().strip() == name_en:
                            return str(c.get('id'))
                    
                    for c in data.get('crew', []):
                        if c.get('name', '').lower().strip() == name_en:
                            return str(c.get('id'))
                    
                    # 尝试反转名字
                    parts = name_en.split()
                    if len(parts) == 2:
                        reversed_name = f"{parts[1]} {parts[0]}"
                        for c in data.get('cast', []) + data.get('crew', []):
                            if c.get('name', '').lower().strip() == reversed_name:
                                return str(c.get('id'))
        
        except Exception as e:
            pass
        
        return None
    
    def update_person_source_ids(self, person_db_id: int, tmdb_id: str):
        """更新人物的 source_ids"""
        source_ids = {'tmdb': tmdb_id}
        avatar_path = f"people/tmdb-{tmdb_id}-avatar.jpg"
        
        self.conn.execute("""
            UPDATE person
            SET source_ids = ?,
                tmdb_avatar_path = ?,
                avatar_path = COALESCE(avatar_path, ?)
            WHERE id = ?
        """, (json.dumps(source_ids), avatar_path, avatar_path, person_db_id))
        
        self.conn.commit()
    
    async def supplement_source_ids(self):
        """为没有 source_ids 的人物匹配 TMDB"""
        Logger.info("\n=== 任务 2：匹配没有 source_ids 的人物 ===")
        
        persons = self.get_persons_no_source_ids()
        Logger.info(f"需要匹配: {len(persons)} 人")
        
        if not persons:
            return
        
        matched = 0
        
        for i, person in enumerate(persons):
            name_en = person.get('name_en', '')
            
            if not name_en or len(name_en) < 3:
                continue
            
            # 获取人物参与的电影
            movies = self.get_movies_for_person(person['id'])
            
            if not movies:
                continue
            
            # 尝试通过电影匹配
            tmdb_id = None
            for movie in movies:
                tmdb_id = await self.match_person_via_movie(person, movie)
                if tmdb_id:
                    break
            
            if tmdb_id:
                self.update_person_source_ids(person['id'], tmdb_id)
                matched += 1
                self.stats['no_source_matched'] += 1
                Logger.success(f"[{i+1}/{len(persons)}] {person['name']} -> tmdb: {tmdb_id}")
            
            if matched > 0 and matched % 50 == 0:
                Logger.info(f"已匹配: {matched}")
            
            await asyncio.sleep(0.2)
        
        Logger.info(f"匹配完成: {matched}")
    
    # ========================================
    # 任务 3：利用孤儿头像匹配数据库人物
    # ========================================
    
    def get_orphan_avatars(self) -> List[str]:
        """获取孤儿头像的 TMDB ID"""
        existing_avatars = self.get_existing_avatars()
        
        # 获取数据库中的 TMDB ID
        self.connect()
        cursor = self.conn.execute("SELECT source_ids FROM person WHERE source_ids IS NOT NULL")
        
        db_tmdb_ids = set()
        for row in cursor.fetchall():
            try:
                sources = json.loads(row['source_ids'])
                if sources.get('tmdb'):
                    db_tmdb_ids.add(sources['tmdb'])
            except:
                pass
        
        # 找出孤儿
        orphan_ids = []
        for f in existing_avatars:
            if f.startswith('tmdb-'):
                match = re.match(r'^tmdb-(\d+)-avatar\.jpg$', f)
                if match:
                    tmdb_id = match.group(1)
                    if tmdb_id not in db_tmdb_ids:
                        orphan_ids.append(tmdb_id)
        
        return orphan_ids
    
    async def match_orphan_avatars(self):
        """利用孤儿头像匹配数据库人物"""
        Logger.info("\n=== 任务 3：利用孤儿头像匹配人物 ===")
        
        orphan_ids = self.get_orphan_avatars()
        Logger.info(f"孤儿头像: {len(orphan_ids)} 个")
        
        if not orphan_ids:
            return
        
        matched = 0
        
        for i, tmdb_id in enumerate(orphan_ids):
            # 获取 TMDB 人物信息
            url = f"{self.tmdb_base_url}/person/{tmdb_id}"
            params = {'api_key': self.tmdb_api_key}
            
            try:
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(url, params=params, proxy=self.proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status != 200:
                            continue
                        
                        data = await response.json()
                        name = data.get('name', '')
                        
                        if not name:
                            continue
                        
                        # 在数据库中查找
                        normalized = name.lower().strip()
                        cursor = self.conn.execute(
                            "SELECT id, name, source_ids FROM person WHERE LOWER(name_en) = ? AND source_ids IS NULL",
                            (normalized,)
                        )
                        row = cursor.fetchone()
                        
                        if row:
                            person = dict(row)
                            self.update_person_source_ids(person['id'], tmdb_id)
                            matched += 1
                            self.stats['orphan_matched'] += 1
                            Logger.success(f"[{i+1}/{len(orphan_ids)}] {name} -> {person['name']}")
                        
                        # 尝试反转名字
                        parts = normalized.split()
                        if len(parts) == 2:
                            reversed_name = f"{parts[1]} {parts[0]}"
                            cursor = self.conn.execute(
                                "SELECT id, name, source_ids FROM person WHERE LOWER(name_en) = ? AND source_ids IS NULL",
                                (reversed_name,)
                            )
                            row = cursor.fetchone()
                            
                            if row:
                                person = dict(row)
                                self.update_person_source_ids(person['id'], tmdb_id)
                                matched += 1
                                self.stats['orphan_matched'] += 1
                                Logger.success(f"[{i+1}/{len(orphan_ids)}] {name} -> {person['name']} (反转)")
            
            except Exception as e:
                pass
            
            await asyncio.sleep(0.3)
        
        Logger.info(f"孤儿匹配完成: {matched}")
    
    # ========================================
    # 主流程
    # ========================================
    
    async def run(self):
        Logger.info("=== 开始补充数据 ===")
        
        # 任务 1：补充缺失的头像
        await self.supplement_missing_avatars()
        
        # 任务 2：匹配没有 source_ids 的人物
        await self.supplement_source_ids()
        
        # 任务 3：利用孤儿头像匹配
        await self.match_orphan_avatars()
        
        # 统计
        Logger.info("\n=== 补充完成 ===")
        Logger.info(f"缺失头像下载: {self.stats['missing_avatar_downloaded']}")
        Logger.info(f"无 source_ids 匹配: {self.stats['no_source_matched']}")
        Logger.info(f"孤儿头像匹配: {self.stats['orphan_matched']}")
        
        self.close()


async def main():
    supplementer = DataSupplementer()
    await supplementer.run()


if __name__ == '__main__':
    asyncio.run(main())