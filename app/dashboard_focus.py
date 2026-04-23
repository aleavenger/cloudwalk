from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Literal

from app.anomaly import AlertEngine
from app.data_loader import HistoricalRow, compute_rates
from app.models import MetricsRow


DashboardBucket = Literal["hour", "minute"]
FOCUS_CLUSTER_GAP = timedelta(minutes=90)
FOCUS_CLUSTER_MIN_POINTS = 5


@dataclass(frozen=True)
class FocusCluster:
    rows: tuple[HistoricalRow, ...]
    start: datetime
    end: datetime
    point_count: int
    eligible: bool


def build_focus_clusters(rows: list[HistoricalRow]) -> list[FocusCluster]:
    if not rows:
        return []

    sorted_rows = sorted(rows, key=lambda row: row.timestamp)
    clusters: list[list[HistoricalRow]] = []
    current_cluster: list[HistoricalRow] = [sorted_rows[0]]

    for row in sorted_rows[1:]:
        if row.timestamp - current_cluster[-1].timestamp > FOCUS_CLUSTER_GAP:
            clusters.append(current_cluster)
            current_cluster = [row]
            continue
        current_cluster.append(row)
    clusters.append(current_cluster)

    return [
        FocusCluster(
            rows=tuple(cluster_rows),
            start=cluster_rows[0].timestamp,
            end=cluster_rows[-1].timestamp,
            point_count=len(cluster_rows),
            eligible=len(cluster_rows) >= FOCUS_CLUSTER_MIN_POINTS,
        )
        for cluster_rows in clusters
    ]


def select_focus_cluster(rows: list[HistoricalRow]) -> FocusCluster | None:
    clusters = build_focus_clusters(rows)
    if not clusters:
        return None

    eligible_clusters = [cluster for cluster in clusters if cluster.eligible]
    if eligible_clusters:
        return eligible_clusters[-1]
    return clusters[-1]


def cluster_rows_for_bucket(cluster: FocusCluster, bucket: DashboardBucket) -> list[HistoricalRow]:
    if bucket == "minute":
        return list(cluster.rows)

    hourly_counts: dict[datetime, dict[str, int]] = defaultdict(
        lambda: {
            "approved": 0,
            "denied": 0,
            "failed": 0,
            "reversed": 0,
            "backend_reversed": 0,
            "refunded": 0,
        }
    )
    hourly_auth_codes: dict[datetime, dict[str, int]] = defaultdict(dict)

    for row in cluster.rows:
        hour_bucket = row.timestamp.replace(minute=0, second=0, microsecond=0)
        for key, value in row.counts.items():
            hourly_counts[hour_bucket][key] = hourly_counts[hour_bucket].get(key, 0) + value
        for auth_code, value in row.auth_code_counts.items():
            existing_value = hourly_auth_codes[hour_bucket].get(auth_code, 0)
            hourly_auth_codes[hour_bucket][auth_code] = existing_value + value

    return [
        HistoricalRow(
            timestamp=timestamp,
            counts=hourly_counts[timestamp],
            auth_code_counts=hourly_auth_codes[timestamp],
        )
        for timestamp in sorted(hourly_counts)
    ]


def build_metrics_rows(rows: list[HistoricalRow], engine: AlertEngine) -> list[MetricsRow]:
    metrics_rows: list[MetricsRow] = []
    for row in rows:
        evaluation = engine.evaluate(timestamp=row.timestamp, counts=row.counts, apply_cooldown=False)
        rates = compute_rates(row.counts)
        metrics_rows.append(
            MetricsRow(
                timestamp=row.timestamp,
                total=sum(row.counts.values()),
                approved_rate=round(rates["approved_rate"], 6),
                denied_rate=round(rates["denied_rate"], 6),
                failed_rate=round(rates["failed_rate"], 6),
                reversed_rate=round(rates["reversed_rate"], 6),
                alert_severity=evaluation.severity,
            )
        )
    return metrics_rows


def focus_metrics_rows(rows: list[HistoricalRow], engine: AlertEngine, bucket: DashboardBucket) -> list[MetricsRow]:
    cluster = select_focus_cluster(rows)
    if cluster is None:
        return []
    return build_metrics_rows(cluster_rows_for_bucket(cluster, bucket), engine)


def filter_cluster_alerts(items: list[Any], cluster: FocusCluster) -> list[Any]:
    return [item for item in items if cluster.start <= item.timestamp <= cluster.end]


def focus_dashboard_time_range(
    cluster: FocusCluster,
    *,
    decision_min_history_points: int,
    decision_forecast_horizon_minutes: int,
) -> tuple[datetime, datetime]:
    time_to = cluster.end
    if cluster.point_count >= decision_min_history_points:
        time_to = max(time_to, cluster.end + timedelta(minutes=decision_forecast_horizon_minutes))
    return cluster.start, time_to


def render_dashboard(
    *,
    root_dir: Path,
    cluster: FocusCluster,
    decision_min_history_points: int,
    decision_forecast_horizon_minutes: int,
) -> str:
    template_path = root_dir / "grafana" / "dashboard.template.json"
    output_path = root_dir / "grafana" / "dashboard.json"
    dashboard = json.loads(template_path.read_text(encoding="utf-8"))
    time_from, time_to = focus_dashboard_time_range(
        cluster,
        decision_min_history_points=decision_min_history_points,
        decision_forecast_horizon_minutes=decision_forecast_horizon_minutes,
    )
    dashboard["time"] = {
        "from": _isoformat_z(time_from),
        "to": _isoformat_z(time_to),
    }

    rendered = json.dumps(dashboard, indent=2) + "\n"
    rendered_hash = sha256(rendered.encode("utf-8")).hexdigest()
    if output_path.exists() and output_path.read_text(encoding="utf-8") == rendered:
        os.chmod(output_path, 0o644)
        return rendered_hash

    output_path.write_text(rendered, encoding="utf-8")
    os.chmod(output_path, 0o644)
    return rendered_hash


def _isoformat_z(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
