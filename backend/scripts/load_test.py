"""Load test for the /agents/{id}/execute endpoint.

Usage:
    python3 scripts/load_test.py --base-url http://localhost:8000 \
        --token "Bearer ..." --agent-id <uuid> \
        --concurrency 50 --duration 60

Validates:
  - Rate limiter rejects with 429 once the limit is crossed
  - p95 latency stays below the configured budget
  - No 5xx errors under sustained load
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from collections import Counter
from dataclasses import dataclass, field

import httpx


@dataclass
class Result:
    statuses: Counter = field(default_factory=Counter)
    latencies_ms: list[float] = field(default_factory=list)
    errors: int = 0


async def _worker(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    payload: dict,
    deadline: float,
    out: Result,
) -> None:
    while time.monotonic() < deadline:
        start = time.monotonic()
        try:
            resp = await client.post(url, headers=headers, json=payload, timeout=30.0)
            elapsed = (time.monotonic() - start) * 1000
            out.statuses[resp.status_code] += 1
            out.latencies_ms.append(elapsed)
        except Exception:
            out.errors += 1


async def run(args: argparse.Namespace) -> Result:
    url = f"{args.base_url.rstrip('/')}/api/v1/agents/{args.agent_id}/execute"
    headers = {"Authorization": args.token, "Content-Type": "application/json"}
    payload = {"input": args.input}
    out = Result()
    deadline = time.monotonic() + args.duration

    async with httpx.AsyncClient() as client:
        await asyncio.gather(
            *(
                _worker(client, url, headers, payload, deadline, out)
                for _ in range(args.concurrency)
            )
        )
    return out


def _report(out: Result, args: argparse.Namespace) -> int:
    total = sum(out.statuses.values())
    print(f"\nTotal requests: {total}")
    print(f"Errors (network): {out.errors}")
    print("Status breakdown:")
    for code, n in sorted(out.statuses.items()):
        print(f"  {code}: {n} ({n / total * 100:.1f}%)")

    if out.latencies_ms:
        sorted_l = sorted(out.latencies_ms)
        p50 = statistics.median(sorted_l)
        p95 = sorted_l[int(len(sorted_l) * 0.95)]
        p99 = sorted_l[int(len(sorted_l) * 0.99)]
        print(f"Latency p50/p95/p99 ms: {p50:.0f} / {p95:.0f} / {p99:.0f}")

    rate_429 = out.statuses.get(429, 0)
    rate_5xx = sum(c for code, c in out.statuses.items() if 500 <= code < 600)

    failed = False
    if rate_5xx > 0:
        print(f"❌ FAIL: {rate_5xx} 5xx responses under load")
        failed = True
    if args.expect_rate_limit and rate_429 == 0:
        print("❌ FAIL: expected rate limiter to fire (no 429s seen)")
        failed = True
    if out.latencies_ms and sorted(out.latencies_ms)[
        int(len(out.latencies_ms) * 0.95)
    ] > args.p95_budget_ms:
        print(f"❌ FAIL: p95 above budget ({args.p95_budget_ms}ms)")
        failed = True

    if not failed:
        print("✅ PASS")
    return 1 if failed else 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--token", required=True, help="e.g. 'Bearer eyJ...'")
    p.add_argument("--agent-id", required=True)
    p.add_argument("--input", default="ping")
    p.add_argument("--concurrency", type=int, default=20)
    p.add_argument("--duration", type=int, default=30, help="seconds")
    p.add_argument("--p95-budget-ms", type=float, default=2000.0)
    p.add_argument("--expect-rate-limit", action="store_true")
    args = p.parse_args()

    out = asyncio.run(run(args))
    return _report(out, args)


if __name__ == "__main__":
    raise SystemExit(main())
