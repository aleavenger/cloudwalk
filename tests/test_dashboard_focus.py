from __future__ import annotations

from datetime import datetime, timedelta

from app.dashboard_focus import (
    FOCUS_CLUSTER_GAP,
    FOCUS_CLUSTER_MIN_POINTS,
    build_focus_clusters,
    select_focus_cluster,
)
from app.data_loader import HistoricalRow


def _row(timestamp: datetime) -> HistoricalRow:
    return HistoricalRow(
        timestamp=timestamp,
        counts={
            "approved": 100,
            "denied": 5,
            "failed": 1,
            "reversed": 1,
            "backend_reversed": 0,
            "refunded": 0,
        },
        auth_code_counts={},
    )


def test_seeded_style_cluster_is_selected_when_it_is_latest_eligible_cluster():
    rows = [
        _row(datetime(2025, 7, 12, 13, 45) + timedelta(minutes=offset))
        for offset in range(8)
    ]
    rows.append(_row(datetime(2026, 4, 23, 12, 0)))
    cluster = select_focus_cluster(rows)
    assert cluster is not None
    assert cluster.start == datetime(2025, 7, 12, 13, 45)
    assert cluster.end == datetime(2025, 7, 12, 13, 52)
    assert cluster.eligible is True


def test_newer_cluster_takes_focus_once_it_reaches_minimum_points():
    rows = [
        _row(datetime(2025, 7, 12, 13, 45) + timedelta(minutes=offset))
        for offset in range(8)
    ]
    rows.extend(
        _row(datetime(2026, 4, 23, 12, 0) + timedelta(minutes=offset))
        for offset in range(FOCUS_CLUSTER_MIN_POINTS)
    )
    cluster = select_focus_cluster(rows)
    assert cluster is not None
    assert cluster.start == datetime(2026, 4, 23, 12, 0)
    assert cluster.end == datetime(2026, 4, 23, 12, 4)
    assert cluster.eligible is True


def test_cluster_split_occurs_after_gap_threshold():
    first = _row(datetime(2025, 7, 12, 13, 45))
    second = _row(first.timestamp + FOCUS_CLUSTER_GAP)
    third = _row(first.timestamp + FOCUS_CLUSTER_GAP + timedelta(minutes=1))
    clusters = build_focus_clusters([first, second, third])
    assert len(clusters) == 1

    split_row = _row(first.timestamp + FOCUS_CLUSTER_GAP + timedelta(minutes=2))
    clusters = build_focus_clusters([first, split_row])
    assert len(clusters) == 2
