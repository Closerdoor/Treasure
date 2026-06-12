# Treasure 文档入口

本目录只保留少量“当前有效文档”。归档方案、阶段记录、验收报告、旧设计稿和临时讨论应放入 `docs/archive/`，只作为历史参考。

AI / Codex / Claude 进入项目后，优先按下面顺序阅读：

1. `docs/README.md`
   - 全局入口、当前主链路、文档阅读路线。
2. `docs/PROJECT.md`
   - 项目结构、目录职责、数据流和标准工作流。
3. `docs/STATUS.md`
   - 当前真实进度、数据量、已完成事项、已知问题和下一步。

如果归档文档、模块局部 README 或临时脚本文档与以上三份核心文档冲突，以 `docs/STATUS.md` 为准。

## 当前主线

Treasure 是一个精选型个人收藏馆，不是全量资料库。当前重点是把馆长筛选后的影视、书籍等作品整理成结构化本地数据库，再导出为可部署到 GitHub Pages 的 Astro 静态站。

主链路：

```text
temp-script/ 数据采集与实验
  -> .local/treasure.db
  -> tools/db/export-generated.mjs
  -> generated/ + site/public/assets/
  -> site/
  -> GitHub Pages
```

关键边界：

- `.local/treasure.db` 是本地结构化主数据源，不提交 Git。
- `.local/assets/` 是本地资源主源，不提交 Git。
- `generated/` 是 Astro 前台读取的数据源，不手工编辑。
- `site/public/assets/` 是前台可发布静态资源目录，由导出脚本重建。
- Astro 站点不直接读取 SQLite。
- Astro 站点不直接依赖 `temp-script/`。
- `temp-script/` 的职责止于采集、合并、资源本地化、预检和写入 `.local/treasure.db`。

## 当前模块状态

| 模块 | 当前状态 |
|---|---|
| 电影 | 已跑通稳定单部工作流：多源采集、合并、图片本地化、预检、入库、导出、Astro 渲染。当前数据库 251 部电影。下一阶段回到电影作品录入。 |
| 书籍 | 已跑通单本、小批量和网络小说 fast / manual fallback 批量补录流程。当前数据库 54 本书，书籍前台 `/book` 与 `/book/{id}` 已可访问。 |
| 音乐 | planned，尚未正式建模。 |
| 游戏 | planned，尚未正式建模。 |
| 本地后台 | `admin/` 为旁路人工校正工具，使用原生 Node + 定制前端，不使用 Directus。 |

## 常用命令

```bash
# 查看数据库统计
node tools/db/check-counts.mjs

# 导出 generated 数据与当前记录引用的静态资源
node tools/db/export-generated.mjs

# 构建 Astro 静态站
cd site
npm.cmd run build

# 启动 Astro 本地站点
cd site
npm.cmd run dev -- --host 127.0.0.1

# 启动本地后台管理
npm.cmd run admin
```

Windows PowerShell 下优先使用 `npm.cmd`，避免执行策略拦截 `npm.ps1`。

## 文档分工

| 文档 | 作用 |
|---|---|
| `README.md` | 入口、全局主链路、阅读路线 |
| `PROJECT.md` | 项目结构、目录职责、标准工作流、模块边界 |
| `STATUS.md` | 当前事实快照、数据量、完成项、风险、下一步 |
| `archive/` | 历史文档，仅在追溯旧决策时阅读 |

## 维护原则

- 优先更新 `docs/README.md`、`docs/PROJECT.md`、`docs/STATUS.md`。
- 不轻易新增长期文档；能并入三份核心文档的就并入。
- 阶段记录、验收报告、旧设计稿放入 `docs/archive/`。
- 当前事实和旧文档冲突时，以 `docs/STATUS.md` 为准。
- 数据量、完成量、覆盖率、缺口数量必须量化。
- 任何脚本里的限制性逻辑，例如只取前 N 条、跳过某数据源、降级处理，都必须在运行前说明并写入文档或脚本注释。
