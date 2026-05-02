# Treasure Docs

当前有效文档只看下面 5 份，按此顺序阅读：

1. `PROJECT.md`
   - 项目定位、当前阶段目标、V1 范围、已确认方向、待确认事项
2. `STATUS.md`
   - 当前阶段进度、已完成内容、当前待办、下一步、风险与阻塞
3. `ARCHITECTURE.md`
   - 展示站点与本地工坊的结构边界、模块划分、页面层级、路由与数据层级
4. `CONTRACTS.md`
   - 数据模型、模板骨架、字段语义、变更联动规则
5. `UI-GUIDE.md`
   - 当前生效的 UI 方向、页面结构与交互结论

归档参考：

- `archive/2026-05-doc-reset/`
  - 本轮文档重构前的旧设计文档，仅作历史参考，不再作为当前规范。

额外说明：

- 电影录入执行细则不在 `docs/` 主文档体系中维护，而继续以 `.opencode/skills/movie-entry-workflow/` 下文档为准。
- 如果主文档与 workflow 细则冲突：
  - 项目方向与产品边界以 `PROJECT.md` / `ARCHITECTURE.md` 为准
  - 电影录入执行细节以 `movie-entry-workflow` 文档为准
