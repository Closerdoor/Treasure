# 情感分析指南

## 来源
`nlp-sentiment-analysis-master` 项目的评论情感分析

## 功能
1. **情感分析**：判断评论是好评还是差评
2. **关键词提取**：提取评论中的关键词
3. **主题聚类**：将评论按主题分组

## 依赖

```bash
pip install jieba scikit-learn numpy
```

- **jieba**：中文分词
- **scikit-learn**：机器学习（TF-IDF、朴素贝叶斯、K-Means）
- **numpy**：数值计算

## 核心功能

### 1. 中文分词
```python
import jieba

def tokenize(text: str, stopwords: List[str] = None) -> List[str]:
    """中文分词"""
    words = jieba.cut(text, cut_all=False)
    
    if stopwords:
        words = [w for w in words if w not in stopwords and len(w) > 1]
    
    return list(words)
```

### 2. 情感分析
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

def analyze_sentiment(comments: List[str]) -> Dict:
    """评论情感分析"""
    # 分词
    tokenized = [' '.join(tokenize(c)) for c in comments]
    
    # TF-IDF 向量化
    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform(tokenized)
    
    # 使用情感词典方法
    positive_words = ['好', '棒', '精彩', '感人', '优秀', '经典', '推荐', '喜欢']
    negative_words = ['差', '烂', '无聊', '失望', '垃圾', '难看', '浪费']
    
    positive_count = 0
    for comment in comments:
        if any(word in comment for word in positive_words):
            positive_count += 1
    
    positive_ratio = positive_count / len(comments) if comments else 0
    
    return {
        "positive_ratio": round(positive_ratio, 3),
        "negative_ratio": round(1 - positive_ratio, 3)
    }
```

### 3. 关键词提取
```python
def extract_keywords(comments: List[str], top_n: int = 20) -> List[Tuple[str, float]]:
    """提取评论关键词"""
    # 分词
    tokenized = [' '.join(tokenize(c)) for c in comments]
    
    # TF-IDF
    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform(tokenized)
    
    # 获取关键词
    feature_names = vectorizer.get_feature_names_out()
    tfidf_sum = X.sum(axis=0).A1
    top_indices = tfidf_sum.argsort()[-top_n:][::-1]
    
    keywords = []
    for i in top_indices:
        keywords.append((feature_names[i], round(tfidf_sum[i] / len(comments), 3)))
    
    return keywords
```

### 4. 主题聚类
```python
from sklearn.cluster import KMeans

def cluster_comments(comments: List[str], n_clusters: int = 5) -> Dict[int, List[str]]:
    """评论主题聚类"""
    # 分词
    tokenized = [' '.join(tokenize(c)) for c in comments]
    
    # TF-IDF
    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform(tokenized)
    
    # K-Means 聚类
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(X)
    
    # 分组
    clusters = {}
    for i, label in enumerate(labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(comments[i])
    
    return clusters
```

## 集成方案

### 1. 新建分析模块
```
movie-ingest/analyzer.py
```

### 2. 分析器类
```python
class CommentAnalyzer:
    def __init__(self, stopwords_path: str = "stopwords.txt"):
        self.stopwords = self._load_stopwords(stopwords_path)
    
    def _load_stopwords(self, filepath: str) -> List[str]:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f]
    
    def analyze_movie_comments(self, reviews_json: str) -> Dict:
        """分析电影评论"""
        reviews = json.loads(reviews_json)
        comments = [r["content"] for r in reviews]
        
        # 情感分析
        sentiment = analyze_sentiment(comments)
        
        # 关键词提取
        keywords = extract_keywords(comments, top_n=20)
        
        return {
            "positive_ratio": sentiment["positive_ratio"],
            "negative_ratio": sentiment["negative_ratio"],
            "keywords": keywords
        }
```

### 3. 集成到爬取流程
```python
class MovieIngestPipeline:
    def __init__(self):
        self.analyzer = CommentAnalyzer()
    
    async def crawl_movie(self, douban_id: str):
        # ... 爬取数据
        
        # 分析评论
        if raw_data.get("reviews"):
            analysis = self.analyzer.analyze_movie_comments(
                json.dumps(raw_data["reviews"])
            )
            
            raw_data["sentiment_analysis"] = analysis
```

### 4. 存储到数据库
```python
# 添加字段
ALTER TABLE crawled_movies ADD COLUMN sentiment_json TEXT;

# 保存
sentiment_json = json.dumps(analysis)
```

## 使用示例

```python
from analyzer import CommentAnalyzer

analyzer = CommentAnalyzer()

# 分析评论
comments = [
    "这部电影太精彩了，情节感人，演员演技出色",
    "非常失望，剧情无聊，浪费时间",
    "经典之作，强烈推荐",
    "一般般，没什么亮点"
]

result = analyzer.analyze_movie_comments(json.dumps([
    {"content": c} for c in comments
]))

print(f"好评率: {result['positive_ratio']}")
print(f"关键词: {result['keywords']}")
```

## 输出示例

```python
{
    "positive_ratio": 0.75,
    "negative_ratio": 0.25,
    "keywords": [
        ("精彩", 0.85),
        ("感人", 0.72),
        ("演技", 0.68),
        ("剧情", 0.65),
        ("经典", 0.60)
    ]
}
```

## 注意事项

1. **停用词**：使用停用词表过滤无意义词汇
2. **分词模式**：使用精确模式（`cut_all=False`）
3. **TF-IDF 参数**：`max_features=1000` 限制特征数量
4. **情感词典**：可根据需要扩展
5. **性能**：大量评论时建议分批处理

## 扩展功能

### 1. 训练分类器
如果有标注数据，可以训练更准确的分类器：
```python
# 标注数据
comments = ["好评评论1", "差评评论1", ...]
labels = [1, 0, ...]  # 1=好评，0=差评

# 训练
clf = MultinomialNB(alpha=0.01)
clf.fit(X_train, y_train)
```

### 2. 情感强度
不仅判断正负，还判断强度：
```python
# 强好评、弱好评、中性、弱差评、强差评
```

### 3. 方面级分析
分析评论针对的具体方面：
```python
{
    "演技": {"positive": 0.9, "negative": 0.1},
    "剧情": {"positive": 0.7, "negative": 0.3},
    "特效": {"positive": 0.8, "negative": 0.2}
}
```

## 参考文件
- `code-snippets/sentiment-analysis-snippet.py`：完整实现
- `complete-files/sklearn-sentiment.py`：原始实现
- `complete-files/stopwords.txt`：停用词表
