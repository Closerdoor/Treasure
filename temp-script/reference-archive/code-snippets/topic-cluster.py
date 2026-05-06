# -*- coding: utf-8 -*-
"""
主题聚类代码片段（来自 nlp-sentiment-analysis-master）

功能：
1. KMeans 聚类：将评论按主题分组
2. DBSCAN 聚类：基于密度的聚类
3. SpectralCoclustering：谱聚类
4. PCA 降维：可视化聚类结果

依赖：
- pandas: 数据读取
- sklearn: 机器学习（TF-IDF、聚类、降维）
- matplotlib: 可视化

集成位置：movie-ingest/analyzer.py（新建）
"""

import pandas as pd
import re
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans, DBSCAN, SpectralCoclustering
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from typing import Dict, List


def cluster_comments_kmeans(comments: List[str], n_clusters: int = 20) -> Dict:
    """
    使用 KMeans 对评论进行主题聚类
    
    Args:
        comments: 评论列表
        n_clusters: 聚类数量
    
    Returns:
        {
            "labels": [0, 1, 2, ...],  # 每个评论的簇标签
            "cluster_centers": [...],  # 簇中心点
            "inertia": 123.45,         # 簇内距离总和（评估指标）
            "n_clusters": 20           # 簇数量
        }
    """
    # TF-IDF 向量化
    vectorizer = TfidfVectorizer(
        tokenizer=lambda x: re.split(r'\s+|[,;.-]\s*', x),
        max_features=1000
    )
    X = vectorizer.fit_transform(comments)
    
    # KMeans 聚类
    clf = KMeans(n_clusters=n_clusters, random_state=42)
    clf.fit(X)
    
    return {
        "labels": clf.labels_.tolist(),
        "cluster_centers": clf.cluster_centers_.tolist(),
        "inertia": float(clf.inertia_),
        "n_clusters": n_clusters
    }


def cluster_comments_dbscan(comments: List[str], eps: float = 0.5, min_samples: int = 5) -> Dict:
    """
    使用 DBSCAN 对评论进行密度聚类
    
    Args:
        comments: 评论列表
        eps: 邻域半径
        min_samples: 最小样本数
    
    Returns:
        {
            "labels": [0, 1, -1, ...],  # -1 表示噪声点
            "n_clusters": 5,            # 有效簇数量
            "n_noise": 10               # 噪声点数量
        }
    """
    # TF-IDF 向量化
    vectorizer = TfidfVectorizer(
        tokenizer=lambda x: re.split(r'\s+|[,;.-]\s*', x),
        max_features=1000
    )
    X = vectorizer.fit_transform(comments)
    
    # DBSCAN 聚类
    clf = DBSCAN(eps=eps, min_samples=min_samples)
    clf.fit(X)
    
    # 统计簇数量和噪声点
    labels = clf.labels_.tolist()
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = labels.count(-1)
    
    return {
        "labels": labels,
        "n_clusters": n_clusters,
        "n_noise": n_noise
    }


def visualize_clusters_pca(comments: List[str], labels: List[int], n_components: int = 2):
    """
    使用 PCA 降维可视化聚类结果
    
    Args:
        comments: 评论列表
        labels: 簇标签
        n_components: 降维维度（2 或 3）
    
    Returns:
        matplotlib 图像
    """
    # TF-IDF 向量化
    vectorizer = TfidfVectorizer(
        tokenizer=lambda x: re.split(r'\s+|[,;.-]\s*', x),
        max_features=1000
    )
    X = vectorizer.fit_transform(comments)
    
    # PCA 降维
    pca = PCA(n_components=n_components)
    X_pca = pca.fit_transform(X.toarray())
    
    # 可视化
    if n_components == 2:
        plt.figure(figsize=(10, 8))
        scatter = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=labels, cmap='viridis')
        plt.colorbar(scatter)
        plt.title('Comment Clusters (PCA 2D)')
        plt.xlabel('PC1')
        plt.ylabel('PC2')
        plt.show()
    
    elif n_components == 3:
        from mpl_toolkits.mplot3d import Axes3D
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(X_pca[:, 0], X_pca[:, 1], X_pca[:, 2], c=labels, cmap='viridis')
        plt.colorbar(scatter)
        ax.set_title('Comment Clusters (PCA 3D)')
        ax.set_xlabel('PC1')
        ax.set_ylabel('PC2')
        ax.set_zlabel('PC3')
        plt.show()


def find_optimal_clusters(comments: List[str], max_k: int = 30) -> Dict:
    """
    使用肘部法则找到最优聚类数量
    
    Args:
        comments: 评论列表
        max_k: 最大测试的簇数量
    
    Returns:
        {
            "k_values": [2, 3, ..., max_k],
            "inertias": [...],  # 每个 k 的 inertia 值
            "optimal_k": 10     # 推荐的簇数量
        }
    """
    # TF-IDF 向量化
    vectorizer = TfidfVectorizer(
        tokenizer=lambda x: re.split(r'\s+|[,;.-]\s*', x),
        max_features=1000
    )
    X = vectorizer.fit_transform(comments)
    
    # 测试不同的 k 值
    k_values = list(range(2, max_k + 1))
    inertias = []
    
    for k in k_values:
        clf = KMeans(n_clusters=k, random_state=42)
        clf.fit(X)
        inertias.append(float(clf.inertia_))
    
    # 找到肘部点（简化方法：找到 inertia 下降最慢的点）
    # 计算二阶导数
    second_derivatives = []
    for i in range(1, len(inertias) - 1):
        d2 = inertias[i-1] - 2*inertias[i] + inertias[i+1]
        second_derivatives.append(d2)
    
    # 找到最大二阶导数的点
    optimal_k_idx = second_derivatives.index(max(second_derivatives))
    optimal_k = k_values[optimal_k_idx + 1]
    
    return {
        "k_values": k_values,
        "inertias": inertias,
        "optimal_k": optimal_k
    }


# 使用示例
if __name__ == "__main__":
    """
    集成到 movie-ingest/analyzer.py:
    
    from analyzer import CommentAnalyzer
    
    analyzer = CommentAnalyzer()
    
    # 从数据库读取评论
    comments = analyzer.load_comments(movie_id)
    
    # 主题聚类
    result = cluster_comments_kmeans(comments, n_clusters=10)
    
    # 可视化
    visualize_clusters_pca(comments, result["labels"])
    
    # 找到最优聚类数量
    optimal = find_optimal_clusters(comments, max_k=20)
    print(f"推荐聚类数量: {optimal['optimal_k']}")
    """
    
    # 测试
    comments = [
        "这部电影剧情精彩，演员演技出色",
        "特效震撼，视觉效果一流",
        "剧情无聊，浪费时间",
        "演员表演到位，角色刻画深刻",
        "画面精美，摄影出色",
        "故事感人，情感真挚",
        "节奏拖沓，剧情松散",
        "导演功力深厚，叙事流畅"
    ]
    
    # KMeans 聚类
    result = cluster_comments_kmeans(comments, n_clusters=3)
    print(f"聚类结果: {result['labels']}")
    print(f"簇内距离: {result['inertia']}")
    
    # 找到最优聚类数量
    optimal = find_optimal_clusters(comments, max_k=5)
    print(f"推荐聚类数量: {optimal['optimal_k']}")