#!/usr/bin/env python3
"""
Safely updates README with GitHub stats and full public repo list.
Uses HTML comments as markers to avoid breaking existing content.
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


def get_all_time_stats(username, token):
    """Get recent clone/view data and per-repo stats"""

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

    recent_clones = 0
    recent_visitors = 0
    repo_stats = []

    for repo in repos:
        if repo['fork'] or repo['private']:
            continue

        repo_name = repo['name']
        created_at = repo['created_at'][:10]  # YYYY-MM-DD
        description = repo.get('description', '') or ''
        stars = repo['stargazers_count']

        clone_data = get_traffic_data(username, repo_name, 'clones', headers)
        view_data = get_traffic_data(username, repo_name, 'views', headers)

        clones = clone_data.get('count', 0)
        unique_views = view_data.get('uniques', 0)

        recent_clones += clones
        recent_visitors += unique_views

        repo_stats.append({
            'name': repo_name,
            'url': repo['html_url'],
            'created_at': created_at,
            'description': description,
            'stars': stars,
            'clones': clones,
            'visitors': unique_views
        })

    return {
        'recent_clones': recent_clones,
        'recent_visitors': recent_visitors,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
        'repo_stats': repo_stats
    }


def generate_stats_section(stats):
    """Generate the stats kbd section"""
    return (
        f'<!-- GITHUB_STATS:START -->\n'
        f'`📡 Stats (last 14d):` `📊 {stats["recent_clones"]:,} clones` `👥 {stats["recent_visitors"]:,} visitors`\n'
        f'<!-- GITHUB_STATS:END -->'
    )


def generate_repo_list(stats):
    """Generate the auto repo list table sorted by creation date, newest first"""
    repo_stats = stats.get('repo_stats', [])
    sorted_repos = sorted(repo_stats, key=lambda x: x['created_at'], reverse=True)
    total = len(sorted_repos)

    lines = [
        '<!-- AUTO_REPO_LIST:START -->',
        f'### All Public Repositories ({total} total)',
        '| Repository | Created | ⭐ | 📊 Clones (14d) | 👥 Visitors (14d) |',
        '|:-----------|:-------:|---:|----------------:|------------------:|',
    ]

    for repo in sorted_repos:
        name_cell = f'[{repo["name"]}]({repo["url"]})'
        if repo['description']:
            name_cell += f'<br><sub>{repo["description"]}</sub>'
        lines.append(
            f'| {name_cell} | {repo["created_at"]} | {repo["stars"]} | {repo["clones"]:,} | {repo["visitors"]:,} |'
        )

    lines.append('')
    lines.append(f'*updated: {stats["last_updated"]} — sorted by creation date, newest first*')
    lines.append('<!-- AUTO_REPO_LIST:END -->')

    return '\n'.join(lines)


def update_readme(stats, readme_path):
    """Safely update README with stats section and repo list"""

    if not os.path.exists(readme_path):
        print(f"Error: README not found at {readme_path}")
        return False

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update GITHUB_STATS section
    stats_start = '<!-- GITHUB_STATS:START -->'
    stats_end = '<!-- GITHUB_STATS:END -->'
    if stats_start in content and stats_end in content:
        new_stats = generate_stats_section(stats)
        start_idx = content.find(stats_start)
        end_idx = content.find(stats_end) + len(stats_end)
        content = content[:start_idx] + new_stats + content[end_idx:]
        print("GITHUB_STATS section updated.")

    # Update AUTO_REPO_LIST section
    repo_start = '<!-- AUTO_REPO_LIST:START -->'
    repo_end = '<!-- AUTO_REPO_LIST:END -->'
    if repo_start in content and repo_end in content:
        new_repo_list = generate_repo_list(stats)
        start_idx = content.find(repo_start)
        end_idx = content.find(repo_end) + len(repo_end)
        content = content[:start_idx] + new_repo_list + content[end_idx:]
        print("AUTO_REPO_LIST section updated.")

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\nREADME updated successfully!")
    print(f"Stats: {stats['recent_clones']:,} clones, {stats['recent_visitors']:,} visitors")
    print(f"Repos: {len(stats['repo_stats'])} public repos listed")
    return True


def write_github_summary(stats):
    """Write top 10 repos to GitHub Actions job summary"""

    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_file:
        print("\nNot running in GitHub Actions - skipping summary")
        return

    repo_stats = stats.get('repo_stats', [])
    top_repos = sorted(repo_stats, key=lambda x: x['clones'], reverse=True)[:10]

    summary = "# 🔥 Top 10 Most Popular Repositories (Last 2 Weeks)\n\n"
    summary += "| Rank | Repository | Clones | Unique Visitors |\n"
    summary += "|:----:|:-----------|-------:|----------------:|\n"

    medals = ['🥇', '🥈', '🥉']
    for i, repo in enumerate(top_repos, 1):
        rank = medals[i-1] if i <= 3 else str(i)
        summary += f"| {rank} | **[{repo['name']}]({repo['url']})** | {repo['clones']:,} | {repo['visitors']:,} |\n"

    summary += f"\n---\n"
    summary += f"**Total across all repos:** {stats['recent_clones']:,} clones, {stats['recent_visitors']:,} unique visitors\n"
    summary += f"\n*Updated: {stats['last_updated']}*\n"

    try:
        with open(summary_file, 'a', encoding='utf-8') as f:
            f.write(summary)
        print("\nGitHub Actions summary updated with top 10 repos!")
    except Exception as e:
        print(f"Failed to write summary: {e}")


def main():
    if len(sys.argv) >= 4:
        username = sys.argv[1]
        token = sys.argv[2]
        readme_path = sys.argv[3]
    else:
        username = os.environ.get('GITHUB_USERNAME')
        token = os.environ.get('GITHUB_TOKEN')
        readme_path = 'README.md'

    if not username or not token:
        print("Usage: python update_readme.py <username> <token> <readme_path>")
        sys.exit(1)

    print(f"Fetching GitHub stats for {username}...")
    stats = get_all_time_stats(username, token)

    if stats:
        update_readme(stats, readme_path)
        write_github_summary(stats)
    else:
        print("Failed to fetch stats")
        sys.exit(1)


if __name__ == '__main__':
    main()
