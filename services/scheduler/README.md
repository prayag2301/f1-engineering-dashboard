# Service: Scheduler

TypeScript cron-like dispatcher that enqueues jobs across the pipeline.

## Queue

Produces to: `ingest`, `annotate`, `recon`, `meshops`

## Responsibilities

- Monitor for new race weekends / manual triggers
- Dispatch pipeline stages in order: ingest -> annotate -> recon -> meshops -> publish
- Track job status and handle retries
