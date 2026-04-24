from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Stats(BaseModel):
    total_followers: int
    new_followers: int
    unfollowers: int
    net_change: int = 0


class GitHubProfile(BaseModel):
    username: str
    name: str | None = None
    avatar_url: str | None = None
    html_url: str
    bio: str | None = None
    public_repos: int = 0
    following: int = 0
    followers: int = 0
    company: str | None = None
    location: str | None = None
    created_at: datetime | None = None


class Trends(BaseModel):
    labels: list[datetime]
    history: list[int]


class Change(BaseModel):
    username: str
    timestamp: datetime


class EnrichedChange(Change):
    name: str | None = None
    avatar_url: str | None = None
    html_url: str
    bio: str | None = None
    public_repos: int = 0
    followers: int = 0
    following: int = 0
    company: str | None = None
    location: str | None = None
    created_at: datetime | None = None
    signal_score: float = 0.0
    signal_label: str = "Emerging"


class DashboardMetrics(BaseModel):
    total_followers: int
    following: int
    net_24h: int
    net_7d: int
    net_30d: int
    average_daily_growth: float
    churn_rate: float
    volatility_score: float
    stability_score: float
    snapshot_count: int
    change_records_30d: int


class SyncRunSummary(BaseModel):
    timestamp: datetime
    status: Literal["success", "failure"]
    follower_count: int | None = None
    new_count: int = 0
    lost_count: int = 0
    error: str | None = None


class DashboardHealth(BaseModel):
    api_status: Literal["healthy", "degraded", "error"]
    partial_data: bool
    stale_data: bool
    last_successful_sync: datetime | None = None
    last_failed_sync: datetime | None = None
    last_error: str | None = None
    snapshot_count: int = 0
    expected_cadence_minutes: int | None = None
    missed_snapshots: int = 0
    data_freshness_minutes: int | None = None
    recent_sync_runs: list[SyncRunSummary] = Field(default_factory=list)


class ChartAnnotation(BaseModel):
    timestamp: datetime
    kind: Literal["spike", "dip", "gain", "loss", "peak", "low"]
    label: str
    value: int
    magnitude: int = 0


class DashboardData(BaseModel):
    generated_at: datetime
    profile: GitHubProfile
    stats: Stats
    metrics: DashboardMetrics
    trends: Trends
    health: DashboardHealth
    recent_new_followers: list[EnrichedChange]
    recent_lost_followers: list[EnrichedChange]
    all_new_followers: list[EnrichedChange]
    all_lost_followers: list[EnrichedChange]
    high_signal_new_followers: list[EnrichedChange]
    annotations: list[ChartAnnotation]


InsightRange = Literal["24h", "7d", "30d"]
InsightMode = Literal["brief", "executive", "technical"]


class InsightRequest(BaseModel):
    range: InsightRange = "30d"
    mode: InsightMode = "brief"
    refresh: bool = False


class InsightEvidence(BaseModel):
    label: str
    value: str
    source: str


class InsightResponse(BaseModel):
    generated_at: datetime
    range: InsightRange
    mode: InsightMode
    window_start: datetime | None = None
    window_end: datetime | None = None
    headline: str
    summary: str
    bullets: list[str]
    evidence: list[InsightEvidence]
    recommended_actions: list[str]
    confidence: Literal["high", "medium", "low"]
    stale: bool = False
    data_warnings: list[str] = Field(default_factory=list)


class DashboardQueryRequest(BaseModel):
    question: str
    range: InsightRange = "30d"
    refresh: bool = False


class DashboardQueryResponse(BaseModel):
    generated_at: datetime
    question: str
    interpreted_intent: str
    range: InsightRange
    answer: str
    evidence: list[InsightEvidence]
    recommended_next_action: str
    confidence: Literal["high", "medium", "low"]
    data_warnings: list[str] = Field(default_factory=list)
