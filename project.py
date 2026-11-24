"""Measure end-to-end acknowledged delivery against a local Event Relay instance."""

import argparse
import json
import math
import platform
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4


def percentile(values, p):
    return sorted(values)[math.ceil(len(values) * p) - 1] if values else None


def summarize(rows, seconds):
    delivered = [row for row in rows if row["state"] == "delivered"]
    times = [row["elapsed_ms"] for row in delivered]
    return {
        "submitted": len(rows),
        "delivered": len(delivered),
        "other": len(rows) - len(delivered),
        "wall_seconds": round(seconds, 3),
        "deliveries_per_second": round(len(delivered) / seconds, 2),
        "p50_observed_ms": round(statistics.median(times), 2) if times else None,
        "p95_observed_ms": round(percentile(times, 0.95), 2) if times else None,
        "repeated_attempts": sum(max(0, row["attempts"] - 1) for row in rows),
    }


def request_json(target, body=None, key=None):
    request = Request(target)
    if body is not None:
        request = Request(
            target,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Idempotency-Key": key},
        )
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def benchmark(base, *, count, concurrency, poll_seconds, injected_every):
    url = urlsplit(base)
    if (
        url.scheme != "http"
        or url.hostname not in ("127.0.0.1", "localhost")
        or url.path not in ("", "/")
        or url.query
    ):
        raise ValueError("Use the local Event Relay origin")
    if (
        not 1 <= count <= 5000
        or not 1 <= concurrency <= 32
        or not 0.01 <= poll_seconds <= 5
        or injected_every < 0
    ):
        raise ValueError("Workload is outside the supported local bounds")
    path = base.rstrip("/") + "/orders"
    key = uuid4().hex

    def observe(index):
        begin = time.monotonic()
        scenario = "ack_failed_once" if injected_every and index % injected_every == 0 else "normal"
        order = request_json(
            path, {"reference": f"bench-{index}", "scenario": scenario}, f"{key}-{index}"
        )
        while order["state"] not in ("delivered", "exhausted") and time.monotonic() - begin < 25:
            time.sleep(poll_seconds)
            order = request_json(f"{path}/{order['event_id']}")
        return {
            **order,
            "scenario": scenario,
            "elapsed_ms": round((time.monotonic() - begin) * 1000, 2),
        }

    begin = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        rows = list(pool.map(observe, range(1, count + 1)))
    return {
        "workload": {
            "count": count,
            "client_concurrency": concurrency,
            "poll_seconds": poll_seconds,
            "fail_ack_every": injected_every,
        },
        "host": {
            "platform": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "results": summarize(rows, time.monotonic() - begin),
        "events": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", required=True)
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--poll-ms", type=int, default=60)
    parser.add_argument("--fail-ack-every", type=int, default=0)
    args = parser.parse_args()
    print(
        json.dumps(
            benchmark(
                args.api,
                count=args.count,
                concurrency=args.concurrency,
                poll_seconds=args.poll_ms / 1000,
                injected_every=args.fail_ack_every,
            ),
            indent=2,
        )
    )
