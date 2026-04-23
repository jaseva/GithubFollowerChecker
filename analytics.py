import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime


def create_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS followers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unfollowers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()


def insert_follower(conn, username, timestamp):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO followers (username, timestamp)
        VALUES (?, ?)
    ''', (username, timestamp))
    conn.commit()


def plot_follower_growth(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, COUNT(DISTINCT username) FROM followers GROUP BY timestamp ORDER BY timestamp")
    data = cursor.fetchall()

    if not data:
        print("No follower data available.")
        return

    timestamps = [datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S') for row in data]
    date_values = mdates.date2num(timestamps)
    counts = [row[1] for row in data]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(date_values, counts, marker='o')
    ax.set_title("Follower Growth Over Time")
    ax.set_xlabel("Time")
    ax.set_ylabel("Number of Followers")
    ax.xaxis_date()
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.show()


def segment_followers(followers, segmentation_type):
    segments = {}
    if segmentation_type == "activity":
        segments['active'] = [user for user in followers if len(user) >= 5]
        segments['less_active'] = [user for user in followers if len(user) < 5]
    elif segmentation_type == "repo":
        midpoint = len(followers) // 2
        segments['repo_owners'] = followers[:midpoint]
        segments['contributors'] = followers[midpoint:]
    return segments


def plot_unfollower_trend(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, COUNT(DISTINCT username) FROM unfollowers GROUP BY timestamp ORDER BY timestamp")
    data = cursor.fetchall()

    if not data:
        print("No unfollower data available.")
        return

    timestamps = [datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S') for row in data]
    date_values = mdates.date2num(timestamps)
    counts = [row[1] for row in data]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(date_values, counts, marker='o', linestyle='-', color='red', label='Unfollowers Over Time')
    ax.set_title("Unfollower Trends Over Time")
    ax.set_xlabel("Time")
    ax.set_ylabel("Number of Unfollowers")
    ax.legend()
    ax.xaxis_date()
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.show()
