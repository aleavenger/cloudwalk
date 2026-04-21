from __future__ import annotations

import csv
from pathlib import Path

def _read_rows(input_path: Path) -> list[dict[str, str]]:
    with input_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _line_points(values: list[float], width: int, height: int, padding: int, max_value: float) -> str:
    if not values:
        return ""
    step_x = (width - 2 * padding) / max(1, len(values) - 1)
    points = []
    for idx, value in enumerate(values):
        x = padding + idx * step_x
        y = height - padding - (value / max_value) * (height - 2 * padding) if max_value else height - padding
        points.append(f"{x:.2f},{y:.2f}")
    return " ".join(points)


def generate_chart(input_path: Path, output_path: Path, title: str) -> None:
    rows = _read_rows(input_path)
    hours = [r["time"] for r in rows]
    series = {
        "Today": [float(r["today"]) for r in rows],
        "Yesterday": [float(r["yesterday"]) for r in rows],
        "Avg Last Week": [float(r["avg_last_week"]) for r in rows],
        "Avg Last Month": [float(r["avg_last_month"]) for r in rows],
    }
    colors = {
        "Today": "#1f77b4",
        "Yesterday": "#2ca02c",
        "Avg Last Week": "#ff7f0e",
        "Avg Last Month": "#d62728",
    }
    width, height, padding = 1100, 520, 60
    max_value = max((max(values) for values in series.values()), default=1.0)
    poly = []
    legends = []
    for idx, (name, values) in enumerate(series.items()):
        points = _line_points(values, width, height, padding, max_value)
        poly.append(
            f'<polyline fill="none" stroke="{colors[name]}" stroke-width="2.5" points="{points}" />'
        )
        legends.append(
            f'<text x="{padding + idx * 240}" y="30" fill="{colors[name]}" font-size="14">{name}</text>'
        )

    labels = []
    step_x = (width - 2 * padding) / max(1, len(hours) - 1)
    for idx, hour in enumerate(hours):
        x = padding + idx * step_x
        labels.append(
            f'<text x="{x:.2f}" y="{height - 20}" font-size="10" text-anchor="middle">{hour}</text>'
        )

    grid = []
    for i in range(6):
        y = padding + i * (height - 2 * padding) / 5
        value = max_value * (1 - i / 5)
        grid.append(f'<line x1="{padding}" y1="{y:.2f}" x2="{width-padding}" y2="{y:.2f}" stroke="#e8e8e8" />')
        grid.append(f'<text x="10" y="{y + 4:.2f}" font-size="11">{value:.1f}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
<rect width="100%" height="100%" fill="white"/>
<text x="{padding}" y="18" font-size="18" font-family="Arial">{title}</text>
{''.join(legends)}
{''.join(grid)}
<line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}" stroke="#555"/>
<line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height-padding}" stroke="#555"/>
{''.join(poly)}
{''.join(labels)}
</svg>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    generate_chart(Path("database/checkout_1.csv"), Path("charts/checkout_1.svg"), "Checkout 1 - Hourly Comparison")
    generate_chart(Path("database/checkout_2.csv"), Path("charts/checkout_2.svg"), "Checkout 2 - Hourly Comparison")
