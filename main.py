# main.py
# MIT License
# Created Date: 2024-09-02
# Created By: Jason Evans
# Modified Date: 2025-01-29
# Modified By: Jason Evans
# Version 1.2.6

import tkinter as tk
from tkinter import ttk, scrolledtext, Menu, messagebox
import threading
import os
import json
import sqlite3
from datetime import datetime
import requests
from analytics import create_table, insert_follower, plot_follower_growth, segment_followers, plot_unfollower_trend
from dev.prototype.utils import get_all_followers, format_list
from openai import OpenAI
from dotenv import load_dotenv
import sys
import logging
from datetime import datetime
import webbrowser

# Set up logger for debugging and error tracking
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Load API key from .env file
load_dotenv()

# Function to check for the existence of the 'profile_summaries' table and creates it if it doesn't exist 
# Stores the generated summaries
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

# Helper function to get all users you are following
def get_all_following(username, token):
    following_url = f'https://api.github.com/users/{username}/following'
    return get_all_followers(username, token, following_url)  # Reuse get_all_followers for simplicity

# Function to open PayPal donation link
def open_donation_link():
    donation_url = "https://www.paypal.com/donate/?hosted_button_id=AQCPKNSDGMJLL"
    webbrowser.open(donation_url)

# Function to track followers and who you follow that don't follow you back
def track_followers(username, token, followers_file):
    try:
        # Step 1: Establish connection to database
        conn = sqlite3.connect('follower_data.db')
        create_table(conn)
        cursor = conn.cursor()  # ✅ Create cursor at the start

        # Step 2: Load previous follower data if exists
        if os.path.exists(followers_file):
            with open(followers_file, 'r') as f:
                follower_data = json.load(f)
                previous_followers = follower_data.get('followers', [])
                follower_history = follower_data.get('history', {})
        else:
            previous_followers = []
            follower_history = {}

        # Step 3: Get current followers from GitHub API
        followers_url = f'https://api.github.com/users/{username}/followers'
        current_followers = get_all_followers(username, token, followers_url)

        following_list = get_all_following(username, token)  # Fetch users you are following

        # Step 4: Compute new followers, unfollowers, and followers who followed back
        new_followers = list(set(current_followers) - set(previous_followers))
        unfollowers = list(set(previous_followers) - set(current_followers))
        followers_back = list(set(previous_followers) & set(current_followers))

        # Find users you are following who don't follow you back
        not_following_back = list(set(following_list) - set(current_followers))

        # Step 5: Capture current date and time
        today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        follower_history[today] = len(current_followers)

        # Step 6: Insert current followers into database
        for follower in current_followers:
            insert_follower(conn, follower, today)

        # ✅ Step 7: Insert unfollowers into database (Ensure `conn` is not closed early)
        for unfollower in unfollowers:
            cursor.execute('''
                INSERT INTO unfollowers (username, timestamp)
                VALUES (?, ?)
            ''', (unfollower, today))
            conn.commit()

        # Step 8: Update output window (with timestamp)
        follower_text.config(state=tk.NORMAL)
        follower_text.delete(1.0, tk.END)

        timestamp_output = f"Followers tracked on: {today}\n\n"
        print(f"Inserting timestamp: {timestamp_output}")  
        follower_text.insert(tk.END, timestamp_output)  

        formatted_new, color_new = format_list("New followers", new_followers, "green")
        follower_text.insert(tk.END, formatted_new, "new_followers")

        formatted_unf, color_unf = format_list("Unfollowers", unfollowers, "red")
        follower_text.insert(tk.END, formatted_unf, "unfollowers")

        formatted_not_following_back, color_not_following_back = format_list("Not following you back", not_following_back, "purple")
        follower_text.insert(tk.END, formatted_not_following_back, "not_following_back")

        formatted_back, color_back = format_list("Followers who followed back", followers_back, "blue")
        follower_text.insert(tk.END, formatted_back, "followers_back")

        follower_text.tag_config("new_followers", foreground=color_new)
        follower_text.tag_config("unfollowers", foreground=color_unf)
        follower_text.tag_config("not_following_back", foreground=color_not_following_back)
        follower_text.tag_config("followers_back", foreground=color_back)

        follower_text.config(state=tk.DISABLED)

        # Step 9: Save updated data to file
        with open(followers_file, 'w') as f:
            json.dump({'followers': current_followers, 'history': follower_history}, f, indent=4)

        # ✅ Enable buttons after tracking completes successfully
        show_analytics_button.config(state=tk.NORMAL)
        show_unfollower_trend_button.config(state=tk.NORMAL)
        segment_followers_button.config(state=tk.NORMAL)
        summary_button.config(state=tk.NORMAL)

    except Exception as e:
        messagebox.showerror("Error", str(e))

    finally:
        if conn:
            conn.close()  # ✅ Ensure database connection is always closed safely

    switch_tab(notebook, 0)  # Switch to "Followers" tab after generating summary


    # Insert unfollowers into database
    for unfollower in unfollowers:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO unfollowers (username, timestamp)
            VALUES (?, ?)
        ''', (unfollower, today))
        conn.commit()

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
        return summary, profile_description, repos_contributed_to

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
    summary, profile_description, repos_contributed_to = generate_summary(username, token)

    if summary:
        
        # Store the summary in the database
        try:
            conn = sqlite3.connect('follower_data.db')
            create_summary_table(conn)  # Ensure the table is created
            cursor = conn.cursor()

            # Insert the summary into the database
            cursor.execute('''INSERT INTO profile_summaries (username, profile_description, repos_contributed_to, summary)
                              VALUES (?, ?, ?, ?)''',
                           (username, profile_description, ", ".join(repos_contributed_to), summary))
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", str(e))

        # Display the summary in the UI 
        summary_text.config(state=tk.NORMAL)
        summary_text.delete(1.0, tk.END)
        summary_text.insert(tk.END, f"Summary: {summary}", "summary")
        summary_text.tag_config("summary", foreground="black")
        summary_text.config(state=tk.DISABLED)
        
        # Switch to the Profile Summary tab
        # notebook.select(1)  # Index 1 refers to the "Profile Summary" tab
        switch_tab(notebook, 1)  # Switch to "Profile Summary" tab after generating summary

def switch_tab(notebook, index):
     # Initialize selected_tab here
    selected_tab = 0  # or any default value
    
    notebook.select(index)
    style.configure("TNotebook.Tab{}".format(index), background="blue", foreground="white")
    style.configure("TNotebook.Tab{}".format(selected_tab), background="gray", foreground="black")
    selected_tab = index

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

def show_unfollowers():
    try:
        conn = sqlite3.connect('follower_data.db')
        plot_unfollower_trend(conn)
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", str(e))
    switch_tab(notebook, 0)

# GUI setup
root = tk.Tk()
root.title("GitHub Follower Checker")

# Initialize selected tab
selected_tab = 0

# Configure notebook style
style = ttk.Style()
style.theme_use("default")
style.configure("TNotebook.Tab", background="gray", foreground="black")

# Add notebook to root
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')

# Increase window size to accommodate all elements
root.geometry("1000x800")
root.resizable(True, True)

# Header
header = tk.Label(root, text="GitHub Follower Checker", font=('Helvetica', 18, 'bold'), pady=10)
header.pack()

# Frame for input fields with columns
input_frame = tk.Frame(root, padx=20, pady=10)
input_frame.pack(fill=tk.X)

# Left column for follower-related controls
left_column = tk.Frame(input_frame)
left_column.grid(row=0, column=0, padx=(0, 20), pady=10, sticky="n")

# Right column for profile summary-related controls
right_column = tk.Frame(input_frame)
right_column.grid(row=0, column=1, pady=10, sticky="n")

# Tabs for different outputs
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')

# Tab for follower data
follower_tab = ttk.Frame(notebook)
notebook.add(follower_tab, text="Followers")

# Tab for summary data
summary_tab = ttk.Frame(notebook)
notebook.add(summary_tab, text="Profile Summary")

# Username input
username_label = tk.Label(left_column, text="GitHub Username:")
username_label.pack(anchor="w")
username_entry = tk.Entry(left_column)
username_entry.pack(anchor="w")

# Token input
token_label = tk.Label(left_column, text="GitHub Token:")
token_label.pack(anchor="w")
token_entry = tk.Entry(left_column, show="*")
token_entry.pack(anchor="w")

# Follower file name input
followers_file_label = tk.Label(left_column, text="Followers File:")
followers_file_label.pack(anchor="w")
followers_file_entry = tk.Entry(left_column)
followers_file_entry.pack(anchor="w")

# Profile entry input (right column)
profile_label = tk.Label(right_column, text="Enter GitHub Profile:")
profile_label.pack(anchor="w")
profile_entry = tk.Entry(right_column)
profile_entry.pack(anchor="w")

# Tracking button
track_button = tk.Button(left_column, text="Track Followers", command=start_tracking)
track_button.pack(anchor="w", pady=5)

# Show analytics button
show_analytics_button = tk.Button(left_column, text="Show Follower Trends", command=show_analytics, state=tk.DISABLED)
show_analytics_button.pack(anchor="w", pady=5)

# Show unfollower trends button
show_unfollower_trend_button = tk.Button(left_column, text="Show Unfollower Trends", command=show_unfollowers, state=tk.DISABLED)
show_unfollower_trend_button.pack(anchor="w", pady=5)

# Create the segmentation type variable with a default read-only label "Please Select"
segmentation_type_var = tk.StringVar(value="Please Select")

# Label for Segmentation
segmentation_label = tk.Label(left_column, text="Segment By:")
segmentation_label.pack(anchor="w", pady=5)

# Dropdown menu for Segmentation Types
segmentation_menu = tk.OptionMenu(left_column, segmentation_type_var, "repo", "activity")
segmentation_menu.pack(anchor="w", pady=5)

# Segment followers button
segment_followers_button = tk.Button(left_column, text="Segment Followers", command=segment_followers_ui, state=tk.DISABLED)
segment_followers_button.pack(anchor="w", pady=5)

# Profile summary button
summary_button = tk.Button(right_column, text="Generate Summary", command=generate_summary_wrapper, state=tk.DISABLED)
summary_button.pack(anchor="w", pady=5)

# Adding the "Donate Now" button
donate_button = tk.Button(root, text="Donate Now", command=open_donation_link, bg="blue", fg="white", font=("Arial", 12, "bold"))
donate_button.pack(pady=10)  # Adjust padding as needed

# Follower display
follower_text = scrolledtext.ScrolledText(follower_tab, height=20, state=tk.DISABLED, wrap=tk.WORD)
follower_text.pack(fill=tk.BOTH, padx=20, pady=10, expand=True)

# Summary display
summary_text = scrolledtext.ScrolledText(summary_tab, height=20, state=tk.DISABLED, wrap=tk.WORD)
summary_text.pack(fill=tk.BOTH, padx=20, pady=10, expand=True)

# Switch to the "Followers" tab initially
switch_tab(notebook, 0)

# Menu Bar for Theme Selection
menu_bar = Menu(root)
root.config(menu=menu_bar)

file_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="Exit", command=root.quit)

# Theme Menu
theme_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Settings", menu=theme_menu)

theme_menu.add_command(label="Light Theme", command=lambda: set_theme("light"))
theme_menu.add_command(label="Dark Theme", command=lambda: set_theme("dark"))
theme_menu.add_command(label="Solarized Light Theme", command=lambda: set_theme("solarized_light"))
theme_menu.add_command(label="Custom Theme", command=lambda: set_theme("custom"))

root.mainloop()