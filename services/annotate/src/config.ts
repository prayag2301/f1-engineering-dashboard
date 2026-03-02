export const config = {
  REDIS_HOST: process.env.REDIS_HOST ?? "localhost",
  REDIS_PORT: parseInt(process.env.REDIS_PORT ?? "6379", 10),
  REDIS_URL: process.env.REDIS_URL ?? "redis://localhost:6379/0",
  API_URL: process.env.API_URL ?? "http://localhost:8000/api/v1",
  LLM_API_KEY: process.env.LLM_API_KEY ?? "",
  LLM_MODEL: process.env.LLM_MODEL ?? "claude-sonnet-4-6",
  DRY_RUN: process.env.DRY_RUN === "true",
} as const;
