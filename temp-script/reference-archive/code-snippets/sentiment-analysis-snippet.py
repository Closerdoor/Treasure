# -*- coding: utf-8 -*-
"""
情感分析代码片段（来自 nlp-sentiment-analysis-master）

功能：
1. 评论情感分析（好评/差评）
2. 关键词提取
3. 主题聚类

依赖：
- jieba: 中文分词
- sklearn: 机器学习

集成位置：movie-ingest/analyzer.py（新建）
"""

import jieba
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn import metrics
from typing import List, Dict, Tuple


def load_stopwords(filepath: str = "stopwords.txt") -> List[str]:
    """
    加载停用词表
    
    Args:
        filepath: 停用词文件路径
    
    Returns:
        停用词列表
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        stopwords = [line.strip() for line in f]
    return stopwords


def tokenize(text: str, stopwords: List[str] = None) -> List[str]:
    """
    中文分词
    
    Args:
        text: 文本
        stopwords: 停用词列表
    
    Returns:
        分词列表
    """
    words = jieba.cut(text, cut_all=False)
    
    if stopwords:
        words = [w for w in words if w not in stopwords and len(w) > 1]
    
    return list(words)


def analyze_sentiment(comments: List[str], labels: List[int] = None) -> Dict:
    """
    评论情感分析
    
    Args:
        comments: 评论列表
        labels: 标签列表（1=好评，0=差评），如果为 None 则使用预训练模型
    
    Returns:
        {
            "positive_ratio": 0.85,
            "negative_ratio": 0.15,
            "keywords": ["精彩", "感人", ...]
        }
    """
    # 分词
    tokenized = [' '.join(tokenize(c)) for c in comments]
    
    # TF-IDF 向量化
    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform(tokenized)
    
    # 如果有标签，训练模型
    if labels:
        # 分割训练集和测试集
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.3)
        
        # 训练朴素贝叶斯分类器
        clf = MultinomialNB(alpha=0.01)
        clf.fit(X_train, y_train)
        
        # 预测
        y_pred = clf.predict(X_test)
        
        # 评估
        precision = metrics.precision_score(y_test, y_pred)
        recall = metrics.recall_score(y_test, y_pred)
        
        print(f"准确率: {precision:.3f}")
        print(f"召回率: {recall:.3f}")
        
        # 预测所有评论
        all_pred = clf.predict(X)
        positive_ratio = np.mean(all_pred)
        
    else:
        # 使用简单的情感词典方法
        positive_words = ['好', '棒', '精彩', '感人', '优秀', '经典', '推荐', '喜欢']
        negative_words = ['差', '烂', '无聊', '失望', '垃圾', '难看', '浪费']
        
        positive_count = 0
        for comment in comments:
            if any(word in comment for word in positive_words):
                positive_count += 1
        
        positive_ratio = positive_count / len(comments) if comments else 0
    
    # 提取关键词
    feature_names = vectorizer.get_feature_names_out()
    tfidf_sum = X.sum(axis=0).A1
    top_indices = tfidf_sum.argsort()[-20:][::-1]
    keywords = [feature_names[i] for i in top_indices]
    
    return {
        "positive_ratio": round(positive_ratio, 3),
        "negative_ratio": round(1 - positive_ratio, 3),
        "keywords": keywords
    }


def extract_keywords(comments: List[str], top_n: int = 20) -> List[Tuple[str, float]]:
    """
    提取评论关键词
    
    Args:
        comments: 评论列表
        top_n: 返回关键词数量
    
    Returns:
        [("精彩", 0.85), ("感人", 0.72), ...]
    """
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


def cluster_comments(comments: List[str], n_clusters: int = 5) -> Dict[int, List[str]]:
    """
    评论主题聚类
    
    Args:
        comments: 评论列表
        n_clusters: 聚类数量
    
    Returns:
        {0: ["评论1", "评论2"], 1: [...], ...}
    """
    from sklearn.cluster import KMeans
    
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


# 使用示例
if __name__ == "__main__":
    """
    集成到 movie-ingest/analyzer.py:
    
    class CommentAnalyzer:
        def __init__(self):
            self.stopwords = load_stopwords("stopwords.txt")
        
        def analyze_movie_comments(self, reviews_json: str) -> Dict:
            import json
            
            reviews = json.loads(reviews_json)
            comments = [r["content"] for r in reviews]
            
            # 情感分析
            sentiment = analyze_sentiment(comments)
            
            # 关键词提取
            keywords = extract_keywords(comments, top_n=20)
            
            return {
                "positive_ratio": sentiment["positive_ratio"],
                "keywords": keywords
            }
    
    # 使用：
    # analyzer = CommentAnalyzer()
    # result = analyzer.analyze_movie_comments(movie["reviews_json"])
    # print(f"好评率: {result['positive_ratio']}")
    # print(f"关键词: {result['keywords']}")
    """
    
    # 测试
    comments = [
        "这部电影太精彩了，情节感人，演员演技出色",
        "非常失望，剧情无聊，浪费时间",
        "经典之作，强烈推荐",
        "一般般，没什么亮点"
    ]
    
    result = analyze_sentiment(comments)
    print(f"好评率: {result['positive_ratio']}")
    print(f"关键词: {result['keywords']}")
