# main.py
# MIT License
# Created Date: 2024-09-02
# Version 1.1.2
# Dark Theme

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
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

# Function to track followers
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
        current_followers = get_all_followers(username, token, followers_url)

        new_followers = list(set(current_followers) - set(previous_followers))
        unfollowers = list(set(previous_followers) - set(current_followers))
        followers_back = list(set(previous_followers) & set(current_followers))  

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

        formatted_back, color_back = format_list("Followers who followed back", followers_back, "blue")
        follower_text.insert(tk.END, formatted_back, "followers_back")

        follower_text.tag_config("new_followers", foreground=color_new)
        follower_text.tag_config("unfollowers", foreground=color_unf)
        follower_text.tag_config("followers_back", foreground=color_back)

        follower_text.config(state=tk.DISABLED)

        with open(followers_file, 'w') as f:
            json.dump({'followers': current_followers, 'history': follower_history}, f, indent=4)

        show_analytics_button.config(state=tk.NORMAL)
        segment_followers_button.config(state=tk.NORMAL)
        summary_button.config(state=tk.NORMAL)

        conn.close()

    except Exception as e:
        messagebox.showerror("Error", str(e))
    switch_tab(notebook, 0)  # Switch to "Followers" tab after generating summary

# Function to start tracking in a separate thread
def start_tracking():
    username = username_entry.get().strip()
    token = token_entry.get().strip()
    followers_file = followers_file_entry.get().strip()

    if not username or not token or not followers_file:
        messagebox.showwarning("Input Error", "Please fill in all fields.")
        return

    threading.Thread(target=track_followers, args=(username, token, followers_file)).start()
    summary_button.config(state=tk.NORMAL)  # Enable button after tracking

# Function to show analytics
def show_analytics():
    try:
        conn = sqlite3.connect('follower_data.db')
        plot_follower_growth(conn)
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", str(e))
    switch_tab(notebook, 0)  # Switch to "Followers" tab after generating summary

# Function to segment followers
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

# Function to generate AI summary 
def generate_summary(username, token):
    try:
        # Initialize OpenAI API key
        client = OpenAI(
            api_key=os.environ['OPENAI_API_KEY']
        )

        # Define GitHub API URLs
        headers = {'Authorization': f'token {token}'}
        profile_url = f'https://api.github.com/users/{username}'
        repos_url = f'https://api.github.com/users/{username}/repos'

        # Fetch GitHub profile and repos data
        profile_response = requests.get(profile_url, headers=headers)
        repos_response = requests.get(repos_url, headers=headers)

        # Check for successful API response
        profile_response.raise_for_status()
        repos_response.raise_for_status()

        profile_data = profile_response.json()
        repos_data = repos_response.json()

        # Extract profile information and repos
        profile_description = profile_data.get('bio', 'No bio available')
        repos_contributed_to = [repo['name'] for repo in repos_data if isinstance(repo, dict)]

        # Create prompt for OpenAI API
        prompt = (f"User {username} has the following bio: {profile_description}. "
                 f"They have contributed to the following repositories: {', '.join(repos_contributed_to)}. "
                 "Summarize the user's profile and contributions. Identify the sentiment & tone of the individual.")

        # Make request to OpenAI chat completions
        completion = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": "Write a summary from this user's GitHub profile."
                }
            ]
        )

        # Extract and return summary using object attributes
        summary = completion.choices[0].message.content.strip()
        return summary

    except Exception as e:
        messagebox.showerror("Error", str(e))
        return None

# Function to wrap AI generated summary
def generate_summary_wrapper():
    username = profile_entry.get().strip()
    token = token_entry.get().strip()
    if not username or not token:
        messagebox.showwarning("Input Error", "Please enter username and token.")
        return
    summary = generate_summary(username, token)
    if summary:
        summary_text.config(state=tk.NORMAL)
        summary_text.delete(1.0, tk.END)
        summary_text.insert(tk.END, f"Summary: {summary}", "summary")
        summary_text.tag_config("summary", foreground="white")
        summary_text.config(state=tk.DISABLED)
        # Switch to the Profile Summary tab
        # notebook.select(1)  # Index 1 refers to the "Profile Summary" tab
        switch_tab(notebook, 1)  # Switch to "Profile Summary" tab after generating summary

def switch_tab(notebook, index):
     # Initialize selected_tab here
    selected_tab = 0  # or any default value
    
    notebook.select(index)
    style.configure("TNotebook.Tab{}".format(index), background="blue", foreground="white")
    style.configure("TNotebook.Tab{}".format(selected_tab), background="gray", foreground="white")
    selected_tab = index

# GUI setup
root = tk.Tk()
root.title("GitHub Follower Checker")

# Initialize selected tab
selected_tab = 0

# Configure notebook style
style = ttk.Style()
style.theme_use("default")
style.configure("TNotebook", background="black", foreground="white", tabposition='nw')
style.configure("TNotebook.Tab", background="gray", foreground="white", padding=[10, 10])
style.configure("TFrame", background="black")
style.configure("TLabel", background="black", foreground="white")
style.configure("TEntry", background="gray", foreground="white")
style.configure("TButton", background="darkgray", foreground="black")

# Add notebook to root
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')

# Increase window size to accommodate all elements
root.geometry("1000x800")
root.resizable(True, True)

# Header
header = tk.Label(root, text="GitHub Follower Checker", font=('Helvetica', 18, 'bold'), pady=10, bg='black', fg='white')
header.pack()

# Frame for input fields with columns
input_frame = tk.Frame(root, padx=20, pady=10, bg='black')
input_frame.pack(fill=tk.X)

# Left column for follower tracking
left_column = tk.Frame(input_frame, padx=10, bg='black')
left_column.pack(side=tk.LEFT, fill=tk.Y)

username_label = tk.Label(left_column, text="GitHub Username:", font=('Arial', 12, 'bold'), bg='black', fg='white')
username_label.grid(row=0, column=0, sticky='e', pady=5)

username_entry = tk.Entry(left_column, font=('Arial', 12), bg='gray', fg='white')
username_entry.grid(row=0, column=1, pady=5)

token_label = tk.Label(left_column, text="GitHub Token:", font=('Arial', 12, 'bold'), bg='black', fg='white')
token_label.grid(row=1, column=0, sticky='e', pady=5)

token_entry = tk.Entry(left_column, font=('Arial', 12), bg='gray', fg='white', show="*")
token_entry.grid(row=1, column=1, pady=5)

followers_file_label = tk.Label(left_column, text="Followers File:", font=('Arial', 12, 'bold'), bg='black', fg='white')
followers_file_label.grid(row=2, column=0, sticky='e', pady=5)

followers_file_entry = tk.Entry(left_column, font=('Arial', 12), bg='gray', fg='white')
followers_file_entry.grid(row=2, column=1, pady=5)

track_button = tk.Button(left_column, text="Track Followers", font=('Arial', 12, 'bold'), bg='darkgray', fg='black', command=start_tracking)
track_button.grid(row=3, column=0, columnspan=2, pady=10)

show_analytics_button = tk.Button(left_column, text="Show Analytics", font=('Arial', 12, 'bold'), bg='darkgray', fg='black', command=show_analytics, state=tk.DISABLED)
show_analytics_button.grid(row=4, column=0, columnspan=2, pady=10)

segment_followers_button = tk.Button(left_column, text="Segment Followers", font=('Arial', 12, 'bold'), bg='darkgray', fg='black', command=segment_followers_ui, state=tk.DISABLED)
segment_followers_button.grid(row=5, column=0, columnspan=2, pady=10)

# Dropdown for segmentation type
segmentation_type_var = tk.StringVar(left_column)
segmentation_type_var.set("Please Select")

segmentation_label = tk.Label(left_column, text="Segmentation Type:", font=('Arial', 12, 'bold'), bg='black', fg='white')
segmentation_label.grid(row=6, column=0, sticky='e', pady=5)

segmentation_dropdown = tk.OptionMenu(left_column, segmentation_type_var, "repo", "activity", "location", "company")
segmentation_dropdown.config(font=('Arial', 12), bg='gray', fg='white')
segmentation_dropdown.grid(row=6, column=1, pady=5)

# Right column for profile summary
right_column = tk.Frame(input_frame, padx=10, bg='black')
right_column.pack(side=tk.RIGHT, fill=tk.Y)

profile_label = tk.Label(right_column, text="Profile Username:", font=('Arial', 12, 'bold'), bg='black', fg='white')
profile_label.grid(row=0, column=0, sticky='e', pady=5)

profile_entry = tk.Entry(right_column, font=('Arial', 12), bg='gray', fg='white')
profile_entry.grid(row=0, column=1, pady=5)

summary_button = tk.Button(right_column, text="Generate Summary", font=('Arial', 12, 'bold'), bg='darkgray', fg='black', command=generate_summary_wrapper, state=tk.DISABLED)
summary_button.grid(row=1, column=0, columnspan=2, pady=10)

# Followers Tab
followers_tab = ttk.Frame(notebook)
notebook.add(followers_tab, text="Followers")

follower_text = scrolledtext.ScrolledText(followers_tab, wrap=tk.WORD, font=('Arial', 12), bg='gray', fg='white')
follower_text.pack(expand=True, fill='both')
follower_text.config(state=tk.DISABLED)

# Profile Summary Tab
summary_tab = ttk.Frame(notebook)
notebook.add(summary_tab, text="Profile Summary")

summary_text = scrolledtext.ScrolledText(summary_tab, wrap=tk.WORD, font=('Arial', 12), bg='gray', fg='white')
summary_text.pack(expand=True, fill='both')
summary_text.config(state=tk.DISABLED)

root.mainloop()
