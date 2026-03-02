import { Worker } from "bullmq";
import { config } from "./config.js";
import { processIngestJob } from "./worker.js";

const args = process.argv.slice(2);

if (args.includes("--help")) {
  console.log(`
F1 Ingest Service
  Accepts URLs/files, stores raw media and articles, writes evidence rows.

Usage:
  npm run dev           Start in development mode (watch)
  npm start             Start in production mode
  DRY_RUN=true npm dev  Run without side effects

Environment:
  REDIS_URL       Redis connection (default: redis://localhost:6379/0)
  API_URL         API base URL (default: http://localhost:8000/api/v1)
  MINIO_ENDPOINT  MinIO host (default: localhost)
  MINIO_PORT      MinIO port (default: 9000)
  DRY_RUN         Skip actual writes (default: false)
`);
  process.exit(0);
}

if (args.includes("--dry-run")) {
  (config as { DRY_RUN: boolean }).DRY_RUN = true;
  console.log("[ingest] Running in dry-run mode");
}

const worker = new Worker("ingest", processIngestJob, {
  connection: { host: config.REDIS_HOST, port: config.REDIS_PORT },
});

worker.on("completed", (job) => {
  console.log(`[ingest] Job ${job.id} completed`);
});

worker.on("failed", (job, err) => {
  console.error(`[ingest] Job ${job?.id} failed:`, err.message);
});

console.log("[ingest] Worker started, waiting for jobs...");
