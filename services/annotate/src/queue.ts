import { Queue } from "bullmq";
import { config } from "./config.js";

export const annotateQueue = new Queue("annotate", {
  connection: { host: config.REDIS_HOST, port: config.REDIS_PORT },
});
