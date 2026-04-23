## utils.py
## MIT License
## Created Date: 2024-09-01
## Version 1.1

import requests

def get_all_followers(username, token, followers_url):
    followers = []
    headers = {'Authorization': f'token {token}'}
    while followers_url:
        response = requests.get(followers_url, headers=headers)
        response.raise_for_status()
        followers += [follower['login'] for follower in response.json()]
        followers_url = response.links.get('next', {}).get('url')
    return followers

def format_list(title, items, color):
    formatted_items = f"{title} ({len(items)}):\n" + "\n".join(items) + "\n\n"
    return formatted_items, color