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

# Function to check for the existence of the 'profile_summaries' table and create it if it doesn't exist
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
        summary_button.config(state=tk.NORMAL)  # Enable summary button after tracking

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
    summary_button.config(state=tk.NORMAL)  # Enable summary button after tracking

# Function to show analytics
def show_analytics():
    try:
        conn = sqlite3.connect('follower_data.db')
        plot_follower_growth(conn)
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        switch_tab(notebook, 0)  # Switch to "Followers" tab after showing analytics

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
    finally:
        switch_tab(notebook, 0)  # Switch to "Followers" tab after segmenting

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
        switch_tab(notebook, 1)  # Switch to "Profile Summary" tab after generating summary

def switch_tab(notebook, index):
    global selected_tab
    notebook.select(index)
    style.configure("TNotebook.Tab{}".format(index), background="blue", foreground="white")
    style.configure("TNotebook.Tab{}".format(selected_tab), background="gray", foreground="black")
    selected_tab = index

# # Define themes as dictionaries
# themes = {
#     "Default": {
#         "background": "SystemButtonFace",
#         "foreground": "black",
#         "button_background": "SystemButtonFace",
#         "button_foreground": "black",
#     },
#     "Solarized Light": {
#         "background": "#fdf6e3",
#         "foreground": "#657b83",
#         "button_background": "#eee8d5",
#         "button_foreground": "#657b83",
#     },
#     "Solarized Dark": {
#         "background": "#002b36",
#         "foreground": "#839496",
#         "button_background": "#073642",
#         "button_foreground": "#839496",
#     },
#     "High Contrast": {
#         "background": "black",
#         "foreground": "white",
#         "button_background": "black",
#         "button_foreground": "white",
#     }
# }

# def apply_theme(theme_name):
#     theme = themes.get(theme_name, themes["Default"])

#     root.config(bg=theme["background"])
#     for widget in root.winfo_children():
#         try:
#             widget.config(bg=theme["background"], fg=theme["foreground"])
#         except:
#             pass

#     for btn in [start_button, show_analytics_button, segment_followers_button, summary_button]:
#         # btn.config(bg=theme["button_background"], fg=theme["button_foreground"])
#         btn["style"] = "TButton"

# def select_theme():
#     theme_name = theme_var.get()
#     apply_theme(theme_name)

root = tk.Tk()
root.title("GitHub Follower Tracker")
style = ttk.Style()

# Add menu for theme selection
menu_bar = Menu(root)
root.config(menu=menu_bar)

file_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="Exit", command=root.quit)

settings_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Settings", menu=settings_menu)

# Add menu for theme selection
menu_bar = Menu(root)
root.config(menu=menu_bar)

file_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="Exit", command=root.quit)  

settings_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Settings", menu=settings_menu)

# Add theme selection options to Settings menu
theme_var = tk.StringVar(root)
theme_var.set("Default")  # Set default theme

theme_options = [
    ("Default", "Default"),
    ("Solarized Light", "Solarized Light"),
    ("Solarized Dark", "Solarized Dark"),
    ("High Contrast", "High Contrast"),
]

theme_submenu = Menu(settings_menu, tearoff=0)

for theme_name, theme_display in theme_options:
    theme_submenu.add_radiobutton(
        label=theme_display, variable=theme_var, command=lambda t=theme_name: select_theme(t)
    )

settings_menu.add_cascade(label="Theme", menu=theme_submenu)

# Define themes as dictionaries
themes = {
    "Default": {
        "background": "SystemButtonFace",
        "foreground": "black",
        "button_background": "SystemButtonFace",
        "button_foreground": "black",
    },
    "Solarized Light": {
        "background": "#fdf6e3",
        "foreground": "#657b83",
        "button_background": "#eee8d5",
        "button_foreground": "#657b83",
    },
    "Solarized Dark": {
        "background": "#002b36",
        "foreground": "#839496",
        "button_background": "#073642",
        "button_foreground": "#839496",
    },
    "High Contrast": {
        "background": "black",
        "foreground": "white",
        "button_background": "black",
        "button_foreground": "white",
    }
}

def apply_theme(theme_name):
    theme = themes.get(theme_name, themes["Default"])

    # Set background and foreground colors for all widgets
    root.config(bg=theme["background"])
    for widget in root.winfo_children():
        try:
            widget.config(bg=theme["background"], fg=theme["foreground"])
        except:
            pass

    # Set button styles using theme colors
    style = ttk.Style(root)
    for btn_name in ["start_button", "show_analytics_button", "segment_followers_button", "summary_button"]:
        style.configure(btn_name, background=theme["button_background"], foreground=theme["button_foreground"])

# Apply default theme on startup
apply_theme("Default")

# Function to apply chosen theme
def select_theme():
    theme_name = theme_var.get()
    apply_theme(theme_name)

theme_submenu.add_radiobutton(
    label=theme_display, variable=theme_var, command=select_theme
)

# Create the main window
root = tk.Tk()
root.title("GitHub Follower Tracker")

# Add menu for theme selection
menu_bar = Menu(root)
root.config(menu=menu_bar)

file_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="Exit", 
 command=root.quit)

settings_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Settings", menu=settings_menu)

theme_var = tk.StringVar()
theme_var.set("Default")  # Set default theme

theme_options = [
    ("Default", "Default"),
    ("Solarized Light", "Solarized Light"),
    ("Solarized Dark", "Solarized Dark"),
    ("High Contrast", "High Contrast"),
]

theme_submenu = Menu(settings_menu, tearoff=0)

for theme_name, theme_display in theme_options:
    theme_submenu.add_radiobutton(
        label=theme_display, variable=theme_var, command=lambda t=theme_name: select_theme(t)
    )

settings_menu.add_cascade(label="Theme", menu=theme_submenu)

# Adding a Notebook widget for tabbed interface
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')

follower_tab = ttk.Frame(notebook)
summary_tab = ttk.Frame(notebook)
notebook.add(follower_tab, text="Followers")
notebook.add(summary_tab, text="Profile Summary")

selected_tab = 0

# Label and entry for GitHub username
username_label = ttk.Label(follower_tab, text="GitHub Username:")
username_label.pack(pady=5)
username_entry = ttk.Entry(follower_tab, width=30)
username_entry.pack(pady=5)

# Label and entry for GitHub token
token_label = ttk.Label(follower_tab, text="GitHub Token:")
token_label.pack(pady=5)
token_entry = ttk.Entry(follower_tab, show='*', width=30)
token_entry.pack(pady=5)

# Label and entry for follower data file
followers_file_label = ttk.Label(follower_tab, text="Followers File:")
followers_file_label.pack(pady=5)
followers_file_entry = ttk.Entry(follower_tab, width=30)
followers_file_entry.pack(pady=5)

# Button to start tracking followers
start_button = ttk.Button(follower_tab, text="Start Tracking", command=start_tracking)
start_button.pack(pady=10)

# Button to show analytics
show_analytics_button = ttk.Button(follower_tab, text="Show Analytics", command=show_analytics, state=tk.DISABLED)
show_analytics_button.pack(pady=10)

# Dropdown for segmentation type
segmentation_type_label = ttk.Label(follower_tab, text="Segmentation Type:")
segmentation_type_label.pack(pady=5)
segmentation_type_var = tk.StringVar()
segmentation_type_dropdown = ttk.Combobox(follower_tab, textvariable=segmentation_type_var, state="readonly")
segmentation_type_dropdown['values'] = ["Please Select", "Repo", "Activity"]
segmentation_type_dropdown.current(0)
segmentation_type_dropdown.pack(pady=5)

# Button to segment followers
segment_followers_button = ttk.Button(follower_tab, text="Segment Followers", command=segment_followers_ui, state=tk.DISABLED)
segment_followers_button.pack(pady=10)

# ScrolledText widget to display follower information
follower_text = scrolledtext.ScrolledText(follower_tab, width=70, height=20, state=tk.DISABLED)
follower_text.pack(pady=10)

# Label and entry for Profile Summary tab
profile_label = ttk.Label(summary_tab, text="GitHub Username:")
profile_label.pack(pady=5)
profile_entry = ttk.Entry(summary_tab, width=30)
profile_entry.pack(pady=5)

# Button to generate summary
summary_button = ttk.Button(summary_tab, text="Generate Summary", command=generate_summary_wrapper, state=tk.DISABLED)
summary_button.pack(pady=10)

# ScrolledText widget to display profile summary
summary_text = scrolledtext.ScrolledText(summary_tab, width=70, height=20, state=tk.DISABLED)
summary_text.pack(pady=10)

# Function calls theme after all widgets are created
def apply_theme_after_init():
    apply_theme("Default")

# Start the main loop
root.mainloop()