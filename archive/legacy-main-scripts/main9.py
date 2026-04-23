# main.py
# MIT License
# Created Date: 2024-09-02
# Created By: Jason Evans
# Version 1.1.1.2

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, Menu
import threading
import os
import json
import sqlite3
from datetime import datetime
import requests
from analytics import create_table, insert_follower, plot_follower_growth, segment_followers
from dev.prototype.utils import get_all_followers, format_list
from openai import OpenAI
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()

def create_summary_table(conn):
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS profile_summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        profile_description TEXT,
                        repos_contributed_to TEXT,
                        summary TEXT,
                        date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')
    conn.commit()

def track_followers(username, token, followers_file):
    try:
        conn = sqlite3.connect('follower_data.db')
        create_table(conn)

        if os.path.exists(followers_file):
            with open(followers_file, 'r') as f:
                follower_data = json.load(f)
                previous_followers = follower_data.get('followers', [])
                follower_history = follower_data.get('history', {})
        else:
            previous_followers = []
            follower_history = {}

        followers_url = f'https://api.github.com/users/{username}/followers'
        following_url = f'https://api.github.com/users/{username}/following'
        current_followers = get_all_followers(username, token, followers_url)
        current_followings = get_all_followers(username, token, following_url)

        new_followers = list(set(current_followers) - set(previous_followers))
        unfollowers = list(set(previous_followers) - set(current_followers))
        followers_back = list(set(current_followers) & set(current_followings))  
        not_following_back = list(set(current_followings) - set(current_followers))

        today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        follower_history[today] = len(current_followers)

        for follower in current_followers:
            insert_follower(conn, follower, today)

        follower_text.config(state=tk.NORMAL)
        follower_text.delete(1.0, tk.END)

        formatted_new, color_new = format_list("New followers", new_followers, "green")
        follower_text.insert(tk.END, formatted_new, "new_followers")

        formatted_unf, color_unf = format_list("Unfollowers", unfollowers, "red")
        follower_text.insert(tk.END, formatted_unf, "unfollowers")

        formatted_back, color_back = format_list("Followers who follow back", followers_back, "blue")
        follower_text.insert(tk.END, formatted_back, "followers_back")

        formatted_not_back, color_not_back = format_list("Users you follow who don't follow back", not_following_back, "orange")
        follower_text.insert(tk.END, formatted_not_back, "not_following_back")

        follower_text.tag_config("new_followers", foreground=color_new)
        follower_text.tag_config("unfollowers", foreground=color_unf)
        follower_text.tag_config("followers_back", foreground=color_back)
        follower_text.tag_config("not_following_back", foreground=color_not_back)

        follower_text.config(state=tk.DISABLED)

        with open(followers_file, 'w') as f:
            json.dump({'followers': current_followers, 'history': follower_history}, f, indent=4)

        show_analytics_button.config(state=tk.NORMAL)
        segment_followers_button.config(state=tk.NORMAL)
        summary_button.config(state=tk.NORMAL)

        conn.close()

    except Exception as e:
        messagebox.showerror("Error", str(e))
    switch_tab(notebook, 0)

def start_tracking():
    username = username_entry.get().strip()
    token = token_entry.get().strip()
    followers_file = followers_file_entry.get().strip()

    if not username or not token or not followers_file:
        messagebox.showwarning("Input Error", "Please fill in all fields.")
        return

    threading.Thread(target=track_followers, args=(username, token, followers_file)).start()
    summary_button.config(state=tk.NORMAL)

def show_analytics():
    try:
        conn = sqlite3.connect('follower_data.db')
        plot_follower_growth(conn)
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", str(e))
    switch_tab(notebook, 0)

def segment_followers_ui():
    username = username_entry.get().strip()
    token = token_entry.get().strip()
    followers_file = followers_file_entry.get().strip()
    segmentation_type = segmentation_type_var.get()

    if not username or not token or not followers_file:
        messagebox.showwarning("Input Error", "Please fill in all fields.")
        return

    try:
        with open(followers_file, 'r') as f:
            follower_data = json.load(f)
            followers = follower_data['followers']

        segments = segment_followers(followers, segmentation_type)

        follower_text.config(state=tk.NORMAL)
        follower_text.delete(1.0, tk.END)

        for segment, members in segments.items():
            formatted_segment, color_segment = format_list(segment, members, "blue")
            follower_text.insert(tk.END, formatted_segment, "segment")

        follower_text.tag_config("segment", foreground="blue")
        follower_text.config(state=tk.DISABLED)

    except Exception as e:
        messagebox.showerror("Error", str(e))
    switch_tab(notebook, 0)  # Switch to "Followers" tab after generating summary

def generate_summary(username, token):
    try:
        client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

        headers = {'Authorization': f'token {token}'}
        profile_url = f'https://api.github.com/users/{username}'
        repos_url = f'https://api.github.com/users/{username}/repos'

        profile_response = requests.get(profile_url, headers=headers)
        repos_response = requests.get(repos_url, headers=headers)
        
        profile_response.raise_for_status()
        repos_response.raise_for_status()

        profile_data = profile_response.json()
        repos_data = repos_response.json()

        profile_description = profile_data.get('bio', 'No bio available')
        repos_contributed_to = [repo['name'] for repo in repos_data if isinstance(repo, dict)]

        prompt = (f"User {username} has the following bio: {profile_description}. "
                 f"They have contributed to the following repositories: {', '.join(repos_contributed_to)}. "
                 "Summarize the user's profile and contributions. Identify the sentiment & tone of the individual.")

        completion = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Write a summary from this user's GitHub profile."}
            ]
        )

        summary = completion.choices[0].message.content.strip()
        return summary, profile_description, repos_contributed_to

    except Exception as e:
        messagebox.showerror("Error", str(e))
        return None, None, None

def save_summary_to_db(username, summary, profile_description, repos_contributed_to):
    try:
        conn = sqlite3.connect('follower_data.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO profile_summaries (username, profile_description, repos_contributed_to, summary) VALUES (?, ?, ?, ?)",
                       (username, profile_description, ', '.join(repos_contributed_to), summary))
        conn.commit()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", str(e))

def show_summary():
    username = username_entry.get().strip()
    token = token_entry.get().strip()

    if not username or not token:
        messagebox.showwarning("Input Error", "Please fill in all fields.")
        return

    summary, profile_description, repos_contributed_to = generate_summary(username, token)

    if summary:
        summary_text.config(state=tk.NORMAL)
        summary_text.delete(1.0, tk.END)
        summary_text.insert(tk.END, f"Username: {username}\n\n")
        summary_text.insert(tk.END, f"Profile Description: {profile_description}\n\n")
        summary_text.insert(tk.END, f"Repositories Contributed To: {', '.join(repos_contributed_to)}\n\n")
        summary_text.insert(tk.END, f"Summary:\n{summary}\n")
        summary_text.config(state=tk.DISABLED)

        save_summary_to_db(username, summary, profile_description, repos_contributed_to)

    switch_tab(notebook, 1)

def switch_tab(notebook, tab_index):
    notebook.select(tab_index)

def set_theme(theme):
    if theme == "light":
        root.configure(bg="white")
        style.configure('TLabel', background="white", foreground="black")
        follower_text.configure(bg="white", fg="black")
    elif theme == "dark":
        root.configure(bg="black")
        style.configure('TLabel', background="black", foreground="white")
        follower_text.configure(bg="black", fg="white")
    elif theme == "solarized_light":
        root.configure(bg="#FDF6E3")
        style.configure('TLabel', background="#FDF6E3", foreground="#657B83")
        follower_text.configure(bg="#FDF6E3", fg="#657B83")
    elif theme == "custom":
        root.configure(bg="#2E3440")  # replace with your custom color
        style.configure('TLabel', background="#2E3440", foreground="#2E3440")  # replace with your custom color
        follower_text.configure(bg="#2E3440", fg="#2E3440")
    else:
        root.configure(bg="default_color_bg")
        style.configure('TLabel', background="default_color_bg", foreground="default_color_fg")
        follower_text.configure(bg="default_color_bg", fg="default_color_fg")

# UI Setup
root = tk.Tk()
root.title("GitHub Follower Tracker")
root.geometry("800x600")

# Create a style object
style = ttk.Style(root)

# Notebook for Tabs
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill="both")

# Tab 1: Follower Data
tab1 = ttk.Frame(notebook)
notebook.add(tab1, text="Follower Data")

# Tab 2: Profile Summary
tab2 = ttk.Frame(notebook)
notebook.add(tab2, text="Profile Summary")

# Frame for User Inputs
input_frame = ttk.Frame(tab1)
input_frame.pack(pady=10, padx=10, fill="x")

username_label = ttk.Label(input_frame, text="GitHub Username:")
username_label.grid(row=0, column=0, sticky="e")
username_entry = ttk.Entry(input_frame)
username_entry.grid(row=0, column=1, padx=5, pady=5)

token_label = ttk.Label(input_frame, text="GitHub Token:")
token_label.grid(row=1, column=0, sticky="e")
token_entry = ttk.Entry(input_frame, show="*")
token_entry.grid(row=1, column=1, padx=5, pady=5)

followers_file_label = ttk.Label(input_frame, text="Followers File:")
followers_file_label.grid(row=2, column=0, sticky="e")
followers_file_entry = ttk.Entry(input_frame)
followers_file_entry.grid(row=2, column=1, padx=5, pady=5)

start_button = ttk.Button(input_frame, text="Start Tracking", command=start_tracking)
start_button.grid(row=3, column=1, padx=5, pady=10)

# Frame for Follower Text Output
follower_text = scrolledtext.ScrolledText(tab1, wrap=tk.WORD, height=15, state=tk.DISABLED)
follower_text.pack(pady=10, padx=10, fill="both", expand=True)

# Analytics Button
show_analytics_button = ttk.Button(tab1, text="Show Analytics", command=show_analytics, state=tk.DISABLED)
show_analytics_button.pack(side=tk.LEFT, padx=10, pady=10)

# Create the segmentation type variable with a default read-only label "Please Select"
segmentation_type_var = tk.StringVar(value="Please Select")

# Label for Segmentation
segmentation_label = tk.Label(tab1, text="Segment By:")
segmentation_label.pack(side=tk.LEFT, padx=10, pady=10)

# Dropdown menu for Segmentation Types
segmentation_menu = tk.OptionMenu(tab1, segmentation_type_var, "repo", "activity")
segmentation_menu.pack(side=tk.LEFT, padx=10, pady=10)

# Segment followers button
segment_followers_button = tk.Button(tab1, text="Segment Followers", command=segment_followers_ui, state=tk.DISABLED)
# segment_followers_button.pack(anchor="w", pady=5)
segment_followers_button.pack(side=tk.LEFT, padx=10, pady=10)

# Generate Summary Button
summary_button = ttk.Button(tab1, text="Generate Summary", command=show_summary, state=tk.DISABLED)
summary_button.pack(side=tk.LEFT, padx=10, pady=10)

# Frame for Summary Text Output
summary_text = scrolledtext.ScrolledText(tab2, wrap=tk.WORD, height=15, state=tk.DISABLED)
summary_text.pack(pady=10, padx=10, fill="both", expand=True)

# Menu Bar for Theme Selection
menu_bar = Menu(root)
root.config(menu=menu_bar)

# Theme Menu
theme_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Settings", menu=theme_menu)

theme_menu.add_command(label="Light Theme", command=lambda: set_theme("light"))
theme_menu.add_command(label="Dark Theme", command=lambda: set_theme("dark"))
theme_menu.add_command(label="Solarized Light Theme", command=lambda: set_theme("solarized_light"))
theme_menu.add_command(label="Custom Theme", command=lambda: set_theme("custom"))

# Main Loop
root.mainloop()