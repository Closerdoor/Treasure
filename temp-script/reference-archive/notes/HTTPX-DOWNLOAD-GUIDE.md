# httpx 下载指南

## 来源
`douban-top250` 项目的 httpx 图片下载实现

## httpx vs aiohttp

### httpx 优势
1. **更现代的 API**：设计更简洁
2. **支持 HTTP/2**：性能更好
3. **响应内容直接可用**：`response.content`
4. **更好的错误处理**：异常体系清晰
5. **同步/异步统一 API**：易于切换

### aiohttp 劣势
1. **需要手动管理 connector**
2. **响应内容需要 await**：`await response.read()`
3. **API 较复杂**
4. **不支持 HTTP/2**

## 代码对比

### aiohttp（当前 movie-ingest）
```python
import aiohttp

async with aiohttp.ClientSession() as session:
    async with session.get(url, proxy=proxy) as response:
        if response.status == 200:
            content = await response.read()
```

### httpx（推荐）
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(url, proxy=proxy)
    if response.status_code == 200:
        content = response.content
```

## 集成方案

### 1. 替换 downloader.py
```python
# 当前
import aiohttp

# 替换为
import httpx
```

### 2. 修改下载方法
```python
async def _download_image(self, url: str, output_path: Path) -> bool:
    """下载单张图片"""
    try:
        async with httpx.AsyncClient(
            timeout=self.timeout,
            proxy=self.proxy if self.proxy else None
        ) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                return False
            
            # 写入文件
            output_path.write_bytes(response.content)
            return True
            
    except httpx.TimeoutException:
        print(f"超时: {url}")
        return False
    except httpx.HTTPStatusError as e:
        print(f"HTTP 错误: {e}")
        return False
    except Exception as e:
        print(f"下载失败: {e}")
        return False
```

### 3. 批量下载
```python
async def download_batch(self, images: List[Dict], output_dir: Path):
    """批量下载图片"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    semaphore = asyncio.Semaphore(self.max_concurrency)
    
    async def download_one(img: Dict):
        async with semaphore:
            url = img["url"]
            filename = f"{img['type']}_{img['index']:03d}.jpg"
            output_path = output_dir / filename
            
            return await self._download_image(url, output_path)
    
    tasks = [download_one(img) for img in images]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if r is True)
    print(f"下载完成: {success_count}/{len(images)}")
```

## 高级功能

### 1. 重试机制
```python
async def download_with_retry(url: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.content
        except:
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
            raise
```

### 2. 进度显示
```python
from tqdm import tqdm

async def download_with_progress(images: List[Dict]):
    async with httpx.AsyncClient(timeout=30) as client:
        for img in tqdm(images, desc="下载图片"):
            response = await client.get(img["url"])
            if response.status_code == 200:
                Path(img["path"]).write_bytes(response.content)
```

### 3. 代理支持
```python
# HTTP 代理
proxy = "http://127.0.0.1:7890"

# SOCKS 代理（需要 httpx[socks]）
proxy = "socks5://127.0.0.1:1080"

async with httpx.AsyncClient(proxy=proxy) as client:
    response = await client.get(url)
```

## 安装

```bash
pip install httpx

# SOCKS 代理支持
pip install httpx[socks]

# HTTP/2 支持
pip install httpx[http2]
```

## 迁移步骤

1. **安装 httpx**
```bash
pip install httpx
```

2. **修改 imports**
```python
# 删除
import aiohttp

# 添加
import httpx
```

3. **修改下载方法**
- `aiohttp.ClientSession()` → `httpx.AsyncClient()`
- `response.status` → `response.status_code`
- `await response.read()` → `response.content`

4. **测试**
```bash
python main.py --test-download
```

## 注意事项

1. **超时设置**：httpx 默认 5 秒，建议增加到 30 秒
2. **代理格式**：`http://` 而非 `http://`
3. **异常处理**：使用 httpx 的异常类型
4. **连接池**：httpx 自动管理，无需手动创建 connector

## 参考文件
- `code-snippets/httpx-download.py`：完整实现
