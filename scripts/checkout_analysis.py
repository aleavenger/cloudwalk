from __future__ import annotations

import csv
from pathlib import Path


def analyze_checkout(input_path: Path, output_path: Path) -> None:
    rows = []
    with input_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            today = float(row["today"])
            baseline = (
                float(row["same_day_last_week"])
                + float(row["avg_last_week"])
                + float(row["avg_last_month"])
            ) / 3.0
            absolute_deviation = today - baseline
            relative_deviation = absolute_deviation / baseline if baseline else 0.0
            rows.append(
                {
                    **row,
                    "baseline": round(baseline, 4),
                    "absolute_deviation": round(absolute_deviation, 4),
                    "relative_deviation": round(relative_deviation, 4),
                }
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    analyze_checkout(Path("database/checkout_1.csv"), Path("database/report/checkout_1_anomaly.csv"))
    analyze_checkout(Path("database/checkout_2.csv"), Path("database/report/checkout_2_anomaly.csv"))
