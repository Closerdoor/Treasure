# 主题聚类指南

## 来源
`nlp-sentiment-analysis-master` 项目的 `sklearn-topic-cluster.py`

## 功能
将电影评论按主题自动分组，发现评论中的常见话题。

### 1. KMeans 聚类
- **用途**：将评论分成 K 个主题组
- **优点**：简单、快速、易于理解
- **缺点**：需要预先指定 K 值

### 2. DBSCAN 聚类
- **用途**：基于密度的聚类，自动发现簇数量
- **优点**：不需要指定簇数量，能发现噪声点
- **缺点**：参数敏感（eps、min_samples）

### 3. PCA 降维可视化
- **用途**：将高维数据降维到 2D/3D，可视化聚类结果
- **优点**：直观展示聚类效果
- **缺点**：降维会损失信息

### 4. 肘部法则
- **用途**：找到最优的聚类数量 K
- **优点**：自动推荐 K 值
- **缺点**：肘部点可能不明显

---

## 使用场景

### 场景 1：评论主题分析
发现评论中的常见话题：
- 剧情评价（精彩、无聊、感人）
- 演员评价（演技出色、角色刻画）
- 视觉效果（特效震撼、画面精美）
- 导演评价（功力深厚、叙事流畅）

### 场景 2：评论分类
将评论按主题分类，方便用户查看：
- 正面评论（剧情、演员、视觉效果）
- 负面评论（剧情无聊、节奏拖沓）

### 场景 3：评论推荐
根据用户偏好推荐相关评论：
- 用户喜欢剧情 → 推荐剧情相关评论
- 用户关注演员 → 推荐演员相关评论

---

## 集成方案

### 1. 新建分析模块
```
movie-ingest/analyzer.py
```

### 2. 分析器类
```python
class CommentAnalyzer:
    def __init__(self):
        self.stopwords = load_stopwords("stopwords.txt")
    
    def cluster_comments(self, movie_id: str, n_clusters: int = 10):
        """评论主题聚类"""
        # 从数据库读取评论
        comments = self.load_comments(movie_id)
        
        # TF-IDF 向量化
        vectorizer = TfidfVectorizer(tokenizer=self.tokenize)
        X = vectorizer.fit_transform(comments)
        
        # KMeans 聚类
        clf = KMeans(n_clusters=n_clusters)
        clf.fit(X)
        
        return {
            "labels": clf.labels_,
            "inertia": clf.inertia_
        }
    
    def visualize_clusters(self, movie_id: str):
        """可视化聚类结果"""
        comments = self.load_comments(movie_id)
        result = self.cluster_comments(movie_id)
        
        # PCA 降维
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X.toarray())
        
        # 绘图
        plt.scatter(X_pca[:, 0], X_pca[:, 1], c=result["labels"])
        plt.show()
```

### 3. 集成到爬取流程
```python
class MovieIngestPipeline:
    def __init__(self):
        self.analyzer = CommentAnalyzer()
    
    async def process_movie(self, douban_id: str):
        # ... 爬取数据
        
        # 评论聚类
        if raw_data.get("reviews"):
            cluster_result = self.analyzer.cluster_comments(movie_id)
            
            # 保存聚类结果
            self.db.update_movie_clusters(movie_id, cluster_result)
```

---

## 参数调优

### KMeans 参数
- `n_clusters`：簇数量（推荐 10-20）
- `random_state`：随机种子（固定结果）

### DBSCAN 参数
- `eps`：邻域半径（推荐 0.3-0.7）
- `min_samples`：最小样本数（推荐 3-10）

### TF-IDF 参数
- `max_features`：最大特征数（推荐 500-2000）
- `tokenizer`：分词器（推荐 jieba）

---

## 注意事项

### 1. 数据预处理
- 使用停用词表过滤无意义词汇
- 使用 jieba 分词
- 建议过滤短评论（< 10 字）

### 2. 聚类数量
- 评论少（< 50）：使用 3-5 个簇
- 评论中等（50-200）：使用 5-10 个簇
- 评论多（> 200）：使用 10-20 个簇

### 3. 可视化
- 2D 可视化适合展示
- 3D 可视化适合深入分析
- 建议保存图片到文件

### 4. 性能
- 评论数量大时，TF-IDF 计算耗时
- 建议限制 `max_features`
- 可使用 PCA 降维加速

---

## 输出示例

### 聚类结果
```python
{
    "labels": [0, 1, 2, 0, 1, 2, 0, 1],
    "inertia": 123.45,
    "n_clusters": 3
}
```

### 簇主题（示例）
- 簇 0：剧情评价（精彩、感人、无聊）
- 簇 1：演员评价（演技出色、角色刻画）
- 簇 2：视觉效果（特效震撼、画面精美）

---

## 参考文件
- `code-snippets/topic-cluster.py`：完整实现
- `complete-files/sklearn-sentiment.py`：原始实现