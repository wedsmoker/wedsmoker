#!/usr/bin/env python3
import requests
import sys
import os
import json
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
        if repo['fork'] or repo['private']:
            continue

        repo_name = repo['name']
        print(f"Processing {repo_name}...")

        # Get traffic data
        clone_data = get_traffic_data(username, repo_name, 'clones', headers)
        view_data = get_traffic_data(username, repo_name, 'views', headers)

        clones = clone_data.get('count', 0)
        unique_cloners = clone_data.get('uniques', 0)
        unique_views = view_data.get('uniques', 0)

        # Get description
        description = repo.get('description', '') or ''

        # Store per-repo data
        repo_stats.append({
            'name': repo_name,
            'url': repo['html_url'],
            'clones': clones,
            'unique_cloners': unique_cloners,
            'visitors': unique_views,
            'description': description
        })

    # Convert UTC to EST (UTC-5)
    from datetime import timedelta
    utc_time = datetime.utcnow()
    est_time = utc_time - timedelta(hours=5)

    return {
        'repo_stats': repo_stats,
        'last_updated': est_time.strftime('%Y-%m-%d %H:%M EST')
    }

def generate_clone_total_snippet(stats):
    """Generate the inline clone total snippet"""
    repo_stats = stats.get('repo_stats', [])
    total_clones = sum(r['clones'] for r in repo_stats)
    total_unique = sum(r['unique_cloners'] for r in repo_stats)
    return (
        f'<!-- CLONE_TOTAL:START -->'
        f'<p><small><i>{total_clones:,} clones / {total_unique:,} unique cloners (last 2 weeks)</i></small></p>'
        f'<!-- CLONE_TOTAL:END -->'
    )

def generate_html_table(stats):
    repo_stats = stats.get('repo_stats', [])
    top_clones = sorted(repo_stats, key=lambda x: x['clones'], reverse=True)[:10]

    html = '<!-- PORTFOLIO_STATS:START -->\n\n'
    html += '<div class="col-header">Most Cloned (last 2 weeks)</div>\n\n'

    for repo in top_clones:
        desc = repo['description'] or 'No description'
        html += '<div class="repo-card">\n'
        html += f'  <div><a href="{repo["url"]}">{repo["name"]}</a></div>\n'
        html += f'  <div class="desc">{desc}</div>\n'
        html += f'  <div class="meta"><kbd>{repo["clones"]} Clones</kbd> / <kbd>{repo["unique_cloners"]} Unique Cloners</kbd></div>\n'
        html += '</div>\n\n'

    html += f'<div class="timestamp">Last updated: {stats["last_updated"]}</div>\n'
    html += '<!-- PORTFOLIO_STATS:END -->'

    return html


def write_stats_json(stats, output_dir):
    repo_stats = stats.get('repo_stats', [])
    top_clones = sorted(repo_stats, key=lambda x: x['clones'], reverse=True)[:10]
    total_clones = sum(r['clones'] for r in repo_stats)
    total_unique = sum(r['unique_cloners'] for r in repo_stats)

    data = {
        'last_updated': stats['last_updated'],
        'total_clones': total_clones,
        'total_unique_cloners': total_unique,
        'repos': top_clones
    }

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'stats.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Stats JSON written to {output_path}")

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

    # Update clone total snippet
    clone_start = '<!-- CLONE_TOTAL:START -->'
    clone_end = '<!-- CLONE_TOTAL:END -->'
    if clone_start in new_content and clone_end in new_content:
        print("Updating clone total snippet...")
        snippet = generate_clone_total_snippet(stats)
        cs_idx = new_content.find(clone_start)
        ce_idx = new_content.find(clone_end) + len(clone_end)
        new_content = new_content[:cs_idx] + snippet + new_content[ce_idx:]

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
        data_dir = sys.argv[4] if len(sys.argv) >= 5 else os.path.join(os.path.dirname(portfolio_path), 'data')
    else:
        username = os.environ.get('GITHUB_USERNAME')
        token = os.environ.get('GITHUB_TOKEN')
        portfolio_path = os.environ.get('PORTFOLIO_PATH', 'index.html')
        data_dir = os.path.join(os.path.dirname(portfolio_path), 'data')

    if not username or not token:
        print("Usage: python update_portfolio_stats.py <username> <token> <portfolio_path> [data_dir]")
        print("Example: python update_portfolio_stats.py usr-wwelsh ghp_xxx /path/to/index.html")
        sys.exit(1)

    print(f"Fetching GitHub stats for {username}...")
    stats = get_all_repo_stats(username, token)

    if stats:
        write_stats_json(stats, data_dir)
    else:
        print("Failed to fetch stats")
        sys.exit(1)

if __name__ == '__main__':
    main()
