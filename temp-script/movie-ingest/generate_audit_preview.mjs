import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const runDir = path.join(root, "temp-script/movie-ingest/data/batch-runs/2026-06-13-media-validation");
const stagingDir = path.join(root, "temp-script/movie-ingest/data/staging");
const assetsDir = path.join(root, "temp-script/movie-ingest/data/assets/works");
const reportPath = path.join(runDir, "validation-report.json");

const titleOverrides = new Map([
  ["0301000043", "星之梦~星之人"],
  ["0302000001", "食灵零"],
]);

const profileLabels = {
  live_action_movie: "电影",
  documentary_film: "纪录片",
  documentary_series: "纪录片",
  animated_movie: "动画电影",
  live_action_series: "电视剧",
  animated_series: "番剧",
};

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), { encoding: "utf8" });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"]/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
  })[ch]);
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asText(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(asText).filter(Boolean).join("\n");
  if (typeof value === "object") {
    return value.text || value.summary || value.content || JSON.stringify(value, null, 2);
  }
  return String(value);
}

function firstNames(people, count = 8) {
  return asArray(people)
    .slice(0, count)
    .map((person) => person?.name || person?.nameEn)
    .filter(Boolean)
    .join("、");
}

function ratingLine(work) {
  const parts = [];
  if (work?.doubanRating) {
    parts.push(`豆瓣 ${work.doubanRating}${work.doubanVotes ? ` (${work.doubanVotes})` : ""}`);
  }
  if (work?.imdbRating) {
    parts.push(`IMDb ${work.imdbRating}${work.imdbVotes ? ` (${work.imdbVotes})` : ""}`);
  }
  if (work?.tmdbRating) {
    parts.push(`TMDB ${work.tmdbRating}${work.tmdbVotes ? ` (${work.tmdbVotes})` : ""}`);
  }
  const ratings = work?.ratings;
  if (ratings?.douban?.score) {
    parts.push(`豆瓣 ${ratings.douban.score}${ratings.douban.count ? ` (${ratings.douban.count})` : ""}`);
  }
  if (ratings?.imdb?.score) {
    parts.push(`IMDb ${ratings.imdb.score}${ratings.imdb.count ? ` (${ratings.imdb.count})` : ""}`);
  }
  if (ratings?.tmdb?.score) {
    parts.push(`TMDB ${ratings.tmdb.score}${ratings.tmdb.count ? ` (${ratings.tmdb.count})` : ""}`);
  }
  return [...new Set(parts)].join(" / ");
}

function fileUrl(filePath) {
  return `file:///${filePath.replace(/\\/g, "/")}`;
}

function posterSrc(work) {
  const poster = work.images?.poster;
  if (!poster) return "";
  const fullPath = path.join(assetsDir, work.id, poster.replace(/\//g, path.sep));
  return fs.existsSync(fullPath) ? fileUrl(fullPath) : "";
}

function resourceCounts(work) {
  const images = work.images || {};
  return [
    `封面 ${Object.keys(images.covers || {}).length}`,
    `海报 ${asArray(images.posters).length}`,
    `剧照 ${asArray(images.stills).length}`,
    `壁纸 ${asArray(images.wallpapers).length}`,
    `视频 ${asArray(work.videos).length}`,
    `短评 ${asArray(work.comments).length}`,
    `影评 ${asArray(work.reviews).length}`,
  ].join(" / ");
}

function externalIds(work) {
  return [
    work.doubanId ? `豆瓣 ${work.doubanId}` : "",
    work.imdbId ? `IMDb ${work.imdbId}` : "",
    work.tmdbId ? `TMDB ${work.tmdbId}` : "",
  ].filter(Boolean).join(" / ");
}

function compactText(value, maxLength) {
  const text = asText(value).replace(/\s+/g, " ").trim();
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

function applyTitleOverrides(report) {
  const updatedAt = new Date().toISOString();

  for (const [workId, title] of titleOverrides) {
    const stagingPath = path.join(stagingDir, `${workId}.json`);
    const staging = readJson(stagingPath);
    const previousTitle = staging.auditTitleOverride?.previousTitle || staging.title;
    staging.auditTitleOverride = {
      previousTitle,
      title,
      reason: "用户审核要求使用馆内标题",
      updatedAt,
    };
    staging.title = title;
    writeJson(stagingPath, staging);
  }

  for (const item of report.items || []) {
    if (!titleOverrides.has(item.workId)) continue;
    const title = titleOverrides.get(item.workId);
    item.titleOverride = {
      previousTitle: item.titleOverride?.previousTitle || item.summary?.title,
      title,
      reason: "用户审核要求使用馆内标题",
      updatedAt,
    };
    if (item.summary) item.summary.title = title;
  }
}

function renderWork(item, work) {
  const poster = posterSrc(work);
  const override = work.auditTitleOverride
    ? `<div class="override">标题已改：${escapeHtml(work.auditTitleOverride.previousTitle)} → ${escapeHtml(work.title)}</div>`
    : "";
  const synopsis = compactText(work.synopsis || work.summary || work.introduction, 520);
  const story = compactText(work.story, 680);

  return `<section class="work">
    <div class="poster">${poster ? `<img src="${poster}" alt="${escapeHtml(work.title)}">` : "<div class=\"empty\">无封面</div>"}</div>
    <div class="main">
      <div class="topline">
        <span class="id">${escapeHtml(work.id)}</span>
        <span class="badge">${escapeHtml(profileLabels[work.schemaType] || work.schemaType)}</span>
        <span>${escapeHtml(work.module)}/${escapeHtml(work.submodule)}</span>
      </div>
      <h2>${escapeHtml(work.title)}</h2>
      ${override}
      <div class="grid">
        <div><b>输入名</b><span>${escapeHtml(item.input?.title || "-")}</span></div>
        <div><b>原名</b><span>${escapeHtml(work.originalTitle || "-")}</span></div>
        <div><b>年份</b><span>${escapeHtml(work.year || "-")}</span></div>
        <div><b>国家/语言</b><span>${escapeHtml([work.country, work.language].filter(Boolean).join(" / ") || "-")}</span></div>
        <div><b>时长/集数</b><span>${escapeHtml([
          work.runtime ? `${work.runtime}分钟` : "",
          work.episodeCount ? `${work.episodeCount}集` : "",
          work.episodeTime ? `单集${work.episodeTime}分钟` : "",
        ].filter(Boolean).join(" / ") || "-")}</span></div>
        <div><b>外部 ID</b><span>${escapeHtml(externalIds(work) || "-")}</span></div>
        <div><b>类型</b><span>${escapeHtml(asArray(work.genre).join("、") || "-")}</span></div>
        <div><b>评分</b><span>${escapeHtml(ratingLine(work) || "-")}</span></div>
        <div><b>导演</b><span>${escapeHtml(firstNames(work.director) || "-")}</span></div>
        <div><b>主演</b><span>${escapeHtml(firstNames(work.cast) || "-")}</span></div>
        <div><b>资源</b><span>${escapeHtml(resourceCounts(work))}</span></div>
        <div><b>预检</b><span class="ok">通过</span></div>
      </div>
      <details>
        <summary>简介 / 剧情预览</summary>
        <p>${escapeHtml(synopsis || "无简介")}</p>
        ${story ? `<p>${escapeHtml(story)}</p>` : ""}
      </details>
    </div>
  </section>`;
}

const report = readJson(reportPath);
applyTitleOverrides(report);
writeJson(reportPath, report);

const completed = (report.items || []).filter((item) => item.status === "completed");
const works = completed.map((item) => ({
  item,
  work: readJson(path.join(stagingDir, `${item.workId}.json`)),
}));

const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>媒体批量入库审核预览</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f6f7f9;color:#20242a;font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}.wrap{max-width:1280px;margin:0 auto;padding:28px}header{margin-bottom:18px}h1{font-size:26px;margin:0 0 8px}.meta{color:#5f6875}.summary{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}.pill{background:#fff;border:1px solid #dce1e8;border-radius:8px;padding:8px 12px}.work{display:grid;grid-template-columns:150px 1fr;gap:18px;background:#fff;border:1px solid #dfe4eb;border-radius:8px;padding:16px;margin:14px 0}.poster{width:150px;aspect-ratio:2/3;background:#e8ebef;border-radius:6px;overflow:hidden;display:flex;align-items:center;justify-content:center;color:#7b8490}.poster img{width:100%;height:100%;object-fit:cover}.topline{display:flex;gap:8px;align-items:center;color:#65707d;font-size:13px}.id{font-family:Consolas,monospace}.badge{background:#eef6ff;color:#075a9a;border:1px solid #cfe5ff;border-radius:6px;padding:1px 7px}h2{font-size:22px;line-height:1.25;margin:6px 0 8px}.override{color:#9a5b00;background:#fff7e6;border:1px solid #ffe0a3;border-radius:6px;padding:6px 8px;margin:6px 0 10px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.grid div{border-top:1px solid #edf0f4;padding-top:8px;min-width:0}.grid b{display:block;color:#5f6875;font-size:12px;font-weight:600}.grid span{display:block;word-break:break-word}.ok{color:#087b37;font-weight:700}details{margin-top:12px;border-top:1px solid #edf0f4;padding-top:10px}summary{cursor:pointer;color:#075a9a}@media(max-width:760px){.wrap{padding:14px}.work{grid-template-columns:90px 1fr}.poster{width:90px}.grid{grid-template-columns:1fr}h2{font-size:18px}}
</style>
</head>
<body><div class="wrap">
<header>
  <h1>媒体批量入库审核预览</h1>
  <div class="meta">生成时间：${escapeHtml(new Date().toLocaleString("zh-CN"))}；来源：2026-06-13-media-validation；用于审核本批采集结果与字段质量。</div>
</header>
<div class="summary">
  <div class="pill">输入总量：${report.total}</div>
  <div class="pill">可入库 staging：${completed.length}</div>
  <div class="pill">已入库跳过：${report.skipped}</div>
  <div class="pill">失败：${report.failed}</div>
</div>
${works.map(({ item, work }) => renderWork(item, work)).join("\n")}
</div></body></html>
`;

const previewPath = path.join(runDir, "audit-preview.html");
fs.writeFileSync(previewPath, html, { encoding: "utf8" });
console.log(previewPath);
