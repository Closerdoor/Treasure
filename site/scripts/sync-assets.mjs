import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { existsSync, cpSync, mkdirSync } from 'node:fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const siteRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(siteRoot, '..');
const exportScript = path.join(repoRoot, 'tools', 'db', 'export-generated.mjs');

const localAssetsRoot = path.join(repoRoot, '.local', 'assets');
const publicAssetsRoot = path.join(siteRoot, 'public', 'assets');

console.log('=== 同步资源 ===\n');

// 1. 运行导出脚本
console.log('1. 导出数据...');
const result = spawnSync(process.execPath, [exportScript], {
  cwd: repoRoot,
  stdio: 'inherit'
});

if (result.status !== 0) {
  console.error('导出失败');
  process.exit(result.status ?? 1);
}

// 2. 同步图片资源
console.log('\n2. 同步图片资源...');

function syncDir(src, dest) {
  if (!existsSync(src)) {
    console.log(`  跳过: ${src} (不存在)`);
    return;
  }
  
  mkdirSync(path.dirname(dest), { recursive: true });
  cpSync(src, dest, { recursive: true });
  console.log(`  复制: ${src} -> ${dest}`);
}

// 同步电影图片
const movieSrc = path.join(localAssetsRoot, 'video', 'movie');
const movieDest = path.join(publicAssetsRoot, 'video', 'movie');
syncDir(movieSrc, movieDest);

// 同步人物头像
const peopleSrc = path.join(localAssetsRoot, 'people');
const peopleDest = path.join(publicAssetsRoot, 'people');
syncDir(peopleSrc, peopleDest);

console.log('\n同步完成！');
