#!/usr/bin/env python3
"""
Generate Zscaler-style CSV fixtures compatible with the current backend parser.

Usage examples:
  python scripts/generate_zscaler_fixture.py --rows 200 --anomaly-rate 0.15 > fixtures/generated.csv
  python scripts/generate_zscaler_fixture.py --rows 50 --mode high-risk > fixtures/generated_high_risk.csv
  python scripts/generate_zscaler_fixture.py --rows 50 --mode large-outbound > fixtures/generated_large_outbound.csv
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta


HEADERS = ["datetime", "clientip", "url", "action", "sentbytes", "app_risk_score"]


def gen_row(ts: datetime, mode: str, anomaly_rate: float) -> dict[str, str]:
    ip = f"10.0.{random.randint(0, 3)}.{random.randint(10, 250)}"
    action = random.choice(["Allowed", "Allowed", "Allowed", "Blocked"])
    url = random.choice(
        [
            "https://example.com/",
            "https://example.com/login",
            "https://example.com/search?q=test",
            "https://saas.example.com/app",
            "https://cdn.example.com/static/app.js",
            "https://docs.example.com/help",
            "https://files.example.com/upload",
            "https://risk.example.com/odd",
        ]
    )

    is_anom = random.random() < anomaly_rate

    # Defaults (non-anomalous)
    sentbytes = random.randint(200, 5000)
    risk = random.randint(0, 3)

    if mode == "high-risk":
        if is_anom:
            risk = random.randint(4, 7)
    elif mode == "large-outbound":
        if is_anom:
            sentbytes = random.randint(5_000_001, 12_000_000)
    else:  # mixed
        if is_anom:
            if random.random() < 0.5:
                risk = random.randint(4, 7)
            else:
                sentbytes = random.randint(5_000_001, 12_000_000)

    return {
        "datetime": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "clientip": ip,
        "url": url,
        "action": action,
        "sentbytes": str(sentbytes),
        "app_risk_score": str(risk),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, default=50)
    p.add_argument("--mode", choices=["mixed", "high-risk", "large-outbound"], default="mixed")
    p.add_argument("--anomaly-rate", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    random.seed(args.seed)

    start = datetime(2026, 2, 1, 12, 0, 0)

    print(",".join(HEADERS))
    for i in range(args.rows):
        row = gen_row(start + timedelta(seconds=i), args.mode, args.anomaly_rate)
        print(",".join(row[h] for h in HEADERS))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


