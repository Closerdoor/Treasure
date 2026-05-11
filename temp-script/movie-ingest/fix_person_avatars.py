# -*- coding: utf-8 -*-
"""
修复人物头像数据

流程：
1. 从数据库读取所有电影及其 TMDB ID
2. 调用 TMDB API 获取演职员数据
3. 通过英文名匹配数据库中的人物
4. 更新人物的 source_ids 和头像路径
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
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import config
from utils import Logger


class AvatarFixer:
    """人物头像修复器"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent / ".local" / "treasure.db"
        self.avatar_dir = Path(__file__).parent.parent.parent / ".local" / "assets" / "people"
        self.conn = None
        
        # TMDB API 配置
        self.tmdb_api_key = config.TMDB_API_KEY
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        
        # 缓存
        self.tmdb_persons = {}  # tmdb_id -> person_data
        self.name_to_persons = {}  # name_en -> list of person_db_ids
        
        # 统计
        self.stats = {
            'movies_processed': 0,
            'tmdb_persons_found': 0,
            'persons_matched': 0,
            'persons_updated': 0,
            'avatars_matched': 0,
        }
    
    def connect(self):
        """连接数据库"""
        if not self.conn:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            Logger.info(f"数据库已连接: {self.db_path}")
    
    def close(self):
        """关闭数据库"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_movies_with_tmdb_id(self) -> List[Dict]:
        """获取所有有 TMDB ID 的电影"""
        self.connect()
        
        cursor = self.conn.execute("""
            SELECT id, title, external_source 
            FROM works 
            WHERE submodule = 'movie'
            ORDER BY id
        """)
        
        movies = []
        for row in cursor.fetchall():
            movie = dict(row)
            if movie['external_source']:
                sources = json.loads(movie['external_source'])
                tmdb_source = next((s for s in sources if s['name'] == 'TMDB'), None)
                if tmdb_source:
                    movie['tmdb_id'] = tmdb_source['id']
                    movies.append(movie)
        
        return movies
    
    def load_existing_avatars(self) -> Dict[str, str]:
        """加载已下载的头像文件"""
        avatars = {}
        
        if not self.avatar_dir.exists():
            return avatars
        
        for f in self.avatar_dir.iterdir():
            if f.name.startswith('tmdb-') and f.name.endswith('.jpg'):
                # tmdb-12345-avatar.jpg -> 12345
                match = re.match(r'tmdb-(\d+)-avatar\.jpg', f.name)
                if match:
                    tmdb_id = match.group(1)
                    avatars[tmdb_id] = f.name
        
        Logger.info(f"已加载 {len(avatars)} 个 TMDB 头像文件")
        return avatars
    
    def build_name_index(self):
        """构建英文名索引"""
        self.connect()
        
        cursor = self.conn.execute("""
            SELECT id, person_id, name, name_en, avatar_path, source_ids
            FROM person
        """)
        
        for row in cursor.fetchall():
            person = dict(row)
            name_en = person['name_en']
            
            if name_en:
                # 标准化英文名（小写，去除空格）
                normalized = name_en.lower().strip()
                
                if normalized not in self.name_to_persons:
                    self.name_to_persons[normalized] = []
                
                self.name_to_persons[normalized].append(person)
        
        Logger.info(f"已构建英文名索引: {len(self.name_to_persons)} 个唯一名字")
    
    def normalize_name(self, name: str) -> str:
        """标准化名字"""
        if not name:
            return ""
        return name.lower().strip()
    
    async def fetch_tmdb_credits(self, tmdb_movie_id: str) -> Optional[Dict]:
        """获取 TMDB 电影演职员数据"""
        url = f"{self.tmdb_base_url}/movie/{tmdb_movie_id}/credits"
        params = {'api_key': self.tmdb_api_key}
        
        try:
            # 使用代理
            proxy = config.PROXY_URL if config.PROXY_ENABLED else None
            
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params, proxy=proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        Logger.warning(f"TMDB API 返回 {response.status}: {tmdb_movie_id}")
                        return None
        except asyncio.TimeoutError:
            Logger.warning(f"TMDB API 超时 ({tmdb_movie_id})")
            return None
        except Exception as e:
            Logger.warning(f"获取 TMDB credits 失败 ({tmdb_movie_id}): {e}")
            return None
    
    def match_person(self, tmdb_person: Dict) -> Optional[Dict]:
        """通过英文名匹配数据库中的人物"""
        tmdb_name = tmdb_person.get('name', '')
        if not tmdb_name:
            return None
        
        normalized = self.normalize_name(tmdb_name)
        
        # 查找匹配的人物
        matches = self.name_to_persons.get(normalized, [])
        
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # 多个匹配，返回第一个（后续可以优化）
            Logger.warning(f"英文名重复: {tmdb_name} ({len(matches)} 个匹配)")
            return matches[0]
        
        return None
    
    def update_person(self, person_db_id: int, tmdb_id: str, tmdb_avatar_path: str):
        """更新人物数据"""
        self.connect()
        
        # 获取当前 source_ids
        cursor = self.conn.execute(
            "SELECT source_ids FROM person WHERE id = ?",
            (person_db_id,)
        )
        row = cursor.fetchone()
        
        current_source_ids = {}
        if row and row['source_ids']:
            try:
                current_source_ids = json.loads(row['source_ids'])
            except:
                pass
        
        # 更新 source_ids
        current_source_ids['tmdb'] = tmdb_id
        
        # 更新数据库
        self.conn.execute("""
            UPDATE person 
            SET source_ids = ?,
                tmdb_avatar_path = ?,
                avatar_path = COALESCE(avatar_path, ?)
            WHERE id = ?
        """, (
            json.dumps(current_source_ids),
            tmdb_avatar_path,
            tmdb_avatar_path,
            person_db_id
        ))
        
        self.conn.commit()
        self.stats['persons_updated'] += 1
    
    async def process_movie(self, movie: Dict, avatars: Dict[str, str]):
        """处理一部电影"""
        tmdb_id = movie['tmdb_id']
        work_id = movie['id']
        title = movie['title']
        
        Logger.info(f"处理: {title} ({work_id}) - TMDB ID: {tmdb_id}")
        
        # 获取 TMDB credits
        credits = await self.fetch_tmdb_credits(tmdb_id)
        
        if not credits:
            Logger.warning(f"无法获取 credits: {title}")
            return
        
        cast = credits.get('cast', [])
        crew = credits.get('crew', [])
        
        Logger.info(f"  演员: {len(cast)}, 演职人员: {len(crew)}")
        
        # 处理演员
        for actor in cast:
            tmdb_person_id = str(actor.get('id', ''))
            tmdb_name = actor.get('name', '')
            
            if not tmdb_person_id:
                continue
            
            self.stats['tmdb_persons_found'] += 1
            
            # 匹配数据库人物
            matched_person = self.match_person(actor)
            
            if matched_person:
                self.stats['persons_matched'] += 1
                
                # 检查是否有头像文件
                if tmdb_person_id in avatars:
                    avatar_file = avatars[tmdb_person_id]
                    avatar_path = f"people/{avatar_file}"
                    
                    self.stats['avatars_matched'] += 1
                    
                    # 更新数据库
                    self.update_person(
                        matched_person['id'],
                        tmdb_person_id,
                        avatar_path
                    )
                    
                    Logger.success(f"  匹配: {tmdb_name} -> {matched_person['name']} (头像: {avatar_file})")
        
        # 处理导演
        directors = [c for c in crew if c.get('job') == 'Director']
        for director in directors:
            tmdb_person_id = str(director.get('id', ''))
            tmdb_name = director.get('name', '')
            
            if not tmdb_person_id:
                continue
            
            self.stats['tmdb_persons_found'] += 1
            
            matched_person = self.match_person(director)
            
            if matched_person:
                self.stats['persons_matched'] += 1
                
                if tmdb_person_id in avatars:
                    avatar_file = avatars[tmdb_person_id]
                    avatar_path = f"people/{avatar_file}"
                    
                    self.stats['avatars_matched'] += 1
                    
                    self.update_person(
                        matched_person['id'],
                        tmdb_person_id,
                        avatar_path
                    )
                    
                    Logger.success(f"  匹配: {tmdb_name} -> {matched_person['name']} (导演)")
        
        self.stats['movies_processed'] += 1
    
    async def run(self):
        """执行修复"""
        Logger.info("=== 开始修复人物头像数据 ===")
        
        # 加载已下载的头像
        avatars = self.load_existing_avatars()
        
        # 构建英文名索引
        self.build_name_index()
        
        # 获取所有电影
        movies = self.get_movies_with_tmdb_id()
        Logger.info(f"待处理电影: {len(movies)} 部")
        
        # 处理每部电影
        for i, movie in enumerate(movies):
            Logger.info(f"[{i+1}/{len(movies)}]")
            await self.process_movie(movie, avatars)
            
            # 延迟，避免 API 限制
            await asyncio.sleep(0.5)
        
        # 输出统计
        Logger.info("=== 修复完成 ===")
        Logger.info(f"处理电影: {self.stats['movies_processed']} 部")
        Logger.info(f"TMDB 人物: {self.stats['tmdb_persons_found']} 人")
        Logger.info(f"匹配人物: {self.stats['persons_matched']} 人")
        Logger.info(f"更新人物: {self.stats['persons_updated']} 人")
        Logger.info(f"头像匹配: {self.stats['avatars_matched']} 个")
        
        self.close()


async def main():
    fixer = AvatarFixer()
    await fixer.run()


if __name__ == '__main__':
    asyncio.run(main())