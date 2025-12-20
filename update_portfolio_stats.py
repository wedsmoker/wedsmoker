#!/usr/bin/env python3
"""
Updates portfolio HTML with GitHub repository stats
Generates HTML table with top 10 repos by clones and unique visitors
"""
import requests
import sys
import os
from datetime import datetime

def get_traffic_data(username, repo_name, traffic_type, headers):
    """Helper function to fetch traffic data from GitHub API"""
    url = f"https://api.github.com/repos/{username}/{repo_name}/traffic/{traffic_type}"
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else {}

def get_repo_description(username, repo_name, headers):
    """Fetch repository description from GitHub API"""
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get('description', '') or ''
    return ''

def get_all_repo_stats(username, token):
    """Get repository stats with traffic data and descriptions"""

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    repos_url = 'https://api.github.com/user/repos?per_page=100&type=owner'
    response = requests.get(repos_url, headers=headers)

    if response.status_code != 200:
        print(f"Error fetching repos: {response.status_code}")
        return None

    repos = response.json()
    repo_stats = []

    for repo in repos:
        if repo['fork']:
            continue

        repo_name = repo['name']
        print(f"Processing {repo_name}...")

        # Get traffic data
        clone_data = get_traffic_data(username, repo_name, 'clones', headers)
        view_data = get_traffic_data(username, repo_name, 'views', headers)

        clones = clone_data.get('count', 0)
        unique_views = view_data.get('uniques', 0)

        # Get description
        description = repo.get('description', '') or ''

        # Store per-repo data
        repo_stats.append({
            'name': repo_name,
            'url': repo['html_url'],
            'clones': clones,
            'visitors': unique_views,
            'description': description
        })

    return {
        'repo_stats': repo_stats,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    }

def generate_html_table(stats):
    """Generate HTML table with top 10 repos by clones and unique visitors"""

    repo_stats = stats.get('repo_stats', [])

    # Get top 10 by clones
    top_clones = sorted(repo_stats, key=lambda x: x['clones'], reverse=True)[:10]

    # Get top 10 by unique visitors
    top_visitors = sorted(repo_stats, key=lambda x: x['visitors'], reverse=True)[:10]

    # Generate HTML table
    html = '<!-- PORTFOLIO_STATS:START -->\n\n'

    # Top 10 by Clones
    html += '<h3>Most Cloned (last 2 weeks)</h3>\n'
    html += '<table border="1" cellpadding="3">\n'
    html += '<tr><th>Rank</th><th>Repository</th><th>Description</th><th>Clones</th><th>Visitors</th></tr>\n'

    for i, repo in enumerate(top_clones, 1):
        name = repo['name']
        url = repo['url']
        desc = repo['description'] if repo['description'] else 'No description'
        clones = repo['clones']
        visitors = repo['visitors']

        html += f'<tr><td>{i}</td><td><a href="{url}">{name}</a></td><td>{desc}</td><td>{clones}</td><td>{visitors}</td></tr>\n'

    html += '</table>\n\n'

    # Top 10 by Unique Visitors
    html += '<h3>Most Visited (last 2 weeks)</h3>\n'
    html += '<table border="1" cellpadding="3">\n'
    html += '<tr><th>Rank</th><th>Repository</th><th>Description</th><th>Visitors</th><th>Clones</th></tr>\n'

    for i, repo in enumerate(top_visitors, 1):
        name = repo['name']
        url = repo['url']
        desc = repo['description'] if repo['description'] else 'No description'
        clones = repo['clones']
        visitors = repo['visitors']

        html += f'<tr><td>{i}</td><td><a href="{url}">{name}</a></td><td>{desc}</td><td>{visitors}</td><td>{clones}</td></tr>\n'

    html += '</table>\n'
    html += f'<p><small>Last updated: {stats["last_updated"]}</small></p>\n'
    html += '<!-- PORTFOLIO_STATS:END -->'

    return html

def update_portfolio(stats, portfolio_path):
    """Update portfolio HTML with stats table"""

    if not os.path.exists(portfolio_path):
        print(f"Error: Portfolio not found at {portfolio_path}")
        return False

    # Read existing portfolio
    with open(portfolio_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Generate new stats section
    new_section = generate_html_table(stats)

    # Markers for safe insertion
    start_marker = '<!-- PORTFOLIO_STATS:START -->'
    end_marker = '<!-- PORTFOLIO_STATS:END -->'

    if start_marker in content and end_marker in content:
        # Replace existing section
        print("Found existing stats section, updating...")
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker) + len(end_marker)
        new_content = content[:start_idx] + new_section + content[end_idx:]
    else:
        # Append at the end
        print("No existing stats section found, appending to end...")
        new_content = content.rstrip() + '\n\n' + new_section + '\n'

    # Write updated portfolio
    with open(portfolio_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"\nPortfolio updated successfully!")
    return True

def main():
    if len(sys.argv) >= 4:
        username = sys.argv[1]
        token = sys.argv[2]
        portfolio_path = sys.argv[3]
    else:
        username = os.environ.get('GITHUB_USERNAME')
        token = os.environ.get('GITHUB_TOKEN')
        portfolio_path = os.environ.get('PORTFOLIO_PATH', 'index.html')

    if not username or not token:
        print("Usage: python update_portfolio_stats.py <username> <token> <portfolio_path>")
        print("Example: python update_portfolio_stats.py usr-wwelsh ghp_xxx /path/to/index.html")
        sys.exit(1)

    print(f"Fetching GitHub stats for {username}...")
    stats = get_all_repo_stats(username, token)

    if stats:
        update_portfolio(stats, portfolio_path)
    else:
        print("Failed to fetch stats")
        sys.exit(1)

if __name__ == '__main__':
    main()
