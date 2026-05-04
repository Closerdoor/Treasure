# 图片展示尺寸规范

> 当前说明：本文档保留为图片抓取与人工审阅时的视觉参考。
> 当前资源主目录已切换到 `site/public/assets/`，页面最终展示以站点实现与导出结果为准。

本文档定义电影条目中各类图片的展示尺寸标准，确保所有电影页面视觉一致性。

## 图片尺寸标准

| 图片类型 | 容器宽度 | 图片尺寸 | 高度 | 样式 |
|----------|----------|----------|------|------|
| 主演头像 | 120px | 100px | 100px | `border-radius: 4px; object-fit: cover;` |
| 海报 | 160px | 160px | 自适应 | `border-radius: 4px;` |
| 剧照 | 200px | 200px | 自适应 | `border-radius: 4px;` |
| 视频缩略图 | 280px | 280px | 自适应 | `border-radius: 4px;` |
| 主海报（顶部） | - | 200px | 自适应 | `border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);` |

## HTML 模板

### 主演头像

```html
<div style="width: 120px; text-align: center;">
<img src="images/avatar-xxx.jpg" width="100" height="100" style="border-radius: 4px; object-fit: cover;"><br>
<strong>演员名</strong><br>
<small>Actor Name</small><br>
<small>饰 角色</small>
</div>
```

### 海报

```html
<div style="width: 160px;">
<img src="images/poster-xx.jpg" width="160" style="border-radius: 4px;"><br>
</div>
```

### 剧照

```html
<div style="width: 200px;">
<img src="images/still-xx.jpg" width="200" style="border-radius: 4px;"><br>
</div>
```

### 视频缩略图

```html
<div style="width: 280px;">
<img src="images/video-trailer-xx.png" width="280" style="border-radius: 4px;"><br>
<strong>预告片标题</strong><br>
<small>时长：XX:XX | [豆瓣](链接)</small>
</div>
```

## 图片容器布局

所有图片容器使用 Flexbox 布局：

```html
<div style="display: flex; flex-wrap: wrap; gap: 16px; margin: 16px 0;">
  <!-- 图片容器 -->
</div>
```

- `gap: 16px` - 主演头像、视频缩略图
- `gap: 12px` - 海报、剧照

## 图片命名规范

| 类型 | 命名格式 | 示例 |
|------|----------|------|
| 主海报 | `poster-main.jpg` | poster-main.jpg |
| 海报列表 | `poster-NN.jpg` | poster-01.jpg, poster-02.jpg |
| 剧照 | `still-NN.jpg` | still-01.jpg, still-02.jpg |
| 头像 | `avatar-姓名拼音.扩展名` | avatar-tim-robbins.png |
| 视频缩略图 | `video-trailer-NN.png` | video-trailer-01.png |

## 图片来源优先级

| 图片类型 | 优先来源 | 备选来源 |
|----------|----------|----------|
| 海报 | 豆瓣 | OMDb |
| 剧照 | 豆瓣 | - |
| 头像 | Wikipedia | 豆瓣、IMDb |
| 视频缩略图 | 豆瓣预告片页 | - |

## 图片下载技术要点

### 豆瓣图片

```powershell
# 需要带 Referer header 绕过防盗链
Invoke-WebRequest -Uri $url -OutFile $outFile -Headers @{Referer="https://movie.douban.com/"}
```

### Wikipedia 图片

```powershell
# 无防盗链，直接下载
Invoke-WebRequest -Uri $url -OutFile $outFile
```

## 更新记录

| 日期 | 变更 |
|------|------|
| 2026-05-01 | 初始版本，基于《肖申克的救赎》模板 |
