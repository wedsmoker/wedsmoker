#!/usr/bin/env python3
"""
Safely updates README with GitHub stats badge section
Uses HTML comments as markers to avoid breaking existing content
"""
import requests
import sys
import os
from datetime import datetime

def get_all_time_stats(username, token):
    """Get all-time stats (stars, forks, repos) and recent clone data"""

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

    # All-time stats
    total_stars = 0
    total_forks = 0
    total_repos = 0

    # Recent stats (14 days)
    recent_clones = 0
    recent_unique = 0

    # Per-repo data for top 10
    repo_stats = []

    for repo in repos:
        if repo['fork']:
            continue

        total_repos += 1
        total_stars += repo['stargazers_count']
        total_forks += repo['forks_count']

        # Get recent clone data
        repo_name = repo['name']
        clone_url = f"https://api.github.com/repos/{username}/{repo_name}/traffic/clones"
        clone_response = requests.get(clone_url, headers=headers)

        if clone_response.status_code == 200:
            data = clone_response.json()
            clones = data.get('count', 0)
            uniques = data.get('uniques', 0)

            recent_clones += clones
            recent_unique += uniques

            # Store per-repo data
            repo_stats.append({
                'name': repo_name,
                'url': repo['html_url'],
                'clones': clones,
                'uniques': uniques
            })

    return {
        'total_stars': total_stars,
        'total_forks': total_forks,
        'total_repos': total_repos,
        'recent_clones': recent_clones,
        'recent_unique': recent_unique,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
        'repo_stats': repo_stats
    }

def generate_stats_section(stats):
    """Generate the stats badge section with kbd tags"""

    section = f"""<!-- GITHUB_STATS:START -->
<kbd>last 2 weeks:</kbd> <kbd>📊 {stats['recent_clones']:,} clones</kbd> <kbd>👥 {stats['recent_unique']:,} visitors</kbd>

<kbd>all time:</kbd> <kbd>📦 {stats['total_repos']:,} repos</kbd> <kbd>🍴 {stats['total_forks']:,} forks</kbd> <kbd>⭐ {stats['total_stars']:,} stars</kbd>
<!-- GITHUB_STATS:END -->"""

    return section

def update_readme(stats, readme_path):
    """Safely update README with stats section"""

    # Check if README exists
    if not os.path.exists(readme_path):
        print(f"Error: README not found at {readme_path}")
        return False

    # Read existing README
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Generate new stats section
    new_section = generate_stats_section(stats)

    # Markers for safe insertion
    start_marker = '<!-- GITHUB_STATS:START -->'
    end_marker = '<!-- GITHUB_STATS:END -->'

    if start_marker in content and end_marker in content:
        # Replace existing section
        print("Found existing stats section, updating...")
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker) + len(end_marker)
        new_content = content[:start_idx] + new_section + content[end_idx:]
    else:
        # Insert at the top (after title if it exists)
        print("No existing stats section found, inserting at top...")
        lines = content.split('\n')

        # Find where to insert (after first header or at beginning)
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('#'):
                insert_idx = i + 1
                break

        # Insert the section
        lines.insert(insert_idx, '')
        lines.insert(insert_idx + 1, new_section)
        lines.insert(insert_idx + 2, '')
        new_content = '\n'.join(lines)

    # Write updated README
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"\n✓ README updated successfully!")
    print(f"Stats: {stats['recent_clones']} clones, {stats['recent_unique']} unique, {stats['total_stars']} stars")
    return True

def write_github_summary(stats):
    """Write top 10 repos to GitHub Actions job summary"""

    # Check if running in GitHub Actions
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_file:
        print("\nNot running in GitHub Actions - skipping summary")
        return

    # Sort repos by clone count
    repo_stats = stats.get('repo_stats', [])
    top_repos = sorted(repo_stats, key=lambda x: x['clones'], reverse=True)[:10]

    # Generate markdown summary
    summary = "# 🔥 Top 10 Most Popular Repositories (Last 2 Weeks)\n\n"
    summary += "| Rank | Repository | Clones | Unique Visitors |\n"
    summary += "|:----:|:-----------|-------:|----------------:|\n"

    medals = ['🥇', '🥈', '🥉']
    for i, repo in enumerate(top_repos, 1):
        rank = medals[i-1] if i <= 3 else str(i)
        summary += f"| {rank} | **[{repo['name']}]({repo['url']})** | {repo['clones']:,} | {repo['uniques']:,} |\n"

    summary += f"\n---\n"
    summary += f"**Total across all repos:** {stats['recent_clones']:,} clones, {stats['recent_unique']:,} unique visitors\n"
    summary += f"\n*Updated: {stats['last_updated']}*\n"

    # Write to summary file
    try:
        with open(summary_file, 'a', encoding='utf-8') as f:
            f.write(summary)
        print("\n✓ GitHub Actions summary updated with top 10 repos!")
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
        print("Example: python update_readme.py wedsmoker ghp_xxx /path/to/README.md")
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
