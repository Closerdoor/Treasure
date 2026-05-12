# Treasure Docs

本目录记录 Treasure 项目的当前有效上下文。以后接手项目时，优先从本文件开始读。

## 推荐阅读顺序

1. `PROJECT.md`
   - 项目定位、当前阶段、V1 范围、暂不做的事情。
2. `STATUS.md`
   - 当前真实状态、最近校验结果、已知风险、下一步建议。
3. `ARCHITECTURE.md`
   - 展示站点、本地内容工坊、数据库、导出产物、静态资源之间的边界。
4. `WORKFLOW.md`
   - 从爬取/录入到 GitHub Pages 发布的标准工作流。
5. `GENERATED-DATA.md`
   - `generated/` 目录结构、JSON 契约、资源引用规则和当前校验项。
6. `DATABASE.md`
   - SQLite / Prisma 当前表结构与数据统计。
7. `CONTRACTS.md`
   - 页面消费字段、内容字段语义、跨模块数据契约。
8. `UI-GUIDE.md`
   - 当前前台视觉与交互方向。
9. `DOCS-MAINTENANCE.md`
   - 文档维护规则：什么时候更新哪份文档。

## 当前有效主线

```text
爬取/录入脚本
  -> SQLite: .local/treasure.db
  -> 导出脚本: tools/db/export-generated.mjs
  -> generated/*.json
  -> site/public/assets/*
  -> Astro static build
  -> GitHub Pages
```

## 当前阶段

项目已经从早期样板进入 **DB-first 静态站闭环整理阶段**。

当前重点不是继续堆新爬虫，而是把下面三件事稳定下来：

- 数据库是否能稳定导出完整 `generated/`。
- Astro 是否只依赖 `generated/` 和 `site/public/assets/` 完成静态构建。
- 发布前是否能量化报告数据与资源覆盖率。

## 文档状态约定

- `docs/README.md` 是文档入口。
- `PROJECT.md` / `STATUS.md` / `ARCHITECTURE.md` / `WORKFLOW.md` / `GENERATED-DATA.md` 是当前最重要的五份文档。
- `archive/` 下内容仅作历史参考，不作为当前规范。
- `temp-script/` 下 README 或临时分析文档只代表实验阶段结论，不能覆盖 `docs/` 主文档。

## 常用命令

```bash
# 导出数据库到 generated/
node tools/db/export-generated.mjs

# 同步资源并导出数据
cd site
npm.cmd run sync

# 构建 Astro 静态站
cd site
npm.cmd run build

# 查看数据库统计
node tools/db/check-counts.mjs
```

Windows PowerShell 下如果 `npm run build` 被执行策略拦截，使用 `npm.cmd run build`。
