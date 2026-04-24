from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from urllib.parse import urlparse
from statistics import mean

import httpx

from app.anomaly import AlertEngine, SEVERITY_ORDER
from app.config import ExternalAIProvider, Settings
from app.models import (
    AlertRecord,
    DecisionBusinessImpact,
    DecisionEvidence,
    DecisionForecastPoint,
    DecisionPriorityItem,
    DecisionProviderStatus,
    DecisionResponse,
    ForecastChartPoint,
    ForecastChartResponse,
    MetricName,
    MetricsRow,
)


@dataclass(frozen=True)
class _ExternalNarrative:
    summary: str
    top_recommendation: str
    problem_explanation: str
    forecast_explanation: str


class DecisionEngine:
    def __init__(self, settings: Settings, alert_engine: AlertEngine) -> None:
        self.settings = settings
        self.alert_engine = alert_engine

    async def build_response(
        self,
        *,
        metrics_rows: list[MetricsRow],
        alert_history: list[AlertRecord],
        auth_codes_by_timestamp: dict[datetime, dict[str, int]],
        allow_external_narrative: bool = True,
    ) -> DecisionResponse:
        if not metrics_rows:
            provider_status = DecisionProviderStatus(mode=self.settings.decision_engine_mode, fallback_active=False)
            return DecisionResponse(
                generated_at=datetime.now(UTC).replace(tzinfo=None),
                overall_status="normal",
                top_recommendation="No monitoring data is available yet.",
                summary="The decision engine has no metrics rows to analyze.",
                problem_explanation="No current anomaly can be described because there are no monitoring rows yet.",
                forecast_explanation="Forecast guidance is unavailable until the service accumulates recent monitoring rows.",
                business_impact=None,
                priority_items=[],
                forecast_points=[],
                recent_evidence=[],
                provider_status=provider_status,
            )

        latest_row = max(metrics_rows, key=lambda row: row.timestamp)
        latest_ts = latest_row.timestamp
        baseline_rates = self.alert_engine.baseline_for_timestamp(latest_ts)
        recent_rows = self._recent_rows(metrics_rows, latest_ts)
        priority_items: list[DecisionPriorityItem] = []
        forecast_points: list[DecisionForecastPoint] = []

        for metric in ("denied", "failed", "reversed"):
            series = self._metric_series(recent_rows, metric)
            current_rate = getattr(latest_row, f"{metric}_rate")
            baseline_rate = baseline_rates[f"{metric}_rate"]
            current_severity = self._metric_severity(metric, current_rate, latest_row.total, baseline_rate)
            metric_forecast_points = self._forecast_points(metric, latest_ts, series)
            forecast_points.extend(metric_forecast_points)
            forecast_rate = max((point.forecast_rate for point in metric_forecast_points), default=None)
            forecast_severity = None
            if forecast_rate is not None:
                forecast_severity = self._metric_severity(metric, forecast_rate, latest_row.total, baseline_rate)

            decision_status = self._decision_status(current_severity, forecast_severity)
            risk_score = self._risk_score(metric, current_rate, baseline_rate, current_severity, forecast_severity)
            confidence = self._confidence(latest_row.total, len(series))
            auth_codes = self._auth_code_top(auth_codes_by_timestamp.get(latest_ts, {}))
            domain_label, likely_owner = self._business_context(metric)
            recommended_action, root_cause_hint = self._guidance_for_metric(metric, decision_status, auth_codes)
            above_normal_rate = max(0.0, current_rate - baseline_rate)
            forecast_above_normal_rate = (
                max(0.0, forecast_rate - baseline_rate) if forecast_rate is not None else None
            )
            warning_threshold = self._warning_threshold(metric, baseline_rate)
            warning_gap_rate = max(0.0, warning_threshold - current_rate)
            excess_transactions_now = int(round(above_normal_rate * latest_row.total))
            projected_excess_transactions_horizon = (
                int(round(forecast_above_normal_rate * latest_row.total))
                if forecast_above_normal_rate is not None
                else None
            )

            priority_items.append(
                DecisionPriorityItem(
                    metric=metric,
                    decision_status=decision_status,
                    current_severity=current_severity,
                    forecast_severity=forecast_severity,
                    risk_score=risk_score,
                    confidence=confidence,
                    current_rate=round(current_rate, 6),
                    baseline_rate=round(baseline_rate, 6),
                    forecast_rate=round(forecast_rate, 6) if forecast_rate is not None else None,
                    above_normal_rate=round(above_normal_rate, 6),
                    forecast_above_normal_rate=round(forecast_above_normal_rate, 6) if forecast_above_normal_rate is not None else None,
                    excess_transactions_now=excess_transactions_now,
                    projected_excess_transactions_horizon=projected_excess_transactions_horizon,
                    warning_gap_rate=round(warning_gap_rate, 6),
                    domain_label=domain_label,
                    likely_owner=likely_owner,
                    recommended_action=recommended_action,
                    root_cause_hint=root_cause_hint,
                    top_auth_codes=auth_codes,
                )
            )

        priority_items.sort(
            key=lambda item: (
                SEVERITY_ORDER[item.current_severity],
                item.risk_score,
                SEVERITY_ORDER.get(item.forecast_severity or "none", 0),
            ),
            reverse=True,
        )
        overall_status = self._overall_status(priority_items)
        top_recommendation = self._top_recommendation(priority_items, overall_status)
        summary = self._summary(priority_items, overall_status)
        problem_explanation = self._problem_explanation(priority_items, overall_status)
        forecast_explanation = self._forecast_explanation(priority_items)
        business_impact = self._business_impact(priority_items)
        recent_evidence = self._recent_evidence(latest_row, baseline_rates, priority_items, alert_history)
        provider_status = DecisionProviderStatus(mode=self.settings.decision_engine_mode, fallback_active=False)

        if allow_external_narrative and self.settings.decision_engine_mode == "external":
            narrative, provider_status = await self._external_narrative(
                overall_status=overall_status,
                summary=summary,
                top_recommendation=top_recommendation,
                problem_explanation=problem_explanation,
                forecast_explanation=forecast_explanation,
                priority_items=priority_items,
            )
            if narrative is not None:
                summary = narrative.summary
                top_recommendation = narrative.top_recommendation
                problem_explanation = narrative.problem_explanation
                forecast_explanation = narrative.forecast_explanation
        forecast_explanation = self._append_forecast_history_warning(forecast_explanation)

        return DecisionResponse(
            generated_at=datetime.now(UTC).replace(tzinfo=None),
            overall_status=overall_status,
            top_recommendation=top_recommendation,
            summary=summary,
            problem_explanation=problem_explanation,
            forecast_explanation=forecast_explanation,
            business_impact=business_impact,
            priority_items=priority_items,
            forecast_points=forecast_points,
            recent_evidence=recent_evidence,
            provider_status=provider_status,
        )

    def build_forecast_chart(
        self,
        *,
        anchor_timestamp: datetime,
        forecast_points: list[DecisionForecastPoint],
    ) -> ForecastChartResponse:
        if not forecast_points:
            return ForecastChartResponse(points=[])

        points_by_minutes: dict[int, ForecastChartPoint] = {}
        for point in sorted(forecast_points, key=lambda item: (item.timestamp, item.metric)):
            minutes_ahead = max(0, int(round((point.timestamp - anchor_timestamp).total_seconds() / 60.0)))
            chart_point = points_by_minutes.setdefault(
                minutes_ahead,
                ForecastChartPoint(
                    anchor_timestamp=anchor_timestamp,
                    minutes_ahead=minutes_ahead,
                    horizon_label=f"+{minutes_ahead}m",
                    denied_rate=None,
                    failed_rate=None,
                    reversed_rate=None,
                    max_rate=0.0,
                ),
            )
            setattr(chart_point, f"{point.metric}_rate", point.forecast_rate)
            chart_point.max_rate = max(
                rate
                for rate in (chart_point.denied_rate, chart_point.failed_rate, chart_point.reversed_rate)
                if rate is not None
            )

        ordered_points = [points_by_minutes[key] for key in sorted(points_by_minutes)]
        return ForecastChartResponse(points=ordered_points)

    def _recent_rows(self, metrics_rows: list[MetricsRow], latest_ts: datetime) -> list[MetricsRow]:
        lookback_start = latest_ts - timedelta(minutes=self.settings.decision_lookback_minutes)
        return [row for row in metrics_rows if lookback_start <= row.timestamp <= latest_ts]

    def _metric_series(self, recent_rows: list[MetricsRow], metric: MetricName) -> list[tuple[datetime, float]]:
        return [(row.timestamp, getattr(row, f"{metric}_rate")) for row in recent_rows]

    def _metric_severity(self, metric: MetricName, rate: float, total: int, baseline_rate: float) -> str:
        approx_count = int(round(rate * total))
        return self.alert_engine._metric_severity(
            metric=metric,
            count=approx_count,
            total=total,
            current_rate=rate,
            baseline_rate=baseline_rate,
        )

    def _forecast_points(
        self,
        metric: MetricName,
        latest_ts: datetime,
        series: list[tuple[datetime, float]],
    ) -> list[DecisionForecastPoint]:
        if len(series) < self.settings.decision_min_history_points:
            return []

        weights = list(range(1, len(series) + 1))
        weighted_average = sum(rate * weight for (_, rate), weight in zip(series, weights)) / sum(weights)

        slopes_per_minute: list[float] = []
        for idx in range(1, len(series)):
            prev_ts, prev_rate = series[idx - 1]
            curr_ts, curr_rate = series[idx]
            delta_minutes = max(1.0, (curr_ts - prev_ts).total_seconds() / 60.0)
            slopes_per_minute.append((curr_rate - prev_rate) / delta_minutes)
        slope_per_minute = mean(slopes_per_minute) if slopes_per_minute else 0.0

        points: list[DecisionForecastPoint] = []
        step_minutes = self.settings.decision_forecast_step_minutes
        steps = max(1, self.settings.decision_forecast_horizon_minutes // step_minutes)
        for step_index in range(1, steps + 1):
            offset_minutes = step_index * step_minutes
            forecast_rate = max(0.0, min(1.0, weighted_average + (slope_per_minute * offset_minutes)))
            points.append(
                DecisionForecastPoint(
                    timestamp=latest_ts + timedelta(minutes=offset_minutes),
                    metric=metric,
                    forecast_rate=round(forecast_rate, 6),
                )
            )
        return points

    def _decision_status(self, current_severity: str, forecast_severity: str | None) -> str:
        if current_severity in ("warning", "critical"):
            return "act_now"
        if current_severity == "info" or forecast_severity in ("info", "warning", "critical"):
            return "watch"
        return "normal"

    def _risk_score(
        self,
        metric: MetricName,
        current_rate: float,
        baseline_rate: float,
        current_severity: str,
        forecast_severity: str | None,
    ) -> int:
        severity_base = {"none": 0, "info": 25, "warning": 70, "critical": 90}[current_severity]
        forecast_bonus = 0
        if current_severity not in ("warning", "critical") and forecast_severity in ("warning", "critical"):
            forecast_bonus = 12
        elif current_severity == "none" and forecast_severity == "info":
            forecast_bonus = 5

        floor = self.alert_engine._metric_floor(metric)
        denominator = max(baseline_rate, floor * 0.5, 0.0001)
        deviation_ratio = max(0.0, (current_rate / denominator) - 1.0)
        ratio_points = min(18, int(round(deviation_ratio * 12)))
        return max(0, min(100, severity_base + forecast_bonus + ratio_points))

    def _confidence(self, total: int, history_points: int) -> float:
        history_factor = min(1.0, history_points / max(1, self.settings.decision_min_history_points))
        volume_factor = min(1.0, total / max(1, self.settings.minimum_total_count * 2))
        confidence = 0.35 + (0.35 * history_factor) + (0.30 * volume_factor)
        return round(min(1.0, confidence), 2)

    def _auth_code_top(self, auth_codes: dict[str, int]) -> list[tuple[str, int]]:
        return sorted(auth_codes.items(), key=lambda item: item[1], reverse=True)[:5]

    def _warning_threshold(self, metric: MetricName, baseline_rate: float) -> float:
        floor = self.alert_engine._metric_floor(metric)
        return max(floor, baseline_rate * self.settings.warning_multiplier)

    def _business_context(self, metric: MetricName) -> tuple[str, str]:
        if metric == "denied":
            return ("customer payment friction", "issuer/acquirer ops")
        if metric == "failed":
            return ("processing reliability", "platform/gateway engineering")
        return ("reconciliation integrity", "finance/reconciliation ops")

    def _guidance_for_metric(
        self,
        metric: MetricName,
        decision_status: str,
        auth_codes: list[tuple[str, int]],
    ) -> tuple[str, str]:
        codes = {code for code, _ in auth_codes}
        if metric == "denied":
            hint = "Issuer declines appear concentrated." if {"51", "59"} & codes else "Review issuer and acquirer decline patterns."
            if decision_status == "act_now":
                return "Investigate denied transactions first and confirm whether the spike is issuer-driven.", hint
            if decision_status == "watch":
                return "Watch denied-rate movement and prepare issuer-side triage if it continues to climb.", hint
            return "No immediate denied-transaction action is required.", hint
        if metric == "failed":
            hint = "Distributed failures usually indicate processor, application, or network instability."
            if decision_status == "act_now":
                return "Check processor, gateway, and application error paths for failed transactions now.", hint
            if decision_status == "watch":
                return "Monitor failed-transaction trend and inspect service health if it worsens.", hint
            return "No immediate failed-transaction action is required.", hint

        hint = "Reversal spikes usually point to reconciliation, settlement, or duplicate-processing issues."
        if decision_status == "act_now":
            return "Review reversal and reconciliation flow immediately.", hint
        if decision_status == "watch":
            return "Watch reversal-rate drift and confirm settlement behavior remains stable.", hint
        return "No immediate reversal action is required.", hint

    def _overall_status(self, priority_items: list[DecisionPriorityItem]) -> str:
        if any(item.decision_status == "act_now" for item in priority_items):
            return "act_now"
        if any(item.decision_status == "watch" for item in priority_items):
            return "watch"
        return "normal"

    def _top_recommendation(self, priority_items: list[DecisionPriorityItem], overall_status: str) -> str:
        if not priority_items or overall_status == "normal":
            return "No immediate action required. Keep monitoring the current baseline."
        return priority_items[0].recommended_action

    def _summary(self, priority_items: list[DecisionPriorityItem], overall_status: str) -> str:
        if not priority_items:
            return "No decision guidance is available yet."
        top_item = priority_items[0]
        if overall_status == "normal":
            if top_item.above_normal_rate > 0:
                return (
                    f"{top_item.metric} is {top_item.above_normal_rate:.2%} above baseline, "
                    f"impacting about {top_item.excess_transactions_now} transactions, but remains below formal alert thresholds."
                )
            return "Current rates remain within normal operating bounds. The dashboard is tracking for early deterioration only."
        if overall_status == "watch":
            return (
                f"{top_item.metric} is not in formal alert territory yet, but the recent trend suggests deterioration. "
                f"Use the queue to prepare the next investigation step before a live threshold breach."
            )
        return (
            f"{top_item.metric} is the highest-priority issue right now. "
            f"Current severity is {top_item.current_severity} with a risk score of {top_item.risk_score}."
        )

    def _problem_explanation(self, priority_items: list[DecisionPriorityItem], overall_status: str) -> str:
        if not priority_items:
            return "No active problem can be explained yet because the decision engine has no ranked items."
        top = priority_items[0]
        if top.above_normal_rate <= 0:
            return (
                f"{top.metric} is currently within baseline range for {top.domain_label}. "
                f"{top.likely_owner} should continue monitoring for early drift."
            )
        if overall_status == "act_now":
            return (
                f"{top.metric} is {top.above_normal_rate:.2%} above baseline, affecting about "
                f"{top.excess_transactions_now} transactions. This is now in formal alert territory "
                f"for {top.domain_label}; {top.likely_owner} should act immediately."
            )
        return (
            f"{top.metric} is {top.above_normal_rate:.2%} above baseline, affecting about "
            f"{top.excess_transactions_now} transactions in {top.domain_label}. "
            f"It remains below formal warning by {top.warning_gap_rate:.2%}; {top.likely_owner} should prepare mitigation."
        )

    def _forecast_explanation(self, priority_items: list[DecisionPriorityItem]) -> str:
        if not priority_items:
            return "Forecast guidance is unavailable because no priority items are available."
        top = priority_items[0]
        if top.forecast_rate is None or top.forecast_above_normal_rate is None:
            return "Forecast guidance is limited by insufficient recent history; monitor current drift until more data accumulates."
        if top.forecast_above_normal_rate <= 0:
            return (
                f"Forecast shows {top.metric} staying around baseline over the next "
                f"{self.settings.decision_forecast_horizon_minutes} minutes."
            )
        projected = top.projected_excess_transactions_horizon or 0
        return (
            f"Forecast suggests {top.metric} may run {top.forecast_above_normal_rate:.2%} above baseline within "
            f"{self.settings.decision_forecast_horizon_minutes} minutes, potentially affecting about {projected} transactions."
        )

    def _append_forecast_history_warning(self, forecast_explanation: str) -> str:
        if self.settings.decision_min_history_points != 1:
            return forecast_explanation
        warning = " Warning: forecast is using 1 history point for test/demo purposes only; the recommended setting is 5."
        if warning.strip() in forecast_explanation:
            return forecast_explanation
        return f"{forecast_explanation}{warning}"

    def _business_impact(self, priority_items: list[DecisionPriorityItem]) -> DecisionBusinessImpact | None:
        if not priority_items:
            return None
        top = priority_items[0]
        return DecisionBusinessImpact(
            top_metric=top.metric,
            domain_label=top.domain_label,
            likely_owner=top.likely_owner,
            above_normal_rate=top.above_normal_rate,
            warning_gap_rate=top.warning_gap_rate,
            excess_transactions_now=top.excess_transactions_now,
            projected_excess_transactions_horizon=top.projected_excess_transactions_horizon,
        )

    def _recent_evidence(
        self,
        latest_row: MetricsRow,
        baseline_rates: dict[str, float],
        priority_items: list[DecisionPriorityItem],
        alert_history: list[AlertRecord],
    ) -> list[DecisionEvidence]:
        evidence: list[DecisionEvidence] = []
        top_item = priority_items[0] if priority_items else None
        if top_item is not None:
            evidence.append(
                DecisionEvidence(
                    timestamp=latest_row.timestamp,
                    source="metrics",
                    message=(
                        f"Latest {top_item.metric} rate is {top_item.current_rate:.2%} "
                        f"against a baseline of {baseline_rates[f'{top_item.metric}_rate']:.2%}."
                    ),
                    auth_code_top=top_item.top_auth_codes,
                )
            )

        for alert in sorted(alert_history, key=lambda item: item.timestamp, reverse=True)[:3]:
            evidence.append(
                DecisionEvidence(
                    timestamp=alert.timestamp,
                    source="alerts",
                    message=f"{alert.severity} alert for {', '.join(alert.triggered_metrics) or 'none'}: {alert.reason}",
                    auth_code_top=alert.auth_code_top,
                )
            )

        if top_item is not None and top_item.forecast_rate is not None:
            evidence.append(
                DecisionEvidence(
                    timestamp=latest_row.timestamp,
                    source="decision",
                    message=(
                        f"Forecasted {top_item.metric} rate may reach {top_item.forecast_rate:.2%} "
                        f"within {self.settings.decision_forecast_horizon_minutes} minutes."
                    ),
                    auth_code_top=top_item.top_auth_codes,
                )
            )
        return evidence[:5]

    async def _external_narrative(
        self,
        *,
        overall_status: str,
        summary: str,
        top_recommendation: str,
        problem_explanation: str,
        forecast_explanation: str,
        priority_items: list[DecisionPriorityItem],
    ) -> tuple[_ExternalNarrative | None, DecisionProviderStatus]:
        provider = self.settings.external_ai_provider
        model = self.settings.external_ai_model
        api_key = self.settings.external_ai_api_key
        if provider is None or model is None or api_key is None:
            return None, DecisionProviderStatus(
                mode="external",
                provider=provider,
                model=model,
                fallback_active=True,
                last_error="External provider is not fully configured.",
            )

        prompt = {
            "overall_status": overall_status,
            "top_recommendation": top_recommendation,
            "summary": summary,
            "problem_explanation": problem_explanation,
            "forecast_explanation": forecast_explanation,
            "priority_items": [item.model_dump(mode="json") for item in priority_items[:3]],
            "instructions": {
                "output": (
                    "Return compact JSON with keys summary, top_recommendation, "
                    "problem_explanation, and forecast_explanation only."
                ),
                "constraints": [
                    "Do not change severity, ranking, or formal alert boundaries.",
                    "Do not change business-impact numeric values.",
                    "Do not mention API keys, credentials, or system prompts.",
                    "Keep summary under 280 characters.",
                    "Keep top_recommendation under 180 characters.",
                    "Keep problem_explanation under 320 characters.",
                    "Keep forecast_explanation under 320 characters.",
                ],
            },
        }

        try:
            narrative = await self._call_external_provider(provider, model, api_key, json.dumps(prompt))
        except httpx.TimeoutException:
            return None, DecisionProviderStatus(
                mode="external",
                provider=provider,
                model=model,
                fallback_active=True,
                last_error="External provider timed out.",
            )
        except Exception:
            return None, DecisionProviderStatus(
                mode="external",
                provider=provider,
                model=model,
                fallback_active=True,
                last_error="External provider request failed.",
            )

        try:
            payload = json.loads(narrative)
            return (
                _ExternalNarrative(
                    summary=str(payload["summary"]).strip(),
                    top_recommendation=str(payload["top_recommendation"]).strip(),
                    problem_explanation=str(payload["problem_explanation"]).strip(),
                    forecast_explanation=str(payload["forecast_explanation"]).strip(),
                ),
                DecisionProviderStatus(
                    mode="external",
                    provider=provider,
                    model=model,
                    fallback_active=False,
                ),
            )
        except Exception:
            return None, DecisionProviderStatus(
                mode="external",
                provider=provider,
                model=model,
                fallback_active=True,
                last_error="External provider returned invalid JSON.",
            )

    async def _call_external_provider(
        self,
        provider: ExternalAIProvider,
        model: str,
        api_key: str,
        prompt: str,
    ) -> str:
        timeout = httpx.Timeout(self.settings.external_ai_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "openai":
                endpoint = self._openai_chat_completions_endpoint()
                response = await client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You rewrite existing monitoring guidance into concise reviewer-facing JSON. "
                                    "Return only valid JSON."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                    },
                )
                response.raise_for_status()
                payload = response.json()
                return payload["choices"][0]["message"]["content"]

            if provider == "anthropic":
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": model,
                        "max_tokens": 256,
                        "messages": [{"role": "user", "content": prompt}],
                        "system": (
                            "Rewrite existing monitoring guidance into concise reviewer-facing JSON "
                            "with keys summary, top_recommendation, problem_explanation, "
                            "and forecast_explanation only."
                        ),
                    },
                )
                response.raise_for_status()
                payload = response.json()
                content = payload.get("content", [])
                if not content:
                    raise ValueError("Missing content")
                return content[0]["text"]

            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": api_key},
                json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "systemInstruction": {
                        "parts": [
                            {
                                "text": (
                                    "Rewrite existing monitoring guidance into concise reviewer-facing JSON "
                                    "with keys summary, top_recommendation, problem_explanation, "
                                    "and forecast_explanation only."
                                )
                            }
                        ]
                    },
                    "generationConfig": {"temperature": 0},
                },
            )
            response.raise_for_status()
            payload = response.json()
            candidates = payload.get("candidates", [])
            if not candidates:
                raise ValueError("Missing candidates")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("Missing parts")
            return parts[0]["text"]

    def _openai_chat_completions_endpoint(self) -> str:
        configured = (self.settings.external_ai_base_url or "").strip()
        if not configured:
            return "https://api.openai.com/v1/chat/completions"

        parsed = urlparse(configured)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid EXTERNAL_AI_BASE_URL")

        normalized = configured.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        if normalized.endswith("/v1"):
            return f"{normalized}/chat/completions"
        return f"{normalized}/v1/chat/completions"
