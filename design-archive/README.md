# Design Archive

> 本目录存放项目早期设计阶段的产物，已过时，仅供参考。

---

## 目录结构

```
design-archive/
├── pencil-new.pen      # Pencil 设计工具源文件
├── drafts/             # 早期 HTML/CSS 探索性草稿
├── output/             # Pencil 导出的设计稿截图
├── references/         # 设计参考素材
└── system/             # 早期设计系统文档
```

---

## 各部分说明

### pencil-new.pen

Pencil 设计工具的源文件，包含首页等页面的设计稿。

- 创建时间：2026/4/30
- 最后修改：2026/5/2
- 可用 Pencil 工具打开查看或重新导出截图

**Frame ID 对照**：
- `bi8Au` - 首页设计稿

---

### drafts/

早期 HTML/CSS 探索性草稿，用于测试卡片布局、主题切换等 UI 方案。

| 文件 | 说明 |
|------|------|
| `movie-list-card.html` | 电影列表卡片设计稿（网格/列表双视图） |
| `movie-list-card-b-comparison.html` | 布局 B 方案对比（4 种方案） |
| `index-movie-list.html` | 电影列表页骨架（简单版） |
| `index-movie-detail.html` | 电影详情页骨架（简单版） |
| `index-home.html` | 首页骨架（简单版） |
| `style-movie-list.css` | 电影列表页样式 |
| `style-movie-detail.css` | 电影详情页样式 |
| `style-home.css` | 首页样式 |

**状态**：已过时
- 前台已用 Astro 实现，样式已整合到 `site/src/styles/global.css`
- 图片引用路径指向旧目录（已迁移到 `site/public/assets/`）

---

### output/

Pencil 导出的设计稿截图。

| 文件 | Frame ID | 说明 |
|------|----------|------|
| `bi8Au.png` | bi8Au | 首页设计稿截图 |
| `IqwVf.png` | IqwVf | 其他页面截图 |
| `IfqJZ.png` | IfqJZ | 其他页面截图 |

**状态**：可从 `pencil-new.pen` 重新生成

---

### references/

设计参考素材，包含外部网站截图和 AI 生成图片。

| 文件 | 大小 | 说明 |
|------|------|------|
| `douban-cast-layout.png` | 174 KB | 豆瓣演员列表布局参考 |
| `search-box.jpg` | 62 KB | 搜索框设计参考截图 |
| `gemini-image-01.png` | 6.7 MB | Gemini 生成的图片 |
| `gemini-image-02.png` | 6.8 MB | Gemini 生成的图片 |
| `pic-01.jpg` | 99 KB | 临时截图 |
| `pic-02.jpg` | 78 KB | 临时截图 |

**来源**：原 `reference-assets/` 目录，2026/5/3 添加

---

### system/treasure/MASTER.md

早期设计系统文档，定义了颜色、字体、间距、组件规范。

**状态**：与实际实现已脱节

| 项目 | 文档定义 | 实际实现 |
|------|----------|----------|
| Primary | `#171717` | `#0b0d12` |
| Accent | `#D4AF37` (金色) | `#84a9ff` (蓝紫渐变) |
| 字体 | Inter | Noto Serif SC + LXGW WenKai |
| 风格 | Minimal + Gold | 深色资料馆风格 |

当前实际样式见 `site/src/styles/global.css`。

---

## 当前设计参考

如需了解当前前台设计：

- 样式文件：`site/src/styles/global.css`
- 组件目录：`site/src/components/`
- 页面目录：`site/src/pages/`
- UI 指南：`docs/UI-GUIDE.md`

---

## 保留原因

- 记录设计探索过程
- 方便回溯历史决策
- 不参与构建流程