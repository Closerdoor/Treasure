import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const scriptDir = path.join(root, "temp-script/movie-ingest");
const dataDir = path.join(scriptDir, "data");
const stagingDir = path.join(dataDir, "staging");
const rawDir = path.join(dataDir, "raw");
const assetsDir = path.join(dataDir, "assets/works");
const runDir = path.join(dataDir, "batch-runs/2026-06-13-media-validation");
const reportPath = path.join(runDir, "validation-report.json");

const archiveRoot = path.join(runDir, "skipped-existing-artifacts");
const timestamp = new Date().toISOString().replace(/[:.]/g, "-");

const staleIds = ["0101000252"];
const renames = [
  ["0101000254", "0101000252"],
  ["0101000255", "0101000253"],
  ["0101000256", "0101000254"],
];

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function moveIfExists(src, dest) {
  if (!fs.existsSync(src)) return false;
  ensureDir(path.dirname(dest));
  fs.renameSync(src, dest);
  return true;
}

function archiveArtifact(baseDir, id, label) {
  const src = path.join(baseDir, id);
  if (!fs.existsSync(src)) return false;
  const dest = path.join(archiveRoot, `${id}-${timestamp}`, label);
  moveIfExists(src, dest);
  return true;
}

function archiveStaging(id) {
  const src = path.join(stagingDir, `${id}.json`);
  if (!fs.existsSync(src)) return false;
  const dest = path.join(archiveRoot, `${id}-${timestamp}`, "staging.json");
  moveIfExists(src, dest);
  return true;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), { encoding: "utf8" });
}

function rewriteStagingId(oldId, newId) {
  const oldPath = path.join(stagingDir, `${oldId}.json`);
  const newPath = path.join(stagingDir, `${newId}.json`);
  const data = readJson(oldPath);
  data.id = newId;
  if (data.auditIdOverride?.previousId !== newId) {
    data.auditIdOverride = {
      previousId: oldId,
      id: newId,
      reason: "批量入库前按实际入库顺序重排 ID",
      updatedAt: new Date().toISOString(),
    };
  }
  writeJson(oldPath, data);
  moveIfExists(oldPath, newPath);
}

for (const id of staleIds) {
  archiveStaging(id);
  archiveArtifact(rawDir, id, "raw");
  archiveArtifact(assetsDir, id, "assets");
}

for (const [oldId, newId] of renames) {
  rewriteStagingId(oldId, newId);
  moveIfExists(path.join(rawDir, oldId), path.join(rawDir, newId));
  moveIfExists(path.join(assetsDir, oldId), path.join(assetsDir, newId));
}

const report = readJson(reportPath);
for (const item of report.items || []) {
  const pair = renames.find(([oldId]) => oldId === item.workId);
  if (!pair) continue;
  const [oldId, newId] = pair;
  item.idOverride = {
    previousId: oldId,
    id: newId,
    reason: "批量入库前按实际入库顺序重排 ID",
    updatedAt: new Date().toISOString(),
  };
  item.workId = newId;
  item.expectedWorkId = newId;
  if (item.summary) item.summary.id = newId;
  item.stagingPath = path.join(stagingDir, `${newId}.json`);
  item.rawDir = path.join(rawDir, newId);
}
writeJson(reportPath, report);

console.log(JSON.stringify({
  archived: staleIds,
  renames: renames.map(([from, to]) => ({ from, to })),
  report: reportPath,
}, null, 2));
