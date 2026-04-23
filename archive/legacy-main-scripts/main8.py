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
    switch_tab(notebook, 0)

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
        return None

def generate_summary_wrapper():
    username = profile_entry.get().strip()
    token = token_entry.get().strip()
    if not username or not token:
        messagebox.showwarning("Input Error", "Please enter username and token.")
        return
    summary, profile_description, repos_contributed_to = generate_summary(username, token)

    if summary:
        try:
            conn = sqlite3.connect('follower_data.db')
            create_summary_table(conn)
            cursor = conn.cursor()

            cursor.execute('''INSERT INTO profile_summaries (username, profile_description, repos_contributed_to, summary)
                              VALUES (?, ?, ?, ?)''',
                           (username, profile_description, ", ".join(repos_contributed_to), summary))
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", str(e))

        summary_text.config(state=tk.NORMAL)
        summary_text.delete(1.0, tk.END)
        summary_text.insert(tk.END, f"Summary: {summary}", "summary")
        summary_text.tag_config("summary", foreground="black")
        summary_text.config(state=tk.DISABLED)

        switch_tab(notebook, 1)

def switch_tab(notebook, index):
    global selected_tab
    notebook.select(index)
    selected_tab = index

themes = {
    "Default": {
        "background": "SystemButtonFace",
        "foreground": "black",
        "button_bg": "SystemButtonFace",
        "button_fg": "black",
        "tab_bg": "SystemButtonFace",
        "tab_fg": "black",
    },
    "Solarized Light": {
        "background": "#fdf6e3",
        "foreground": "#657b83",
        "button_bg": "#eee8d5",
        "button_fg": "#586e75",
        "tab_bg": "#eee8d5",
        "tab_fg": "#586e75",
    },
    "Solarized Dark": {
        "background": "#002b36",
        "foreground": "#839496",
        "button_bg": "#073642",
        "button_fg": "#839496",
        "tab_bg": "#073642",
        "tab_fg": "#93a1a1",
    },
    "Material": {
        "background": "#263238",
        "foreground": "#FFFFFF",
        "button_bg": "#546e7a",
        "button_fg": "#FFFFFF",
        "tab_bg": "#37474f",
        "tab_fg": "#FFFFFF",
    },
}

def apply_theme(theme_name):
    theme = themes.get(theme_name, themes["Default"])
    root.configure(bg=theme["background"])
    username_label.config(bg=theme["background"], fg=theme["foreground"])
    token_label.config(bg=theme["background"], fg=theme["foreground"])
    followers_file_label.config(bg=theme["background"], fg=theme["foreground"])
    profile_label.config(bg=theme["background"], fg=theme["foreground"])
    segmentation_label.config(bg=theme["background"], fg=theme["foreground"])
    follower_text.config(bg=theme["background"], fg=theme["foreground"])
    summary_text.config(bg=theme["background"], fg=theme["foreground"])
    start_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
    show_analytics_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
    segment_followers_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
    summary_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
    # theme_menu_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
    notebook.config(bg=theme["tab_bg"], fg=theme["tab_fg"])

root = tk.Tk()
root.title("GitHub Follower Tracker")
root.geometry("950x650")
root.state('zoomed')  # Maximizes the window
root.option_add('*tearOff', False)

theme_var = tk.StringVar()
selected_tab = 0

menu_bar = Menu(root)
root.config(menu=menu_bar)

file_menu = Menu(menu_bar)
menu_bar.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="Exit", command=root.quit)

theme_menu = Menu(menu_bar)
menu_bar.add_cascade(label="Theme", menu=theme_menu)

for theme_name in themes:
    theme_menu.add_radiobutton(label=theme_name, variable=theme_var, command=lambda: apply_theme(theme_var.get()))

notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

# Followers tab
followers_frame = ttk.Frame(notebook)
followers_frame.pack(fill='both', expand=True)
notebook.add(followers_frame, text="Follower Data")

summary_frame = ttk.Frame(notebook)
summary_frame.pack(fill='both', expand=True)
notebook.add(summary_frame, text="Profile Summary")

username_label = ttk.Label(followers_frame, text="GitHub Username:")
username_label.pack(pady=5)
username_entry = ttk.Entry(followers_frame)
username_entry.pack(pady=5)

token_label = ttk.Label(followers_frame, text="GitHub Token:")
token_label.pack(pady=5)
token_entry = ttk.Entry(followers_frame, show='*')
token_entry.pack(pady=5)

followers_file_label = ttk.Label(followers_frame, text="Followers File Path:")
followers_file_label.pack(pady=5)
followers_file_entry = ttk.Entry(followers_frame)
followers_file_entry.pack(pady=5)

start_button = ttk.Button(followers_frame, text="Start Tracking", command=start_tracking)
start_button.pack(pady=5)

show_analytics_button = ttk.Button(followers_frame, text="Show Analytics", command=show_analytics)
show_analytics_button.pack(pady=5)

segmentation_label = ttk.Label(followers_frame, text="Segmentation Type:")
segmentation_label.pack(pady=5)

segmentation_type_var = tk.StringVar(followers_frame)
segmentation_type_var.set("Please Select")

segmentation_type_dropdown = ttk.OptionMenu(followers_frame, segmentation_type_var, "Please Select", "Repo", "Activity")
segmentation_type_dropdown.pack(pady=5)

segment_followers_button = ttk.Button(followers_frame, text="Segment Followers", command=segment_followers_ui)
segment_followers_button.pack(pady=5)

follower_text = scrolledtext.ScrolledText(followers_frame, wrap=tk.WORD, height=15)
follower_text.pack(pady=10)
follower_text.config(state=tk.DISABLED)

profile_label = ttk.Label(summary_frame, text="GitHub Username:")
profile_label.pack(pady=5)
profile_entry = ttk.Entry(summary_frame)
profile_entry.pack(pady=5)

summary_button = ttk.Button(summary_frame, text="Generate Summary", command=generate_summary_wrapper)
summary_button.pack(pady=5)

summary_text = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, height=15)
summary_text.pack(pady=10)
summary_text.config(state=tk.DISABLED)

theme_menu_button = ttk.Label(followers_frame, text="Theme Menu", command=apply_theme(theme_menu))

apply_theme("Default")

root.mainloop()