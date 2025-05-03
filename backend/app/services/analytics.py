## analytics.py
## MIT License
## Created Date: 2024-09-01
## Modified Date: 2025-01-29
## Version 1.1.0

import sqlite3
import matplotlib.pyplot as plt
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

 # New table for tracking unfollowers
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

    timestamps = [datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S') for row in data]
    counts = [row[1] for row in data]

    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, counts, marker='o')
    plt.title("Follower Growth Over Time")
    plt.xlabel("Time")
    plt.ylabel("Number of Followers")
    plt.gcf().autofmt_xdate()  # Rotate and align the tick labels
    plt.tight_layout()
    plt.show()

def segment_followers(followers, segmentation_type):
    segments = {}
    if segmentation_type == "activity":
        segments['active'] = [user for user in followers if len(user) >= 5]
        segments['less_active'] = [user for user in followers if len(user) < 5]
    elif segmentation_type == "repo":
        # This is a placeholder. In a real scenario, you'd need to fetch repository data for each follower.
        segments['repo_owners'] = followers[:len(followers)//2]
        segments['contributors'] = followers[len(followers)//2:]
    return segments

def plot_unfollower_trend(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, COUNT(DISTINCT username) FROM unfollowers GROUP BY timestamp ORDER BY timestamp")
    data = cursor.fetchall()

    if not data:
        print("No unfollower data available.")
        return

    timestamps = [datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S') for row in data]
    counts = [row[1] for row in data]

    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, counts, marker='o', linestyle='-', color='red', label="Unfollowers Over Time")
    plt.title("Unfollower Trends Over Time")
    plt.xlabel("Time")
    plt.ylabel("Number of Unfollowers")
    plt.legend()
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.show()
