import { Worker } from "bullmq";
import { config } from "./config.js";
import { processAnnotateJob } from "./worker.js";

const args = process.argv.slice(2);

if (args.includes("--help")) {
  console.log(`
F1 Annotate Service
  Reads evidence, generates structured hypotheses via LLM, writes callouts.

Usage:
  npm run dev           Start in development mode (watch)
  npm start             Start in production mode
  DRY_RUN=true npm dev  Run without side effects

Environment:
  REDIS_URL     Redis connection (default: redis://localhost:6379/0)
  API_URL       API base URL (default: http://localhost:8000/api/v1)
  LLM_API_KEY   LLM API key for annotation
  LLM_MODEL     LLM model to use (default: claude-sonnet-4-6)
  DRY_RUN       Skip actual writes (default: false)
`);
  process.exit(0);
}

if (args.includes("--dry-run")) {
  (config as { DRY_RUN: boolean }).DRY_RUN = true;
  console.log("[annotate] Running in dry-run mode");
}

const worker = new Worker("annotate", processAnnotateJob, {
  connection: { host: config.REDIS_HOST, port: config.REDIS_PORT },
});

worker.on("completed", (job) => {
  console.log(`[annotate] Job ${job.id} completed`);
});

worker.on("failed", (job, err) => {
  console.error(`[annotate] Job ${job?.id} failed:`, err.message);
});

console.log("[annotate] Worker started, waiting for jobs...");
