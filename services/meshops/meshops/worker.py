"""MeshOps service worker — consumes jobs from Redis queue."""

import argparse
import json
import logging
import sys

import redis

from meshops.config import config
from meshops.processor import align_meshes, compute_delta, generate_placeholder_glb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [meshops] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

QUEUE_NAME = "meshops"


def process_job(job_data: dict) -> dict:
    """Process a single meshops job."""
    job_type = job_data.get("type", "placeholder")

    logger.info(f"Processing meshops job: {job_type}")

    if config.DRY_RUN:
        logger.info(f"DRY RUN: would process {job_type}")
        return {"status": "dry_run"}

    if job_type == "align":
        return align_meshes(
            job_data.get("mesh_a", ""),
            job_data.get("mesh_b", ""),
        )
    elif job_type == "delta":
        return compute_delta(
            job_data.get("mesh_a", ""),
            job_data.get("mesh_b", ""),
        )
    elif job_type == "placeholder":
        path = generate_placeholder_glb(job_data.get("output_path", "/tmp/placeholder.glb"))
        return {"glb_path": path, "status": "placeholder"}
    else:
        logger.warning(f"Unknown job type: {job_type}")
        return {"status": "unknown_type"}


def main():
    parser = argparse.ArgumentParser(
        description="F1 MeshOps Service - mesh alignment and delta computation"
    )
    parser.add_argument("--dry-run", action="store_true", help="Run without side effects")
    parser.add_argument("--once", action="store_true", help="Process one job and exit")
    args = parser.parse_args()

    if args.dry_run:
        config.DRY_RUN = True
        logger.info("Running in dry-run mode")

    logger.info("MeshOps worker started, connecting to Redis...")

    try:
        r = redis.from_url(config.REDIS_URL)
        r.ping()
        logger.info("Connected to Redis")
    except redis.ConnectionError:
        logger.error(f"Cannot connect to Redis at {config.REDIS_URL}")
        sys.exit(1)

    logger.info(f"Listening on queue: {QUEUE_NAME}")

    while True:
        result = r.brpop(QUEUE_NAME, timeout=5)
        if result is None:
            continue

        _, raw = result
        try:
            job_data = json.loads(raw)
            output = process_job(job_data)
            logger.info(f"Job completed: {output}")
        except Exception as e:
            logger.error(f"Job failed: {e}")

        if args.once:
            break


if __name__ == "__main__":
    main()
