import { Queue } from "bullmq";
import { config } from "./config.js";

export const queues = {
  ingest: new Queue("ingest", {
    connection: { host: config.REDIS_HOST, port: config.REDIS_PORT },
  }),
  annotate: new Queue("annotate", {
    connection: { host: config.REDIS_HOST, port: config.REDIS_PORT },
  }),
  recon: new Queue("recon", {
    connection: { host: config.REDIS_HOST, port: config.REDIS_PORT },
  }),
  meshops: new Queue("meshops", {
    connection: { host: config.REDIS_HOST, port: config.REDIS_PORT },
  }),
};
