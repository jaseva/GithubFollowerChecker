from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean, pstdev
from typing import Literal, TypedDict

from app.models import (
    DashboardData,
    DashboardQueryResponse,
    EnrichedChange,
    InsightEvidence,
    InsightMode,
    InsightRange,
    InsightResponse,
)
from app.services.tracker import get_dashboard_data, utcnow


RANGE_TO_DAYS: dict[InsightRange, float] = {
    "24h": 1,
    "7d": 7,
    "30d": 30,
}


class InsightContext(TypedDict):
    start: datetime | None
    end: datetime | None
    points: list[tuple[datetime, int]]
    deltas: list[tuple[datetime, int]]
    new_followers: list[EnrichedChange]
    lost_followers: list[EnrichedChange]
    ranked: list[EnrichedChange]
    baseline: int
    current: int
    net: int
    churn_rate: float
    avg_delta: float
    volatility: float
    biggest_gain: tuple[datetime, int] | None
    biggest_loss: tuple[datetime, int] | None
    warnings: list[str]


def signed(value: int | float) -> str:
    rounded = round(value, 1) if isinstance(value, float) and not value.is_integer() else int(value)
    if rounded > 0:
        return f"+{rounded:,}"
    return f"{rounded:,}"


def pct(value: float) -> str:
    return f"{value:.1f}%"


def range_label(range_key: InsightRange) -> str:
    return {
        "24h": "last 24 hours",
        "7d": "last 7 days",
        "30d": "last 30 days",
    }[range_key]


def parse_window(dashboard: DashboardData, range_key: InsightRange) -> tuple[datetime | None, datetime | None]:
    timestamps = dashboard.trends.labels
    if not timestamps:
        return None, None

    end = timestamps[-1]
    start = end - timedelta(days=RANGE_TO_DAYS[range_key])
    return start, end


def filter_changes(
    items: list[EnrichedChange],
    start: datetime | None,
    end: datetime | None,
) -> list[EnrichedChange]:
    if start is None or end is None:
        return []
    return [item for item in items if start <= item.timestamp <= end]


def window_points(
    dashboard: DashboardData,
    start: datetime | None,
    end: datetime | None,
) -> list[tuple[datetime, int]]:
    if start is None or end is None:
        return []
    points = [
        (timestamp, count)
        for timestamp, count in zip(dashboard.trends.labels, dashboard.trends.history)
        if start <= timestamp <= end
    ]
    if not points and dashboard.trends.labels:
        return [(dashboard.trends.labels[-1], dashboard.trends.history[-1])]
    return points


def point_deltas(points: list[tuple[datetime, int]]) -> list[tuple[datetime, int]]:
    return [
        (points[index][0], points[index][1] - points[index - 1][1])
        for index in range(1, len(points))
    ]


def top_followers(items: list[EnrichedChange], limit: int = 3) -> list[EnrichedChange]:
    return sorted(
        items,
        key=lambda item: (item.signal_score, item.followers, item.public_repos),
        reverse=True,
    )[:limit]


def quality_warnings(dashboard: DashboardData, points: list[tuple[datetime, int]]) -> list[str]:
    warnings: list[str] = []
    health = dashboard.health
    if health.stale_data:
        warnings.append("Follower behavior may be incomplete because the latest snapshot is stale.")
    if health.partial_data:
        warnings.append("Some profile enrichment may be partial because one or more API calls failed.")
    if len(points) < 2:
        warnings.append("Only one snapshot is available in this window, so trend interpretation is limited.")
    if health.missed_snapshots > 0:
        warnings.append(f"{health.missed_snapshots} expected snapshot(s) appear to be missing.")
    return warnings


def build_context(dashboard: DashboardData, range_key: InsightRange) -> InsightContext:
    start, end = parse_window(dashboard, range_key)
    points = window_points(dashboard, start, end)
    deltas = point_deltas(points)
    new_followers = filter_changes(dashboard.all_new_followers, start, end)
    lost_followers = filter_changes(dashboard.all_lost_followers, start, end)
    ranked = top_followers(new_followers, 5)

    baseline = points[0][1] if points else dashboard.stats.total_followers
    current = points[-1][1] if points else dashboard.stats.total_followers
    net = current - baseline if len(points) > 1 else len(new_followers) - len(lost_followers)
    churn_rate = (len(lost_followers) / max(current, 1)) * 100
    avg_delta = mean([delta for _, delta in deltas]) if deltas else 0.0
    volatility = pstdev([delta for _, delta in deltas]) if len(deltas) > 1 else 0.0
    biggest_gain = max(deltas, key=lambda item: item[1], default=None)
    biggest_loss = min(deltas, key=lambda item: item[1], default=None)

    return {
        "start": start,
        "end": end,
        "points": points,
        "deltas": deltas,
        "new_followers": new_followers,
        "lost_followers": lost_followers,
        "ranked": ranked,
        "baseline": baseline,
        "current": current,
        "net": net,
        "churn_rate": churn_rate,
        "avg_delta": avg_delta,
        "volatility": volatility,
        "biggest_gain": biggest_gain,
        "biggest_loss": biggest_loss,
        "warnings": quality_warnings(dashboard, points),
    }


def evidence_for_context(dashboard: DashboardData, context: InsightContext) -> list[InsightEvidence]:
    ranked = context["ranked"]
    biggest_gain = context["biggest_gain"]
    biggest_loss = context["biggest_loss"]

    evidence = [
        InsightEvidence(label="Current followers", value=f"{context['current']:,}", source="dashboard.metrics"),
        InsightEvidence(label="Net movement", value=signed(int(context["net"])), source="dashboard.trends"),
        InsightEvidence(label="New followers", value=f"{len(context['new_followers']):,}", source="dashboard.all_new_followers"),
        InsightEvidence(label="Lost followers", value=f"{len(context['lost_followers']):,}", source="dashboard.all_lost_followers"),
        InsightEvidence(label="Snapshot count", value=f"{len(context['points']):,}", source="dashboard.trends"),
        InsightEvidence(label="Health", value=dashboard.health.api_status, source="dashboard.health"),
    ]

    if isinstance(ranked, list) and ranked:
        top = ranked[0]
        evidence.append(
            InsightEvidence(
                label="Top new follower",
                value=f"@{top.username} ({top.signal_score:.0f} signal, {top.followers:,} followers)",
                source="dashboard.enrichment",
            )
        )
    if biggest_gain:
        timestamp, value = biggest_gain
        evidence.append(
            InsightEvidence(
                label="Largest positive delta",
                value=f"{signed(value)} on {timestamp.strftime('%b %d, %Y')}",
                source="dashboard.trends",
            )
        )
    if biggest_loss:
        timestamp, value = biggest_loss
        evidence.append(
            InsightEvidence(
                label="Largest negative delta",
                value=f"{signed(value)} on {timestamp.strftime('%b %d, %Y')}",
                source="dashboard.trends",
            )
        )
    return evidence


def confidence_for(context: InsightContext, dashboard: DashboardData) -> Literal["high", "medium", "low"]:
    points = context["points"]
    if dashboard.health.api_status == "error" or len(points) < 2:
        return "low"
    if dashboard.health.partial_data or dashboard.health.stale_data or dashboard.health.missed_snapshots > 0:
        return "medium"
    return "high"


def recommended_actions(context: InsightContext, dashboard: DashboardData) -> list[str]:
    net = int(context["net"])
    lost_count = len(context["lost_followers"])
    ranked = context["ranked"]

    actions: list[str] = []
    if dashboard.health.stale_data or dashboard.health.partial_data:
        actions.append("Run an explicit refresh before treating this window as final.")
    if lost_count > 0:
        actions.append("Open the lost follower drawer and sort by reach to inspect churn quality.")
    if isinstance(ranked, list) and ranked:
        actions.append("Review high-signal new followers and add relationship notes outside the app if needed.")
    if net == 0 and lost_count == 0:
        actions.append("Keep monitoring; no immediate investigation is indicated by the current local data.")
    actions.append("Export the filtered events if this window needs to be shared or archived.")
    return actions[:3]


def build_summary(
    mode: InsightMode,
    range_key: InsightRange,
    dashboard: DashboardData,
    context: InsightContext,
) -> tuple[str, str, list[str]]:
    label = range_label(range_key)
    net = int(context["net"])
    new_count = len(context["new_followers"])
    lost_count = len(context["lost_followers"])
    points_count = len(context["points"])
    ranked = context["ranked"]
    top = ranked[0] if isinstance(ranked, list) and ranked else None
    avg_delta = float(context["avg_delta"])
    volatility = float(context["volatility"])
    churn = float(context["churn_rate"])

    if net > 0:
        headline = f"Audience expanded {signed(net)} in the {label}."
    elif net < 0:
        headline = f"Audience contracted {signed(net)} in the {label}."
    else:
        headline = f"Audience was flat in the {label}."

    if mode == "technical":
        summary = (
            f"{points_count} snapshot(s) support this read. The window moved from "
            f"{context['baseline']:,} to {context['current']:,} followers with average snapshot delta "
            f"{signed(avg_delta)} and volatility {volatility:.2f}."
        )
        bullets = [
            f"New/lost events: {new_count:,} gained and {lost_count:,} lost.",
            f"Window churn rate is {pct(churn)} against the current follower count.",
            f"Data health is {dashboard.health.api_status}; missed snapshots: {dashboard.health.missed_snapshots}.",
        ]
    elif mode == "executive":
        summary = (
            f"In the {label}, follower movement was {signed(net)} with {new_count:,} gains and "
            f"{lost_count:,} losses. The practical read is {'positive momentum' if net > 0 else 'churn pressure' if net < 0 else 'stable audience'}."
        )
        bullets = [
            f"Current audience is {context['current']:,} followers.",
            f"Top relationship lead: @{top.username} with {top.followers:,} followers." if top else "No high-signal new follower was recorded in this window.",
            f"Trust state: {dashboard.health.api_status}; freshness is {dashboard.health.data_freshness_minutes if dashboard.health.data_freshness_minutes is not None else 'unknown'} minutes.",
        ]
    else:
        summary = (
            f"{new_count:,} new and {lost_count:,} lost follower event(s) were found in the {label}. "
            f"The net movement is {signed(net)}."
        )
        bullets = [
            f"Current follower count: {context['current']:,}.",
            f"Top new follower: @{top.username} ({top.signal_score:.0f} signal)." if top else "No new follower lead is available for this window.",
            f"Data confidence is {confidence_for(context, dashboard)}.",
        ]

    return headline, summary, bullets


def generate_insights(
    *,
    range_key: InsightRange = "30d",
    mode: InsightMode = "brief",
    refresh: bool = False,
) -> InsightResponse:
    dashboard = get_dashboard_data(refresh=refresh)
    context = build_context(dashboard, range_key)
    headline, summary, bullets = build_summary(mode, range_key, dashboard, context)

    return InsightResponse(
        generated_at=utcnow(),
        range=range_key,
        mode=mode,
        window_start=context["start"],
        window_end=context["end"],
        headline=headline,
        summary=summary,
        bullets=bullets,
        evidence=evidence_for_context(dashboard, context),
        recommended_actions=recommended_actions(context, dashboard),
        confidence=confidence_for(context, dashboard),
        stale=dashboard.health.stale_data,
        data_warnings=context["warnings"],
    )


def classify_question(question: str) -> str:
    normalized = question.lower()
    if any(term in normalized for term in ["important", "high signal", "top follower", "most valuable", "who"]):
        return "important_followers"
    if any(term in normalized for term in ["churn", "lost", "drop", "spike", "dip"]):
        return "churn_spike"
    if any(term in normalized for term in ["manager", "executive", "summarize", "summary"]):
        return "executive_summary"
    if any(term in normalized for term in ["health", "fresh", "stale", "sync", "trust"]):
        return "data_health"
    if any(term in normalized for term in ["changed", "change", "month", "week", "24 hours", "movement"]):
        return "movement"
    return "general"


def answer_query(question: str, *, range_key: InsightRange = "30d", refresh: bool = False) -> DashboardQueryResponse:
    dashboard = get_dashboard_data(refresh=refresh)
    context = build_context(dashboard, range_key)
    intent = classify_question(question)
    evidence = evidence_for_context(dashboard, context)
    warnings = context["warnings"]
    net = int(context["net"])
    new_count = len(context["new_followers"])
    lost_count = len(context["lost_followers"])
    ranked = context["ranked"]
    biggest_loss = context["biggest_loss"]
    biggest_gain = context["biggest_gain"]

    if intent == "important_followers":
        if isinstance(ranked, list) and ranked:
            names = ", ".join(f"@{item.username} ({item.signal_score:.0f} signal, {item.followers:,} reach)" for item in ranked[:3])
            answer = f"The strongest new follower leads in the {range_label(range_key)} are {names}."
            action = "Open the high-signal drawer and sort by reach or repository count for a closer review."
        else:
            answer = f"No high-signal new followers are present in the {range_label(range_key)}."
            action = "Switch to a longer range or refresh data before concluding there are no new leads."
    elif intent == "churn_spike":
        loss_text = "No negative delta was recorded."
        if biggest_loss:
            timestamp, value = biggest_loss
            loss_text = f"The largest churn delta was {signed(value)} on {timestamp.strftime('%b %d, %Y')}."
        answer = f"{loss_text} The window includes {lost_count:,} lost follower event(s)."
        action = "Open lost follower events, sort by reach, and inspect whether the losses cluster around a stale-data warning."
    elif intent == "executive_summary":
        answer = (
            f"For a manager: the {range_label(range_key)} show {signed(net)} net movement, "
            f"{new_count:,} gains, {lost_count:,} losses, and {dashboard.health.api_status} data health."
        )
        action = "Use Executive mode in the Insights panel and export the filtered events if sharing this readout."
    elif intent == "data_health":
        answer = (
            f"Data health is {dashboard.health.api_status}. Freshness is "
            f"{dashboard.health.data_freshness_minutes if dashboard.health.data_freshness_minutes is not None else 'unknown'} minutes, "
            f"with {dashboard.health.missed_snapshots} missed snapshot(s) and {dashboard.health.snapshot_count} total snapshot(s)."
        )
        action = "Run an explicit refresh if the state is stale, degraded, or partial before making decisions from this window."
    elif intent == "movement":
        gain_text = ""
        if biggest_gain:
            timestamp, value = biggest_gain
            gain_text = f" Largest positive delta: {signed(value)} on {timestamp.strftime('%b %d, %Y')}."
        answer = f"The {range_label(range_key)} changed by {signed(net)} with {new_count:,} gained and {lost_count:,} lost follower event(s).{gain_text}"
        action = "Toggle the Delta chart and compare annotations against the event drawer."
    else:
        answer = (
            f"Using only local dashboard data, the {range_label(range_key)} show {signed(net)} net movement, "
            f"{new_count:,} new follower event(s), {lost_count:,} lost follower event(s), and {dashboard.health.api_status} health."
        )
        action = "Ask about movement, churn spikes, high-signal followers, or data health for a narrower answer."

    return DashboardQueryResponse(
        generated_at=utcnow(),
        question=question,
        interpreted_intent=intent,
        range=range_key,
        answer=answer,
        evidence=evidence[:8],
        recommended_next_action=action,
        confidence=confidence_for(context, dashboard),
        data_warnings=warnings,
    )
