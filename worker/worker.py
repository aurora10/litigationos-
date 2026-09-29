"""LitigationOS ingestion worker (D01 placeholder).

D05 implements the real OCR pipeline here; for D01 the worker only
consumes the 'ingestion' queue to prove the queue wiring works.
"""
import os

import redis

QUEUE = "ingestion"


def main() -> None:
    client = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
    client.ping()
    print("worker: connected to redis, waiting for jobs on", QUEUE, flush=True)
    while True:
        item = client.blpop(QUEUE, timeout=30)
        if item:
            print("worker: received job", item[1][:80], flush=True)  # real OCR in D05


if __name__ == "__main__":
    main()
