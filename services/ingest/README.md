# Service: Ingest

TypeScript worker that accepts URLs/files, stores raw media and articles, and writes evidence rows.

## Queue

Consumes from: `ingest` (Redis/BullMQ)

## Responsibilities

- Accept local folders and URLs
- Store raw media/articles in MinIO (S3-compatible)
- Write evidence rows with source, license, and credibility score
