from __future__ import annotations

import csv
from pathlib import Path


def _derive_direction(
    absolute_deviation: float,
    relative_deviation: float,
    *,
    is_material: bool,
) -> str:
    if not is_material:
        return "normal"
    if absolute_deviation >= 8 and relative_deviation >= 0.5:
        return "surge"
    if absolute_deviation <= -8 and relative_deviation <= -0.5:
        return "drop"
    return "normal"


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
            is_material = baseline >= 5.0
            direction = _derive_direction(
                absolute_deviation,
                relative_deviation,
                is_material=is_material,
            )
            zero_gap = is_material and today == 0.0
            severity_score = abs(absolute_deviation) if is_material else 0.0
            rows.append(
                {
                    **row,
                    "baseline": round(baseline, 4),
                    "absolute_deviation": round(absolute_deviation, 4),
                    "relative_deviation": round(relative_deviation, 4),
                    "is_material": str(is_material).lower(),
                    "direction": direction,
                    "zero_gap": str(zero_gap).lower(),
                    "severity_score": round(severity_score, 4),
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
