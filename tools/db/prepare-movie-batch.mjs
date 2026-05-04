import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..');

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) {
      continue;
    }

    const key = token.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith('--')) {
      args[key] = true;
      continue;
    }

    args[key] = next;
    index += 1;
  }
  return args;
}

function printUsage() {
  console.log('Usage: node tools/db/prepare-movie-batch.mjs --input <candidates.json> [--output <file>] [--accept-auto]');
}

function defaultOutputPath(inputPath) {
  const baseName = path.basename(inputPath, path.extname(inputPath)).replace(/\.candidates$/i, '');
  return path.join('.local', 'batches', `${baseName}.tasks.json`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input || args.help) {
    printUsage();
    return;
  }

  const inputPath = path.resolve(repoRoot, args.input);
  const raw = await fs.readFile(inputPath, 'utf8');
  const payload = JSON.parse(raw);
  const items = Array.isArray(payload.items) ? payload.items : [];

  const tasks = [];
  const unresolved = [];

  for (const item of items) {
    const selectedDoubanId = item.selectedDoubanId || (args['accept-auto'] ? item.autoSelection?.doubanId : null);
    const candidate = item.candidates?.find((entry) => entry.doubanId === selectedDoubanId) || null;

    if (!selectedDoubanId || !candidate) {
      unresolved.push({
        query: item.query,
        reason: selectedDoubanId ? 'selectedDoubanId not found in candidates' : 'missing selectedDoubanId'
      });
      continue;
    }

    tasks.push({
      query: item.query,
      doubanId: candidate.doubanId,
      title: candidate.title,
      originalTitle: candidate.originalTitle || null,
      year: candidate.year,
      type: candidate.type,
      subjectUrl: candidate.subjectUrl,
      posterUrl: candidate.posterUrl || null,
      source: item.selectedDoubanId ? 'manual' : 'auto'
    });
  }

  if (unresolved.length) {
    throw new Error(`Cannot build batch tasks, unresolved items: ${unresolved.map((item) => item.query).join(', ')}`);
  }

  const outputPath = path.resolve(repoRoot, args.output || defaultOutputPath(args.input));
  await fs.mkdir(path.dirname(outputPath), { recursive: true });

  const result = {
    version: 1,
    generatedAt: new Date().toISOString(),
    source: path.relative(repoRoot, inputPath).replace(/\\/g, '/'),
    workflow: 'movie_batch_tasks',
    totalTasks: tasks.length,
    tasks
  };

  await fs.writeFile(outputPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  console.log(`Generated task file: ${path.relative(repoRoot, outputPath).replace(/\\/g, '/')}`);
  console.log(`tasks=${result.totalTasks}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
