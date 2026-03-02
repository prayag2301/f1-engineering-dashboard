import { Queue } from "bullmq";
import { config } from "./config.js";

export const ingestQueue = new Queue("ingest", {
  connection: { host: config.REDIS_HOST, port: config.REDIS_PORT },
});
