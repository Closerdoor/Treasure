# Treasure Admin

本目录是原生 Node 本地数据库维护后台，作为旁路工具直接读写 `.local/treasure.db`。当前方案不使用 Directus。

它不参与 Astro 构建，不读取 `generated/`，也不会自动导出前台数据。人工校正完成后，仍然使用既有主链路：

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
