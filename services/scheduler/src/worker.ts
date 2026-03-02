import { config } from "./config.js";
import { queues } from "./queue.js";

export interface PipelineRequest {
  season: number;
  race: string;
  team_id?: string;
  stages?: ("ingest" | "annotate" | "recon" | "meshops")[];
}

const DEFAULT_STAGES = ["ingest", "annotate", "recon", "meshops"] as const;

export async function dispatchPipeline(request: PipelineRequest): Promise<void> {
  const stages = request.stages ?? [...DEFAULT_STAGES];

  console.log(`[scheduler] Dispatching pipeline for ${request.season} ${request.race}`, {
    stages,
    team_id: request.team_id ?? "all",
  });

  if (config.DRY_RUN) {
    console.log(`[scheduler] DRY RUN: would dispatch ${stages.join(" -> ")}`);
    return;
  }

  // Pipeline stages are dispatched sequentially via job dependencies
  // Each stage completion triggers the next
  for (const stage of stages) {
    const queue = queues[stage];
    await queue.add(`${request.season}-${request.race}`, {
      season: request.season,
      race: request.race,
      team_id: request.team_id,
    });
    console.log(`[scheduler] Enqueued ${stage} job`);
  }
}
