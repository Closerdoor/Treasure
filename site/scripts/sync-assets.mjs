import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const siteRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(siteRoot, '..');
const exportScript = path.join(repoRoot, 'tools', 'db', 'export-generated.mjs');

console.log('=== 导出数据与静态资源 ===\n');

process.chdir(repoRoot);

console.log('运行统一导出脚本...');
const result = spawnSync(process.execPath, [exportScript], {
  stdio: 'inherit'
});

if (result.status !== 0) {
  console.error('导出失败');
  process.exit(result.status ?? 1);
}

console.log('\n导出完成！');
