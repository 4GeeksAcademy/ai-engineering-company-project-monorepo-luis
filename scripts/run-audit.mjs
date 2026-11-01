import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

const CHROME_PATH = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

export async function runLighthouseAudit({
  url,
  outputDir,
  name,
  preset = 'desktop', // 'desktop' or 'mobile'
}) {
  fs.mkdirSync(outputDir, { recursive: true });
  const outputPath = path.join(outputDir, name);

  console.log(`\n========================================`);
  console.log(`Running Lighthouse for ${name}`);
  console.log(`URL: ${url}`);
  console.log(`Preset: ${preset}`);
  console.log(`Output: ${outputPath}`);
  console.log(`========================================\n`);

  const args = [
    url,
    '--chrome-flags="--headless=new --no-sandbox"',
    '--output=html',
    '--output=json',
    `--output-path=${outputPath}`,
    '--quiet',
  ];

  if (preset === 'desktop') {
    args.push('--preset=desktop');
  }

  // Execute lighthouse CLI via npx.cmd
  await new Promise((resolve, reject) => {
    const isWindows = process.platform === 'win32';
    const npxCmd = isWindows ? 'npx.cmd' : 'npx';

    const env = { ...process.env, CHROME_PATH };
    const child = spawn(npxCmd, ['lighthouse', ...args], {
      cwd: projectRoot,
      env,
      shell: true,
      stdio: 'inherit',
    });

    child.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`Lighthouse exited with code ${code}`));
    });
  });

  // Check generated report files
  const htmlReport = `${outputPath}.report.html`;
  const jsonReport = `${outputPath}.report.json`;
  const pngPath = `${outputPath}.png`;

  if (!fs.existsSync(htmlReport)) {
    throw new Error(`Report HTML not generated at ${htmlReport}`);
  }

  console.log(`Generated HTML report: ${htmlReport}`);
  console.log(`Generated JSON report: ${jsonReport}`);

  // Extract score summary from JSON
  if (fs.existsSync(jsonReport)) {
    try {
      const data = JSON.parse(fs.readFileSync(jsonReport, 'utf-8'));
      const categories = data.categories || {};
      const perf = Math.round((categories.performance?.score || 0) * 100);
      const acc = Math.round((categories.accessibility?.score || 0) * 100);
      const bp = Math.round((categories['best-practices']?.score || 0) * 100);
      const seo = Math.round((categories.seo?.score || 0) * 100);

      const audits = data.audits || {};
      const lcp = audits['largest-contentful-paint']?.displayValue || 'N/A';
      const fcp = audits['first-contentful-paint']?.displayValue || 'N/A';
      const cls = audits['cumulative-layout-shift']?.displayValue || 'N/A';
      const tbt = audits['total-blocking-time']?.displayValue || 'N/A';
      const si = audits['speed-index']?.displayValue || 'N/A';

      console.log(`[Summary for ${name}]`);
      console.log(`  Performance:    ${perf}`);
      console.log(`  Accessibility:  ${acc}`);
      console.log(`  Best Practices: ${bp}`);
      console.log(`  SEO:            ${seo}`);
      console.log(`  FCP: ${fcp} | LCP: ${lcp} | CLS: ${cls} | TBT: ${tbt} | Speed Index: ${si}`);
    } catch (e) {
      console.warn(`Could not parse JSON report: ${e.message}`);
    }
  }

  // Capture screenshot of the HTML report using headless Chrome
  console.log(`Capturing report screenshot to ${pngPath}...`);
  await new Promise((resolve, reject) => {
    const fileUrl = `file:///${htmlReport.replace(/\\/g, '/')}`;
    const chrome = spawn(
      CHROME_PATH,
      [
        '--headless=new',
        `--screenshot=${pngPath}`,
        '--window-size=1280,1024',
        '--hide-scrollbars',
        fileUrl,
      ],
      { stdio: 'inherit' }
    );

    chrome.on('close', (code) => {
      if (code === 0 && fs.existsSync(pngPath)) {
        console.log(`Saved screenshot: ${pngPath}`);
        resolve();
      } else {
        console.warn(`Screenshot process exited with code ${code}`);
        resolve(); // Don't fail the audit if screenshot fails
      }
    });
  });

  return { htmlReport, jsonReport, pngPath };
}

// Configured test runs
export const AUDIT_TARGETS = [
  {
    name: 'website-home-mobile',
    url: 'http://localhost:5500/index.html',
    preset: 'mobile',
  },
  {
    name: 'website-home-desktop',
    url: 'http://localhost:5500/index.html',
    preset: 'desktop',
  },
  {
    name: 'website-application-desktop',
    url: 'http://localhost:5500/application.html',
    preset: 'desktop',
  },
  {
    name: 'backoffice-index-desktop',
    url: 'http://localhost:5502/index.html',
    preset: 'desktop',
  },
  {
    name: 'backoffice-inventory-desktop',
    url: 'http://localhost:5502/inventory.html',
    preset: 'desktop',
  },
];

// CLI runner: node scripts/run-audit.mjs [before|after] [target-name-filter]
if (process.argv[1] === __filename) {
  const stage = process.argv[2] || 'before';
  const filter = process.argv[3];
  const outputDir = path.join(projectRoot, 'audit', stage);

  const targets = filter
    ? AUDIT_TARGETS.filter((t) => t.name.includes(filter))
    : AUDIT_TARGETS;

  console.log(`Starting audit suite for stage: ${stage} (${targets.length} targets)`);

  (async () => {
    for (const target of targets) {
      await runLighthouseAudit({
        url: target.url,
        outputDir,
        name: target.name,
        preset: target.preset,
      });
    }
    console.log(`\nCompleted audit suite for stage: ${stage}!`);
  })().catch((err) => {
    console.error('Audit suite failed:', err);
    process.exit(1);
  });
}
