# Treasure Admin

本目录是原生 Node 本地数据库维护后台，作为旁路工具直接读写 `.local/treasure.db`。当前方案不使用 Directus。

它不参与 Astro 构建，也不读取 `generated/`。影视作品保存后会自动导出前台数据；人工校正完成后，若要构建或发布前台，仍然使用既有主链路：

```bash
node tools/db/export-generated.mjs
cd site
npm.cmd run build
```

启动：

```bash
npm.cmd run admin
```

默认地址：

```text
http://127.0.0.1:4317
```

启动时会在 `.local/backup/` 下写入一次 `treasure-admin-YYYYMMDDHHMM.db` 备份。

影视作品编辑页采用左侧表单、右侧前台预览的结构。字段表单会同时展示数据库字段名、中文说明和前台用途；保存影视作品基础信息、结构化 JSON、演职员关系或分类关系后，会自动执行：

```bash
node tools/db/export-generated.mjs
```

因此本地 Astro 前台刷新后可以看到最新 generated 数据。书籍模块当前仍保留基础编辑能力，尚未接入前台 generated 链路。

## 当前功能

- 影视作品列表、搜索、状态筛选和分页。
- 影视作品新增、删除、基础字段编辑。
- 影视结构化 JSON 字段编辑，包括评分、图片、外部来源、上映日期、视频、评论、关联作品、名言、别名、原声和角色。
- 影视演职员关系维护，包括检索人物、添加人物、修改部门 / 职位 / 角色、删除关系。
- 影视分类和标签关系维护。
- 影视编辑页右侧前台预览，用于快速检查标题、海报、评分、简介、字段映射、内容块数量和演职员展示效果。
- 书籍基础字段与 JSON 字段维护。

## 当前边界

- 不做用户登录和权限管理，仅作为本机工具使用。
- 暂不提供字段级审计日志；后台 API 修改不会记录 before / after 历史。
- 不替代采集脚本，也不负责抓取外部数据。
- 不参与 Astro build；构建和发布仍使用 `site/` 的静态构建流程。
