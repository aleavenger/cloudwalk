from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean
from typing import Literal

from app.config import Settings
from app.data_loader import HistoricalRow, compute_rates

Severity = Literal["none", "info", "warning", "critical"]


@dataclass(frozen=True)
class AlertEvaluation:
    severity: Severity
    recommendation: Literal["alert", "no_alert"]
    triggered_metrics: list[str]
    rates: dict[str, float]
    baseline_rates: dict[str, float]
    reason: str


SEVERITY_ORDER = {"none": 0, "info": 1, "warning": 2, "critical": 3}


class AlertEngine:
    def __init__(self, settings: Settings, historical_rows: list[HistoricalRow]) -> None:
        self.settings = settings
        self.historical_rows = historical_rows
        self.cooldown_state: dict[tuple[str, Severity], datetime] = {}
        self.global_baseline = self._compute_global_baseline()

    def _compute_global_baseline(self) -> dict[str, float]:
        if not self.historical_rows:
            return {"denied_rate": 0.0, "failed_rate": 0.0, "reversed_rate": 0.0}
        denied = []
        failed = []
        reversed_vals = []
        for row in self.historical_rows:
            rates = compute_rates(row.counts)
            denied.append(rates["denied_rate"])
            failed.append(rates["failed_rate"])
            reversed_vals.append(rates["reversed_rate"])
        return {
            "denied_rate": mean(denied),
            "failed_rate": mean(failed),
            "reversed_rate": mean(reversed_vals),
        }

    def baseline_for_timestamp(self, timestamp: datetime) -> dict[str, float]:
        prior_rates: dict[str, list[float]] = defaultdict(list)
        cutoff_start = timestamp - timedelta(minutes=self.settings.baseline_window_minutes)
        for row in self.historical_rows:
            if cutoff_start <= row.timestamp < timestamp:
                rates = compute_rates(row.counts)
                prior_rates["denied_rate"].append(rates["denied_rate"])
                prior_rates["failed_rate"].append(rates["failed_rate"])
                prior_rates["reversed_rate"].append(rates["reversed_rate"])
        if not prior_rates["denied_rate"]:
            return self.global_baseline
        return {
            "denied_rate": mean(prior_rates["denied_rate"]),
            "failed_rate": mean(prior_rates["failed_rate"]),
            "reversed_rate": mean(prior_rates["reversed_rate"]),
        }

    def _metric_floor(self, metric: str) -> float:
        if metric == "denied":
            return self.settings.floor_rate_denied
        if metric == "failed":
            return self.settings.floor_rate_failed
        return self.settings.floor_rate_reversed

    def _metric_severity(self, metric: str, count: int, total: int, current_rate: float, baseline_rate: float) -> Severity:
        if total < self.settings.minimum_total_count or count < self.settings.minimum_metric_count:
            return "none"
        floor = self._metric_floor(metric)
        critical_threshold = max(floor * 1.5, baseline_rate * self.settings.critical_multiplier)
        warning_threshold = max(floor, baseline_rate * self.settings.warning_multiplier)
        info_threshold = max(floor * 0.8, baseline_rate * 1.5)
        if current_rate >= critical_threshold:
            return "critical"
        if current_rate >= warning_threshold:
            return "warning"
        if current_rate >= info_threshold:
            return "info"
        return "none"

    def evaluate(self, timestamp: datetime, counts: dict[str, int], apply_cooldown: bool) -> AlertEvaluation:
        rates_full = compute_rates(counts)
        rates = {
            "denied_rate": rates_full["denied_rate"],
            "failed_rate": rates_full["failed_rate"],
            "reversed_rate": rates_full["reversed_rate"],
        }
        baseline_rates = self.baseline_for_timestamp(timestamp)
        total = sum(counts.values())
        metric_statuses = {}
        for metric in ("denied", "failed", "reversed"):
            metric_statuses[metric] = self._metric_severity(
                metric=metric,
                count=counts.get(metric, 0),
                total=total,
                current_rate=rates[f"{metric}_rate"],
                baseline_rate=baseline_rates[f"{metric}_rate"],
            )

        highest = "none"
        for metric in metric_statuses:
            if SEVERITY_ORDER[metric_statuses[metric]] > SEVERITY_ORDER[highest]:
                highest = metric_statuses[metric]

        triggered = [m for m, sev in metric_statuses.items() if sev in ("warning", "critical")]
        recommendation = "alert" if highest in ("warning", "critical") else "no_alert"
        reason = f"Severity {highest} from metrics: {', '.join(triggered) if triggered else 'none'}"

        if apply_cooldown and recommendation == "alert":
            filtered = []
            for metric in triggered:
                metric_sev = metric_statuses[metric]
                key = (metric, metric_sev)
                last = self.cooldown_state.get(key)
                if last is None or (timestamp - last) >= timedelta(minutes=self.settings.cooldown_minutes):
                    filtered.append(metric)
                    self.cooldown_state[key] = timestamp
            if not filtered:
                return AlertEvaluation(
                    severity="info",
                    recommendation="no_alert",
                    triggered_metrics=[],
                    rates=rates,
                    baseline_rates=baseline_rates,
                    reason="Suppressed by cooldown window",
                )
            triggered = filtered
            highest = max((metric_statuses[m] for m in triggered), key=lambda sev: SEVERITY_ORDER[sev])
            recommendation = "alert"
            reason = f"Alert triggered for: {', '.join(triggered)}"

        return AlertEvaluation(
            severity=highest,
            recommendation=recommendation,
            triggered_metrics=triggered,
            rates=rates,
            baseline_rates=baseline_rates,
            reason=reason,
        )

