import { config } from "./config.js";
import { dispatchPipeline } from "./worker.js";

const args = process.argv.slice(2);

if (args.includes("--help")) {
  console.log(`
F1 Scheduler Service
  Cron-like dispatcher that enqueues pipeline jobs across services.

Usage:
  npm run dev                       Start scheduler in watch mode
  npm start                         Start scheduler
  tsx src/index.ts --dispatch 2026 R05  Dispatch pipeline for a specific race

Environment:
  REDIS_URL     Redis connection (default: redis://localhost:6379/0)
  API_URL       API base URL (default: http://localhost:8000/api/v1)
  DRY_RUN       Skip actual dispatches (default: false)

Pipeline stages: ingest -> annotate -> recon -> meshops -> publish
`);
  process.exit(0);
}

if (args.includes("--dry-run")) {
  (config as { DRY_RUN: boolean }).DRY_RUN = true;
  console.log("[scheduler] Running in dry-run mode");
}

// Manual dispatch mode
const dispatchIdx = args.indexOf("--dispatch");
if (dispatchIdx !== -1) {
  const season = parseInt(args[dispatchIdx + 1], 10);
  const race = args[dispatchIdx + 2];

  if (!season || !race) {
    console.error("Usage: --dispatch <season> <race>");
    process.exit(1);
  }

  await dispatchPipeline({ season, race });
  console.log("[scheduler] Dispatch complete");
  process.exit(0);
}

// Daemon mode: poll for new race weekends or listen for triggers
console.log("[scheduler] Scheduler started in daemon mode");
console.log("[scheduler] Waiting for triggers... (Ctrl+C to stop)");

// Keep process alive
setInterval(() => {
  // TODO: Check for upcoming race weekends and auto-dispatch
}, 60_000);
