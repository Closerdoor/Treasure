import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { PATHS } from './paths.mjs';

const repoRoot = PATHS.repoRoot;
const scriptRoot = PATHS.scriptRoot;

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) continue;
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

function runNode(scriptPath, scriptArgs) {
  const result = spawnSync(process.execPath, [scriptPath, ...scriptArgs], {
    encoding: 'utf8',
    cwd: repoRoot,
    shell: false
  });

  return {
    status: result.status ?? 1,
    stdout: result.stdout?.trim() ?? '',
    stderr: result.stderr?.trim() ?? ''
  };
}

function runCommand(command, args, workdir = repoRoot) {
  const result = spawnSync(command, args, {
    encoding: 'utf8',
    cwd: workdir,
    shell: false
  });

  return {
    status: result.status ?? 1,
    stdout: result.stdout?.trim() ?? '',
    stderr: result.stderr?.trim() ?? ''
  };
}

function parseJsonOutput(stepName, output) {
  try {
    return JSON.parse(output);
  } catch {
    throw new Error(`${stepName} did not output valid JSON`);
  }
}

function assertOk(stepName, result) {
  if (result.status !== 0) {
    throw new Error(`${stepName} failed:\n${result.stderr || result.stdout || 'no output'}`);
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input) {
    console.log('Usage: node db_tools/run-movie-batch-workflow.mjs --input <tasks.json> [--output-mode staging] [--full-pipeline] [--allow-skipped] [--enforce-high-standard]');
    return;
  }

  const outputMode = 'staging';
  const enforceHighStandard = Boolean(args['enforce-high-standard']);
  const intakeScript = path.join(scriptRoot, 'db_tools', 'run-movie-intake-from-tasks.mjs');
  const qualityScript = path.join(scriptRoot, 'db_tools', 'check-movie-ingest-quality.mjs');

  const intake = runNode(intakeScript, ['--input', args.input, '--output-mode', outputMode]);
  assertOk('intake', intake);
  const intakePayload = parseJsonOutput('intake', intake.stdout);

  if (!args['allow-skipped'] && Array.isArray(intakePayload.skipped) && intakePayload.skipped.length) {
    throw new Error(`intake skipped unresolved tasks: ${intakePayload.skipped.map((item) => item.doubanId || item.query).join(', ')}`);
  }

  const createdIds = Array.isArray(intakePayload.created) ? intakePayload.created.map((item) => item.id).filter(Boolean) : [];
  if (!createdIds.length) {
    throw new Error('intake created no records');
  }

  const qualityArgs = ['--ids', createdIds.join(','), '--mode', outputMode, '--strict'];
  if (enforceHighStandard) {
    qualityArgs.push('--enforce-high-standard');
  }

  const quality = runNode(qualityScript, qualityArgs);
  assertOk('quality check', quality);
  const qualityPayload = parseJsonOutput('quality check', quality.stdout);

  const pipeline = [];
  if (args['full-pipeline']) {
    const importStep = runNode(path.join(scriptRoot, 'db_tools', 'import-movie.mjs'), []);
    assertOk('import', importStep);
    pipeline.push({ step: 'import', ok: true, stdout: importStep.stdout });

    const exportStep = runNode(path.join(repoRoot, 'tools', 'db', 'export-generated.mjs'), []);
    assertOk('export', exportStep);
    pipeline.push({ step: 'export', ok: true, stdout: exportStep.stdout });

    const assetsStep = runNode(path.join(repoRoot, 'tools', 'db', 'check-assets.mjs'), []);
    assertOk('check-assets', assetsStep);
    pipeline.push({ step: 'check-assets', ok: true, stdout: assetsStep.stdout });

    const buildStep = runCommand('npm', ['run', 'build'], path.join(repoRoot, 'site'));
    assertOk('build', buildStep);
    pipeline.push({ step: 'build', ok: true, stdout: buildStep.stdout });
  }

  const payload = {
    version: 1,
    generatedAt: new Date().toISOString(),
    input: args.input,
    outputMode,
    enforceHighStandard,
    created: intakePayload.created,
    skipped: intakePayload.skipped,
    quality: qualityPayload,
    pipeline
  };

  console.log(JSON.stringify(payload, null, 2));
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
