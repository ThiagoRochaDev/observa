from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import time
import urllib.error
import urllib.request


def request_once(url: str, headers: dict[str, str], timeout: float) -> tuple[int, float]:
    started = time.perf_counter()
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except OSError:
        status = 0
    return status, (time.perf_counter() - started) * 1000


def percentile(values: list[float], percent: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percent)))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="Small dependency-free Observa load test")
    parser.add_argument("--url", default="http://127.0.0.1:8080/api/health")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--company-id")
    parser.add_argument("--tenancy-id")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--max-p95-ms", type=float, default=1000)
    args = parser.parse_args()

    headers = {"X-Observa-Api-Key": args.api_key}
    if args.company_id:
        headers["X-Observa-Company-ID"] = args.company_id
    if args.tenancy_id:
        headers["X-Observa-Tenancy-ID"] = args.tenancy_id

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(
            executor.map(
                lambda _: request_once(args.url, headers, args.timeout),
                range(args.requests),
            )
        )

    latencies = [latency for _, latency in results]
    failures = sum(1 for status, _ in results if status < 200 or status >= 400)
    report = {
        "requests": len(results),
        "concurrency": args.concurrency,
        "failures": failures,
        "error_rate": failures / len(results),
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2),
            "p50": round(percentile(latencies, 0.50), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "max": round(max(latencies), 2),
        },
    }
    print(json.dumps(report, indent=2))
    if report["error_rate"] > args.max_error_rate or report["latency_ms"]["p95"] > args.max_p95_ms:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
