"""Recon service worker — consumes jobs from Redis queue."""

import argparse
import json
import logging
import sys
import time

import redis

from recon.config import config
from recon.pipeline import assess_trainability, run_reconstruction

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [recon] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

QUEUE_NAME = "recon"


def process_job(job_data: dict) -> dict:
    """Process a single reconstruction job."""
    image_dir = job_data.get("image_dir", "")
    output_dir = job_data.get("output_dir", "")
    method = job_data.get("method", "splatfacto")

    logger.info(f"Processing recon job: {image_dir} -> {output_dir}")

    if config.DRY_RUN:
        logger.info(f"DRY RUN: would reconstruct {image_dir} with {method}")
        return {"status": "dry_run"}

    # Assess trainability first
    trainability = assess_trainability([])  # TODO: list actual images
    logger.info(f"Trainability score: {trainability['score']}")

    if trainability["score"] < 0.3:
        logger.warning("Low trainability score, reconstruction may fail")

    result = run_reconstruction(image_dir, output_dir, method)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="F1 Recon Service - GPU worker for 3D reconstruction"
    )
    parser.add_argument("--dry-run", action="store_true", help="Run without side effects")
    parser.add_argument("--once", action="store_true", help="Process one job and exit")
    args = parser.parse_args()

    if args.dry_run:
        config.DRY_RUN = True
        logger.info("Running in dry-run mode")

    logger.info("Recon worker started, connecting to Redis...")

    try:
        r = redis.from_url(config.REDIS_URL)
        r.ping()
        logger.info("Connected to Redis")
    except redis.ConnectionError:
        logger.error(f"Cannot connect to Redis at {config.REDIS_URL}")
        sys.exit(1)

    logger.info(f"Listening on queue: {QUEUE_NAME}")

    while True:
        # BRPOP blocks until a job is available
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
