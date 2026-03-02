import type { Job } from "bullmq";
import { config } from "./config.js";

export interface IngestJobData {
  type: "media" | "article";
  source_url?: string;
  local_path?: string;
  upgrade_id?: string;
  metadata?: Record<string, unknown>;
}

export async function processIngestJob(job: Job<IngestJobData>): Promise<void> {
  const { type, source_url, local_path } = job.data;

  console.log(`[ingest] Processing ${type} job ${job.id}`, {
    source_url,
    local_path,
  });

  if (config.DRY_RUN) {
    console.log(`[ingest] DRY RUN: would store ${type} from ${source_url ?? local_path}`);
    return;
  }

  // TODO: Implement actual ingestion logic
  // 1. Fetch/read the source
  // 2. Store raw content in MinIO (raw/media/... or raw/articles/...)
  // 3. Write evidence row via API with source, license, credibility_score
  console.log(`[ingest] Job ${job.id} completed (placeholder)`);
}
