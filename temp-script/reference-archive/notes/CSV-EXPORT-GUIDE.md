# CSV 导出指南

## 来源
`douban-top250` 项目的 CSV 导出功能

## 功能
将 SQLite 数据库数据导出为 CSV 格式，方便：
- Excel 查看
- 数据分析
- 备份存档

## 核心要点

### 1. 编码
```python
# 使用 utf-8-sig 编码（Excel 兼容）
with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
```

**为什么用 utf-8-sig？**
- Excel 打开 utf-8 文件会乱码
- utf-8-sig 添加 BOM（Byte Order Mark）
- Excel 正确识别编码

### 2. 字段映射
```python
# 自动字段名
if not fieldnames:
    fieldnames = list(data[0].keys())

# 手动指定字段名
fieldnames = ["id", "title", "year", "rating"]
```

### 3. JSON 字段展开
```python
import json

# 从 ratings_json 提取各平台评分
ratings = json.loads(ratings_json)

row = {
    "id": movie_id,
    "title": title,
    "douban_rating": ratings.get("douban", {}).get("value", ""),
    "imdb_rating": ratings.get("imdb", {}).get("value", ""),
    "tmdb_rating": ratings.get("tmdb", {}).get("value", ""),
    "aggregate": ratings.get("aggregate", {}).get("value", "")
}
```

## 集成方案

### 1. 添加到 database.py
```python
class DatabaseManager:
    def export_to_csv(self, output_dir: str = "output"):
        """导出所有数据到 CSV"""
        self.connect()
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 导出电影数据
        self._export_movies_csv(output_dir)
        
        # 导出评分数据
        self._export_ratings_csv(output_dir)
        
        # 导出演职员数据
        self._export_credits_csv(output_dir)
```

### 2. 导出电影数据
```python
def _export_movies_csv(self, output_dir: str):
    cursor = self.conn.execute(
        """
        SELECT 
            id, douban_id, title, original_title, year, 
            country, language, runtime_minutes, 
            synopsis_text, story_text,
            crawl_status, created_at, updated_at
        FROM crawled_movies 
        WHERE crawl_status = 'completed'
        ORDER BY id
        """
    )
    
    columns = [desc[0] for desc in cursor.description]
    movies = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    self._write_csv(movies, f"{output_dir}/movies.csv", columns)
```

### 3. 导出评分数据
```python
def _export_ratings_csv(self, output_dir: str):
    cursor = self.conn.execute(
        """
        SELECT id, title, ratings_json 
        FROM crawled_movies 
        WHERE crawl_status = 'completed' AND ratings_json IS NOT NULL
        """
    )
    
    ratings_data = []
    for row in cursor.fetchall():
        movie_id, title, ratings_json = row
        ratings = json.loads(ratings_json)
        
        ratings_data.append({
            "id": movie_id,
            "title": title,
            "douban": ratings.get("douban", {}).get("value", ""),
            "imdb": ratings.get("imdb", {}).get("value", ""),
            "tmdb": ratings.get("tmdb", {}).get("value", ""),
            "rotten_tomatoes": ratings.get("rottenTomatoes", {}).get("value", ""),
            "metascore": ratings.get("metascore", {}).get("value", ""),
            "aggregate": ratings.get("aggregate", {}).get("value", "")
        })
    
    self._write_csv(ratings_data, f"{output_dir}/ratings.csv")
```

### 4. 通用 CSV 写入
```python
def _write_csv(self, data: List[Dict], filepath: str, fieldnames: List[str] = None):
    if not data:
        return
    
    if not fieldnames:
        fieldnames = list(data[0].keys())
    
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"已导出 {len(data)} 条记录到 {filepath}")
```

## 使用方式

### 命令行
```bash
python main.py --export-csv --output-dir output
```

### Python API
```python
from database import DatabaseManager

db = DatabaseManager()
db.export_to_csv("output")
```

## 输出文件

```
output/
├── movies.csv        # 电影基本信息
├── ratings.csv       # 评分数据（展开）
├── credits.csv       # 演职员数据（展开）
└── genres.csv        # 类型数据（展开）
```

## 注意事项

1. **只导出已完成的电影**：`WHERE crawl_status = 'completed'`
2. **JSON 字段展开**：方便 Excel 查看
3. **空值处理**：使用空字符串而非 NULL
4. **文件覆盖**：每次导出覆盖旧文件

## 参考文件
- `code-snippets/csv-export.py`：完整实现
