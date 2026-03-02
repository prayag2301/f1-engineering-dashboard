export const config = {
  REDIS_HOST: process.env.REDIS_HOST ?? "localhost",
  REDIS_PORT: parseInt(process.env.REDIS_PORT ?? "6379", 10),
  REDIS_URL: process.env.REDIS_URL ?? "redis://localhost:6379/0",
  API_URL: process.env.API_URL ?? "http://localhost:8000/api/v1",
  MINIO_ENDPOINT: process.env.MINIO_ENDPOINT ?? "localhost",
  MINIO_PORT: parseInt(process.env.MINIO_PORT ?? "9000", 10),
  MINIO_ACCESS_KEY: process.env.MINIO_ACCESS_KEY ?? "f1admin",
  MINIO_SECRET_KEY: process.env.MINIO_SECRET_KEY ?? "f1adminpass",
  MINIO_BUCKET: process.env.MINIO_BUCKET ?? "f1-raw",
  DRY_RUN: process.env.DRY_RUN === "true",
} as const;
