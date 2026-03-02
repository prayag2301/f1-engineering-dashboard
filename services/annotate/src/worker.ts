import type { Job } from "bullmq";
import { config } from "./config.js";

export interface AnnotateJobData {
  upgrade_id: string;
  evidence_ids: string[];
}

export async function processAnnotateJob(job: Job<AnnotateJobData>): Promise<void> {
  const { upgrade_id, evidence_ids } = job.data;

  console.log(`[annotate] Processing upgrade ${upgrade_id} with ${evidence_ids.length} evidence items`);

  if (config.DRY_RUN) {
    console.log(`[annotate] DRY RUN: would annotate upgrade ${upgrade_id}`);
    return;
  }

  // TODO: Implement actual annotation logic
  // 1. Fetch evidence from API
  // 2. Send to LLM for structured extraction
  // 3. Write hypotheses[] to upgrade
  // 4. Generate callouts (5-10 per upgrade)
  // 5. Compute confidence score based on:
  //    - outlet credibility
  //    - photo presence
  //    - cross-source agreement
  console.log(`[annotate] Job ${job.id} completed (placeholder)`);
}
