import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from statistics import mean, median, pstdev
from threading import Lock
from typing import Any

import requests
from dotenv import load_dotenv

from app.models import (
    Change,
    ChartAnnotation,
    DashboardData,
    DashboardHealth,
    DashboardMetrics,
    EnrichedChange,
    GitHubProfile,
    Stats,
    Trends,
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
load_dotenv(os.path.join(REPO_ROOT, ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

DB_PATH = os.path.join(BASE_DIR, "followers.db")
LEGACY_DB_PATH = os.path.join(REPO_ROOT, "follower_data.db")
API_URL = "https://api.github.com"
USERNAME = os.getenv("GITHUB_USERNAME")
TOKEN = os.getenv("GITHUB_TOKEN")
REQUEST_TIMEOUT = 20
SQLITE_TIMEOUT_SECONDS = 30
SQLITE_BUSY_TIMEOUT_MS = 30000
SQLITE_WRITE_RETRY_ATTEMPTS = 3
SQLITE_WRITE_RETRY_BASE_SECONDS = 0.2
SYNC_INTERVAL_MINUTES = 5
SNAPSHOT_INTERVAL_MINUTES = 30
USER_CACHE_HOURS = 24
FULL_HISTORY_DAYS = 30
RECENT_WINDOW_HOURS = 24
LEGACY_IMPORT_SOURCE = "legacy_desktop_db_v1"
CHANGE_TABLES = {"new_followers", "lost_followers"}

_DB_INIT_LOCK = Lock()
_DB_INITIALIZED = False
_SYNC_LOCK = Lock()


def utcnow() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def isoformat(value: datetime) -> str:
    return value.isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def build_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=SQLITE_TIMEOUT_SECONDS)
    conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS followers (
                count INTEGER,
                timestamp TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS new_followers (
                username TEXT,
                timestamp TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lost_followers (
                username TEXT,
                timestamp TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS current_followers (
                username TEXT PRIMARY KEY
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_cache (
                username TEXT PRIMARY KEY,
                name TEXT,
                avatar_url TEXT,
                html_url TEXT,
                bio TEXT,
                public_repos INTEGER DEFAULT 0,
                followers INTEGER DEFAULT 0,
                following INTEGER DEFAULT 0,
                company TEXT,
                location TEXT,
                created_at TEXT,
                cached_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                follower_count INTEGER,
                new_count INTEGER DEFAULT 0,
                lost_count INTEGER DEFAULT 0
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS data_imports (
                source TEXT PRIMARY KEY,
                imported_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_followers_timestamp ON followers(timestamp)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_followers_unique_timestamp ON followers(timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_new_followers_timestamp ON new_followers(timestamp)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_new_followers_unique ON new_followers(username, timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lost_followers_timestamp ON lost_followers(timestamp)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_lost_followers_unique ON lost_followers(username, timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_sync_runs_timestamp ON sync_runs(timestamp)"
        )
        import_legacy_data(conn)
        conn.commit()
    finally:
        conn.close()


def initialize_tracker_db() -> None:
    global _DB_INITIALIZED

    if _DB_INITIALIZED:
        return

    with _DB_INIT_LOCK:
        if _DB_INITIALIZED:
            return
        init_db()
        _DB_INITIALIZED = True


def request_json(url: str) -> Any:
    response = requests.get(url, headers=build_headers(), timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_github_profile_json() -> dict[str, Any]:
    if not USERNAME:
        raise RuntimeError("GITHUB_USERNAME is not configured.")
    return request_json(f"{API_URL}/users/{USERNAME}")


def fetch_followers() -> list[str]:
    if not USERNAME:
        raise RuntimeError("GITHUB_USERNAME is not configured.")

    url = f"{API_URL}/users/{USERNAME}/followers?per_page=100"
    followers: list[str] = []
    while url:
        response = requests.get(url, headers=build_headers(), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        followers.extend(entry["login"] for entry in data if entry.get("login"))
        url = response.links.get("next", {}).get("url")
    return sorted(set(followers))


def fetch_user_json(username: str) -> dict[str, Any]:
    return request_json(f"{API_URL}/users/{username}")


def normalize_timestamp(value: str | None) -> str | None:
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    return isoformat(parsed)


def import_marker_exists(conn: sqlite3.Connection, source: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM data_imports WHERE source = ?",
        (source,),
    ).fetchone()
    return row is not None


def mark_import_complete(conn: sqlite3.Connection, source: str) -> None:
    conn.execute(
        """
        INSERT INTO data_imports (source, imported_at)
        VALUES (?, ?)
        ON CONFLICT(source) DO UPDATE SET imported_at = excluded.imported_at
        """,
        (source, isoformat(utcnow())),
    )


def import_legacy_data(conn: sqlite3.Connection) -> None:
    if import_marker_exists(conn, LEGACY_IMPORT_SOURCE):
        return
    if not os.path.exists(LEGACY_DB_PATH):
        return

    legacy = sqlite3.connect(LEGACY_DB_PATH)
    legacy.row_factory = sqlite3.Row
    try:
        snapshot_rows = legacy.execute(
            """
            SELECT timestamp, COUNT(*) AS count
            FROM followers
            GROUP BY timestamp
            ORDER BY timestamp
            """
        ).fetchall()

        snapshot_sets: dict[str, set[str]] = {}
        follower_rows = legacy.execute(
            "SELECT username, timestamp FROM followers ORDER BY timestamp, username"
        ).fetchall()
        for row in follower_rows:
            normalized = normalize_timestamp(row["timestamp"])
            if not normalized:
                continue
            snapshot_sets.setdefault(normalized, set()).add(row["username"])

        for row in snapshot_rows:
            normalized = normalize_timestamp(row["timestamp"])
            if not normalized:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO followers (count, timestamp) VALUES (?, ?)",
                (int(row["count"]), normalized),
            )

        previous_followers: set[str] | None = None
        latest_followers: set[str] = set()
        for timestamp in sorted(snapshot_sets):
            current_followers = snapshot_sets[timestamp]
            latest_followers = current_followers
            if previous_followers is None:
                previous_followers = current_followers
                continue

            new_users = sorted(current_followers - previous_followers)
            lost_users = sorted(previous_followers - current_followers)

            if new_users:
                conn.executemany(
                    "INSERT OR IGNORE INTO new_followers (username, timestamp) VALUES (?, ?)",
                    [(username, timestamp) for username in new_users],
                )
            if lost_users:
                conn.executemany(
                    "INSERT OR IGNORE INTO lost_followers (username, timestamp) VALUES (?, ?)",
                    [(username, timestamp) for username in lost_users],
                )
            previous_followers = current_followers

        try:
            unfollower_rows = legacy.execute(
                "SELECT username, timestamp FROM unfollowers"
            ).fetchall()
            if unfollower_rows:
                conn.executemany(
                    "INSERT OR IGNORE INTO lost_followers (username, timestamp) VALUES (?, ?)",
                    [
                        (row["username"], normalized)
                        for row in unfollower_rows
                        if (normalized := normalize_timestamp(row["timestamp"])) is not None
                    ],
                )
        except sqlite3.Error:
            pass

        if latest_followers and not load_current_followers(conn):
            replace_current_followers(conn, latest_followers)

        mark_import_complete(conn, LEGACY_IMPORT_SOURCE)
    finally:
        legacy.close()


def record_sync_run(
    conn: sqlite3.Connection,
    *,
    status: str,
    timestamp: datetime,
    follower_count: int | None = None,
    new_count: int = 0,
    lost_count: int = 0,
    error: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO sync_runs (timestamp, status, error, follower_count, new_count, lost_count)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (isoformat(timestamp), status, error, follower_count, new_count, lost_count),
    )


def load_cached_profile_row(conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM user_cache WHERE username = ?",
        (username,),
    ).fetchone()


def upsert_user_cache(conn: sqlite3.Connection, data: dict[str, Any]) -> None:
    login = data.get("login")
    if not login:
        return

    conn.execute(
        """
        INSERT INTO user_cache (
            username, name, avatar_url, html_url, bio, public_repos, followers,
            following, company, location, created_at, cached_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            name = excluded.name,
            avatar_url = excluded.avatar_url,
            html_url = excluded.html_url,
            bio = excluded.bio,
            public_repos = excluded.public_repos,
            followers = excluded.followers,
            following = excluded.following,
            company = excluded.company,
            location = excluded.location,
            created_at = excluded.created_at,
            cached_at = excluded.cached_at
        """,
        (
            login,
            data.get("name"),
            data.get("avatar_url"),
            data.get("html_url") or f"https://github.com/{login}",
            data.get("bio"),
            data.get("public_repos", 0),
            data.get("followers", 0),
            data.get("following", 0),
            data.get("company"),
            data.get("location"),
            data.get("created_at"),
            isoformat(utcnow()),
        ),
    )


def should_refresh_user_cache(row: sqlite3.Row | None) -> bool:
    if row is None:
        return True
    cached_at = parse_datetime(row["cached_at"])
    if cached_at is None:
        return True
    return cached_at < utcnow() - timedelta(hours=USER_CACHE_HOURS)


def ensure_user_cache(
    conn: sqlite3.Connection,
    username: str,
    *,
    allow_fetch: bool,
) -> sqlite3.Row | None:
    row = load_cached_profile_row(conn, username)
    if allow_fetch and should_refresh_user_cache(row):
        try:
            upsert_user_cache(conn, fetch_user_json(username))
            row = load_cached_profile_row(conn, username)
        except Exception:
            return row
    return row


def profile_from_row(row: sqlite3.Row | None, fallback_username: str | None = None) -> GitHubProfile:
    username = fallback_username or (row["username"] if row else USERNAME) or "unknown"
    html_url = row["html_url"] if row and row["html_url"] else f"https://github.com/{username}"
    return GitHubProfile(
        username=username,
        name=row["name"] if row else None,
        avatar_url=row["avatar_url"] if row else None,
        html_url=html_url,
        bio=row["bio"] if row else None,
        public_repos=int(row["public_repos"] or 0) if row else 0,
        following=int(row["following"] or 0) if row else 0,
        followers=int(row["followers"] or 0) if row else 0,
        company=row["company"] if row else None,
        location=row["location"] if row else None,
        created_at=parse_datetime(row["created_at"]) if row else None,
    )


def load_current_followers(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT username FROM current_followers").fetchall()
    return {row["username"] for row in rows}


def replace_current_followers(conn: sqlite3.Connection, followers: set[str]) -> None:
    conn.execute("DELETE FROM current_followers")
    conn.executemany(
        "INSERT INTO current_followers (username) VALUES (?)",
        [(username,) for username in sorted(followers)],
    )


def latest_successful_sync(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM sync_runs WHERE status = 'success' ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()


def latest_snapshot(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT count, timestamp FROM followers ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()


def should_insert_snapshot(conn: sqlite3.Connection, count: int, timestamp: datetime) -> bool:
    row = latest_snapshot(conn)
    if row is None:
        return True
    last_timestamp = parse_datetime(row["timestamp"])
    last_count = int(row["count"])
    if last_count != count:
        return True
    if last_timestamp is None:
        return True
    return last_timestamp <= timestamp - timedelta(minutes=SNAPSHOT_INTERVAL_MINUTES)


def insert_snapshot(conn: sqlite3.Connection, count: int, timestamp: datetime) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO followers (count, timestamp) VALUES (?, ?)",
        (count, isoformat(timestamp)),
    )


def is_database_locked_error(exc: sqlite3.OperationalError) -> bool:
    message = str(exc).lower()
    return "database is locked" in message or "database table is locked" in message


def successful_sync_since(timestamp: datetime) -> bool:
    conn = get_connection()
    try:
        row = latest_successful_sync(conn)
        if row is None:
            return False
        synced_at = parse_datetime(row["timestamp"])
        return synced_at is not None and synced_at >= timestamp
    finally:
        conn.close()


def sync_followers(*, force: bool = False) -> None:
    initialize_tracker_db()
    requested_at = utcnow()

    with _SYNC_LOCK:
        if force:
            try:
                if successful_sync_since(requested_at):
                    return
            except sqlite3.OperationalError as exc:
                if not is_database_locked_error(exc):
                    raise

        for attempt in range(SQLITE_WRITE_RETRY_ATTEMPTS + 1):
            try:
                _sync_followers_once(force=force)
                return
            except sqlite3.OperationalError as exc:
                if not is_database_locked_error(exc) or attempt >= SQLITE_WRITE_RETRY_ATTEMPTS:
                    raise
                time.sleep(SQLITE_WRITE_RETRY_BASE_SECONDS * (2**attempt))


def _sync_followers_once(*, force: bool = False) -> None:
    conn: sqlite3.Connection | None = None
    now = utcnow()

    try:
        conn = get_connection()
        latest_success = latest_successful_sync(conn)

        if latest_success is not None and not force:
            last_success = parse_datetime(latest_success["timestamp"])
            if last_success and last_success >= now - timedelta(minutes=SYNC_INTERVAL_MINUTES):
                return

        profile_data = fetch_github_profile_json()
        upsert_user_cache(conn, profile_data)

        current_followers = set(fetch_followers())
        previous_followers = load_current_followers(conn)

        new_users = sorted(current_followers - previous_followers) if previous_followers else []
        lost_users = sorted(previous_followers - current_followers) if previous_followers else []
        current_count = int(profile_data.get("followers", len(current_followers)))

        if should_insert_snapshot(conn, current_count, now):
            insert_snapshot(conn, current_count, now)

        replace_current_followers(conn, current_followers)

        if previous_followers:
            if new_users:
                conn.executemany(
                    "INSERT OR IGNORE INTO new_followers (username, timestamp) VALUES (?, ?)",
                    [(username, isoformat(now)) for username in new_users],
                )
            if lost_users:
                conn.executemany(
                    "INSERT OR IGNORE INTO lost_followers (username, timestamp) VALUES (?, ?)",
                    [(username, isoformat(now)) for username in lost_users],
                )

        for username in new_users + lost_users:
            ensure_user_cache(conn, username, allow_fetch=True)

        record_sync_run(
            conn,
            status="success",
            timestamp=now,
            follower_count=current_count,
            new_count=len(new_users),
            lost_count=len(lost_users),
        )
        conn.commit()
    except Exception as exc:
        if conn is not None:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
            try:
                record_sync_run(conn, status="failure", timestamp=now, error=str(exc))
                conn.commit()
            except sqlite3.Error:
                pass
        raise
    finally:
        if conn is not None:
            conn.close()


def load_trends(conn: sqlite3.Connection) -> Trends:
    rows = conn.execute("SELECT timestamp, count FROM followers ORDER BY timestamp").fetchall()
    labels: list[datetime] = []
    history: list[int] = []
    for row in rows:
        parsed = parse_datetime(row["timestamp"])
        if parsed is None:
            continue
        labels.append(parsed)
        history.append(int(row["count"]))
    return Trends(
        labels=labels,
        history=history,
    )


def load_changes(
    conn: sqlite3.Connection,
    table: str,
    *,
    since: datetime | None = None,
) -> list[sqlite3.Row]:
    if table not in CHANGE_TABLES:
        raise ValueError(f"Unsupported change table: {table}")

    query = f"SELECT username, timestamp FROM {table}"
    params: tuple[Any, ...] = ()
    if since is not None:
        query += " WHERE timestamp >= ?"
        params = (isoformat(since),)
    query += " ORDER BY timestamp DESC"
    return conn.execute(query, params).fetchall()


def score_user(row: sqlite3.Row | None) -> tuple[float, str]:
    if row is None:
        return 0.0, "Emerging"

    followers = int(row["followers"] or 0)
    repos = int(row["public_repos"] or 0)
    created_at = parse_datetime(row["created_at"])
    account_age_days = (utcnow() - created_at).days if created_at else 0
    score = 0.0
    score += min(followers, 500) / 8
    score += min(repos, 80) * 0.75
    score += min(account_age_days / 365, 10) * 3
    score += 5 if row["bio"] else 0
    score += 4 if row["company"] else 0
    score += 3 if row["location"] else 0
    score = round(min(score, 100.0), 1)

    if score >= 70:
        label = "High-signal"
    elif score >= 45:
        label = "Notable"
    else:
        label = "Emerging"
    return score, label


def enrich_change_rows(
    conn: sqlite3.Connection,
    rows: list[sqlite3.Row],
    *,
    allow_fetch: bool,
) -> list[EnrichedChange]:
    enriched: list[EnrichedChange] = []
    seen_fetches = 0
    cache: dict[str, sqlite3.Row | None] = {}

    for row in rows:
        username = row["username"]
        if username not in cache:
            can_fetch = allow_fetch and seen_fetches < 24
            cache[username] = ensure_user_cache(conn, username, allow_fetch=can_fetch)
            if can_fetch:
                seen_fetches += 1
        user_row = cache[username]
        score, label = score_user(user_row)
        created_at = parse_datetime(user_row["created_at"]) if user_row else None
        enriched.append(
            EnrichedChange(
                username=username,
                timestamp=parse_datetime(row["timestamp"]) or utcnow(),
                name=user_row["name"] if user_row else None,
                avatar_url=user_row["avatar_url"] if user_row else None,
                html_url=user_row["html_url"] if user_row and user_row["html_url"] else f"https://github.com/{username}",
                bio=user_row["bio"] if user_row else None,
                public_repos=int(user_row["public_repos"] or 0) if user_row else 0,
                followers=int(user_row["followers"] or 0) if user_row else 0,
                following=int(user_row["following"] or 0) if user_row else 0,
                company=user_row["company"] if user_row else None,
                location=user_row["location"] if user_row else None,
                created_at=created_at,
                signal_score=score,
                signal_label=label,
            )
        )

    return enriched


def has_cached_dashboard_data() -> bool:
    conn = get_connection()
    try:
        trends = load_trends(conn)
        if trends.labels:
            return True
        cached_profile = load_cached_profile_row(conn, USERNAME or "")
        return cached_profile is not None
    finally:
        conn.close()


def trend_change_for_window(trends: Trends, days: int) -> int:
    if not trends.labels or not trends.history:
        return 0

    latest_time = trends.labels[-1]
    cutoff = latest_time - timedelta(days=days)
    baseline = trends.history[0]
    for timestamp, count in zip(trends.labels, trends.history):
        if timestamp >= cutoff:
            baseline = count
            break
    return trends.history[-1] - baseline


def cadence_minutes(trends: Trends) -> tuple[int | None, int]:
    if len(trends.labels) < 2:
        return None, 0

    deltas = [
        int((current - previous).total_seconds() // 60)
        for previous, current in zip(trends.labels, trends.labels[1:])
        if current > previous
    ]
    if not deltas:
        return None, 0

    expected = max(1, int(median(deltas)))
    missed = 0
    for delta in deltas:
        if delta > expected * 2:
            missed += max(0, round(delta / expected) - 1)
    return expected, missed


def compute_metrics(
    profile: GitHubProfile,
    trends: Trends,
    new_24h_count: int,
    lost_24h_count: int,
    all_new_count: int,
    all_lost_count: int,
) -> DashboardMetrics:
    daily_changes = [
        trends.history[index] - trends.history[index - 1]
        for index in range(1, len(trends.history))
    ]
    average_daily_growth = round(mean(daily_changes), 2) if daily_changes else 0.0
    volatility = pstdev(daily_changes) if len(daily_changes) > 1 else 0.0
    volatility_score = round(min(100.0, volatility * 18), 1)
    stability_score = round(max(0.0, 100.0 - volatility_score), 1)
    churn_rate = round((all_lost_count / max(profile.followers, 1)) * 100, 2)

    return DashboardMetrics(
        total_followers=profile.followers,
        following=profile.following,
        net_24h=new_24h_count - lost_24h_count,
        net_7d=trend_change_for_window(trends, 7),
        net_30d=trend_change_for_window(trends, 30),
        average_daily_growth=average_daily_growth,
        churn_rate=churn_rate,
        volatility_score=volatility_score,
        stability_score=stability_score,
        snapshot_count=len(trends.history),
        change_records_30d=all_new_count + all_lost_count,
    )


def compute_health(
    conn: sqlite3.Connection,
    trends: Trends,
    *,
    partial_data: bool,
    last_error_override: str | None = None,
) -> DashboardHealth:
    success_row = conn.execute(
        "SELECT timestamp FROM sync_runs WHERE status = 'success' ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    failure_row = conn.execute(
        "SELECT timestamp, error FROM sync_runs WHERE status = 'failure' ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()

    last_success = parse_datetime(success_row["timestamp"]) if success_row else None
    last_failure = parse_datetime(failure_row["timestamp"]) if failure_row else None
    expected_cadence, missed_snapshots = cadence_minutes(trends)
    freshness_minutes = None
    stale = False

    if trends.labels:
        freshness_minutes = int((utcnow() - trends.labels[-1]).total_seconds() // 60)
        threshold = expected_cadence * 3 if expected_cadence else 720
        stale = freshness_minutes > max(threshold, 90)

    last_error = last_error_override or (failure_row["error"] if failure_row else None)
    if not trends.labels and last_error:
        api_status = "error"
    elif partial_data or stale or last_error:
        api_status = "degraded"
    else:
        api_status = "healthy"

    return DashboardHealth(
        api_status=api_status,
        partial_data=partial_data,
        stale_data=stale,
        last_successful_sync=last_success,
        last_failed_sync=last_failure,
        last_error=last_error,
        snapshot_count=len(trends.history),
        expected_cadence_minutes=expected_cadence,
        missed_snapshots=missed_snapshots,
        data_freshness_minutes=freshness_minutes,
    )


def build_annotations(
    trends: Trends,
    new_24h_count: int,
    lost_24h_count: int,
) -> list[ChartAnnotation]:
    annotations: list[ChartAnnotation] = []
    if not trends.labels or not trends.history:
        return annotations

    peak_value = max(trends.history)
    low_value = min(trends.history)
    peak_index = max(index for index, value in enumerate(trends.history) if value == peak_value)
    low_index = max(index for index, value in enumerate(trends.history) if value == low_value)

    annotations.append(
        ChartAnnotation(
            timestamp=trends.labels[peak_index],
            kind="peak",
            label="Peak audience",
            value=peak_value,
            magnitude=0,
        )
    )
    annotations.append(
        ChartAnnotation(
            timestamp=trends.labels[low_index],
            kind="low",
            label="Low point",
            value=low_value,
            magnitude=0,
        )
    )

    if len(trends.history) > 1:
        deltas = [trends.history[index] - trends.history[index - 1] for index in range(1, len(trends.history))]
        max_delta = max(deltas)
        min_delta = min(deltas)

        if max_delta > 0:
            spike_index = deltas.index(max_delta) + 1
            annotations.append(
                ChartAnnotation(
                    timestamp=trends.labels[spike_index],
                    kind="spike",
                    label="Biggest spike",
                    value=trends.history[spike_index],
                    magnitude=max_delta,
                )
            )
        if min_delta < 0:
            dip_index = deltas.index(min_delta) + 1
            annotations.append(
                ChartAnnotation(
                    timestamp=trends.labels[dip_index],
                    kind="dip",
                    label="Largest drop",
                    value=trends.history[dip_index],
                    magnitude=abs(min_delta),
                )
            )

    latest_timestamp = trends.labels[-1]
    latest_value = trends.history[-1]
    if new_24h_count > 0:
        annotations.append(
            ChartAnnotation(
                timestamp=latest_timestamp,
                kind="gain",
                label=f"{new_24h_count} gains in 24h",
                value=latest_value,
                magnitude=new_24h_count,
            )
        )
    if lost_24h_count > 0:
        annotations.append(
            ChartAnnotation(
                timestamp=latest_timestamp,
                kind="loss",
                label=f"{lost_24h_count} losses in 24h",
                value=latest_value,
                magnitude=lost_24h_count,
            )
        )

    return annotations


def fallback_profile(conn: sqlite3.Connection, trends: Trends) -> GitHubProfile:
    cached = load_cached_profile_row(conn, USERNAME or "")
    if cached:
        return profile_from_row(cached, USERNAME)

    latest_count = trends.history[-1] if trends.history else 0
    username = USERNAME or "unknown"
    return GitHubProfile(
        username=username,
        html_url=f"https://github.com/{username}",
        followers=latest_count,
    )


def get_dashboard_data(*, refresh: bool = False) -> DashboardData:
    initialize_tracker_db()

    partial_data = False
    last_error = None

    should_sync = refresh or not has_cached_dashboard_data()
    if should_sync:
        try:
            sync_followers(force=refresh)
        except Exception as exc:
            partial_data = True
            last_error = str(exc)

    conn = get_connection()
    try:
        trends = load_trends(conn)
        profile = fallback_profile(conn, trends)
        recent_cutoff = utcnow() - timedelta(hours=RECENT_WINDOW_HOURS)
        history_cutoff = utcnow() - timedelta(days=FULL_HISTORY_DAYS)

        recent_new_rows = load_changes(conn, "new_followers", since=recent_cutoff)
        recent_lost_rows = load_changes(conn, "lost_followers", since=recent_cutoff)
        all_new_rows = load_changes(conn, "new_followers", since=history_cutoff)
        all_lost_rows = load_changes(conn, "lost_followers", since=history_cutoff)

        recent_new = enrich_change_rows(conn, recent_new_rows, allow_fetch=refresh)
        recent_lost = enrich_change_rows(conn, recent_lost_rows, allow_fetch=refresh)
        all_new = enrich_change_rows(conn, all_new_rows, allow_fetch=refresh)
        all_lost = enrich_change_rows(conn, all_lost_rows, allow_fetch=refresh)

        if refresh:
            conn.commit()

        high_signal_new = sorted(
            all_new,
            key=lambda item: (item.signal_score, item.followers, item.public_repos),
            reverse=True,
        )[:5]

        stats = Stats(
            total_followers=profile.followers or (trends.history[-1] if trends.history else 0),
            new_followers=len(recent_new),
            unfollowers=len(recent_lost),
            net_change=len(recent_new) - len(recent_lost),
        )
        metrics = compute_metrics(
            profile,
            trends,
            len(recent_new),
            len(recent_lost),
            len(all_new),
            len(all_lost),
        )
        health = compute_health(conn, trends, partial_data=partial_data, last_error_override=last_error)
        annotations = build_annotations(trends, len(recent_new), len(recent_lost))

        result = DashboardData(
            generated_at=utcnow(),
            profile=profile,
            stats=stats,
            metrics=metrics,
            trends=trends,
            health=health,
            recent_new_followers=recent_new,
            recent_lost_followers=recent_lost,
            all_new_followers=all_new,
            all_lost_followers=all_lost,
            high_signal_new_followers=high_signal_new,
            annotations=annotations,
        )
        return result
    finally:
        conn.close()


def get_follower_stats(*, refresh: bool = False) -> Stats:
    return get_dashboard_data(refresh=refresh).stats


def get_github_profile(*, refresh: bool = False) -> GitHubProfile:
    return get_dashboard_data(refresh=refresh).profile


def get_follower_trends(*, refresh: bool = False) -> Trends:
    return get_dashboard_data(refresh=refresh).trends


def get_change_history(change_type: str, *, days: int = FULL_HISTORY_DAYS, refresh: bool = False) -> list[Change]:
    if change_type == "new":
        table = "new_followers"
    elif change_type == "lost":
        table = "lost_followers"
    else:
        raise ValueError("change_type must be 'new' or 'lost'")

    sync_followers(force=refresh)
    since = utcnow() - timedelta(days=days)

    conn = get_connection()
    try:
        rows = load_changes(conn, table, since=since)
        return [
            Change(
                username=row["username"],
                timestamp=parse_datetime(row["timestamp"]) or utcnow(),
            )
            for row in rows
        ]
    finally:
        conn.close()
