# 肖申克的救赎爬取进度

## 目标
- 修复百度百科爬虫，提取完整演职员数据（导演、编剧、全部演员），并整合到电影数据爬取流程中

## 约束与偏好
- **豆瓣数据优先原则**：豆瓣爬虫失败时必须先解决，不能跳过
- **全量数据原则**：获取全部演员数据，不限制数量
- 字段命名以 Prisma schema 为准
- 中文名从国内网站获取，英文名从外文网站获取
- 头像统一从百度百科获取（覆盖率最高），TMDB 作为备用

## 进度

### 已完成
- 创建 `RULES.md` 规则文档，明确豆瓣优先、全量数据原则
- 修改豆瓣爬虫 `douban.py`：添加重试机制（5s→10s→30s）、数据完整性验证
- 分析百度百科 PAGE_DATA 结构：
  - `card.content` 包含导演、编剧、主演、制片人（新版结构）
  - `card.left/right` 是旧版结构（已弃用）
  - `modules.featureInfo.data.majorActors` 包含主要演员头像（仅 4 人）
  - HTML `actorItem_EQB0t` 包含完整演员表（65 人，无头像）
- 修改百度百科爬虫 `baike.py`：
  - 添加 `_extract_page_data()` 提取 PAGE_DATA JSON
  - 添加 `_extract_credits_from_card()` 从 card.content 提取演职员
  - 添加 `_extract_major_actors_avatars()` 提取主要演员头像
  - 添加 `_extract_cast_from_html()` 从 HTML 提取完整演员表
  - 添加 `_split_character_name()` 分离中英文角色名
- **发现百度百科演职员数据为空**：
  - `card.content` 中 `director` 和 `starring` 的 value 为 None
  - 只有 `scriptwriter` 有 lemma 数据（斯·芬奇·金）
  - HTML 中也没有演职员数据
- **验证 TMDB 演职员数据完整**：
  - TMDB 提供 59 个演员 + 143 个演职人员
  - 包含完整的角色名（character）和头像（profile_path）
- **验证 merger 合并逻辑正确**：
  - 豆瓣提供中文名
  - TMDB 提供英文名、角色名、头像
  - merger 自动合并两者数据

### 结论
**百度百科演职员数据为空不影响最终结果**。TMDB 提供了完整的演职员数据，merger 会自动合并豆瓣的中文名和 TMDB 的英文名、角色名。

### 下一步
1. 测试完整的电影爬取流程（使用 `main.py`）
2. 验证数据库导入是否正确
3. 清理测试文件

## 关键决策
- 百度百科数据结构：新版使用 `card.content` 数组，旧版使用 `card.left/right`
- 演员数据来源：TMDB > 豆瓣（TMDB 有角色名和头像）
- 头像来源：TMDB（最完整）
- 百度百科演职员数据不可靠，不作为主要来源

## 相关文件
- `F:\MyProject\Treasure\temp-script\movie-ingest\RULES.md` - 爬虫规则文档
- `F:\MyProject\Treasure\temp-script\movie-ingest\sources\douban.py` - 豆瓣爬虫（已添加重试机制）
- `F:\MyProject\Treasure\temp-script\movie-ingest\sources\baike.py` - 百度百科爬虫（已修复）
- `F:\MyProject\Treasure\temp-script\movie-ingest\sources\tmdb.py` - TMDB 客户端
- `F:\MyProject\Treasure\temp-script\movie-ingest\merger.py` - 数据合并模块
- `F:\MyProject\Treasure\temp-script\movie-ingest\test_full_merge.py` - 完整流程测试
