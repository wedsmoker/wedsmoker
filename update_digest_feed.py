#!/usr/bin/env python3
import os
import re
import sys
import json
from pathlib import Path


def parse_date_lookback(filename):
    stem = Path(filename).stem
    match = re.match(r'(\d{4}-\d{2}-\d{2})-(\d+)d', stem)
    if match:
        return match.group(1), int(match.group(2))
    return None, None


def find_latest_digest(digests_dir):
    files = sorted(Path(digests_dir).glob('*.md'), reverse=True)
    return files[0] if files else None


def extract_section(content, section_name):
    pattern = rf'## {re.escape(section_name)}\n(.*?)(?=\n## |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ''


def apply_inline(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text


def md_to_html(text):
    lines = text.split('\n')
    html_lines = []
    in_ul = False

    for line in lines:
        if line.startswith('- '):
            if not in_ul:
                html_lines.append('<ul>')
                in_ul = True
            html_lines.append(f'  <li>{apply_inline(line[2:].strip())}</li>')
        else:
            if in_ul:
                html_lines.append('</ul>')
                in_ul = False
            if line.startswith('### '):
                html_lines.append(f'<h4>{apply_inline(line[4:])}</h4>')
            elif line.strip():
                html_lines.append(f'<p>{apply_inline(line)}</p>')

    if in_ul:
        html_lines.append('</ul>')

    return '\n'.join(html_lines)


def extract_repo_names(per_repo_content):
    return re.findall(r'^### (.+)$', per_repo_content, re.MULTILINE)


def generate_digest_html(date, lookback, summary_text, per_repo_text):
    summary_html = md_to_html(summary_text)
    per_repo_html = md_to_html(per_repo_text)

    html = '<!-- DIGEST_FEED:START -->\n'
    html += '<div class="digest-header">\n'
    html += f'  <span class="digest-date">{date}</span>\n'
    html += f'  <span class="digest-badge">{lookback}d lookback</span>\n'
    html += '</div>\n'
    html += '<div class="digest-summary">\n'
    html += summary_html + '\n'
    html += '</div>\n'
    html += '<details class="digest-details">\n'
    html += '  <summary>Per-repo breakdown</summary>\n'
    html += '  <div class="digest-repos">\n'
    html += per_repo_html + '\n'
    html += '  </div>\n'
    html += '</details>\n'
    html += '<!-- DIGEST_FEED:END -->'

    return html


def inject_into_html(html_path, new_section, start_marker, end_marker):
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if start_marker in content and end_marker in content:
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker) + len(end_marker)
        new_content = content[:start_idx] + new_section + content[end_idx:]
    else:
        print(f"Warning: markers not found in {html_path}, skipping injection")
        return

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)


def write_digest_json(output_dir, date, lookback, filename, summary, repo_names):
    os.makedirs(output_dir, exist_ok=True)
    data = {
        'date': date,
        'lookback': lookback,
        'filename': filename,
        'summary': summary,
        'repos': [f'usr-wwelsh/{r}' for r in repo_names]
    }
    output_path = os.path.join(output_dir, 'digest-latest.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Digest JSON written to {output_path}")


def main():
    if len(sys.argv) < 4:
        print("Usage: python update_digest_feed.py <digests_dir> <index_html> <data_dir>")
        sys.exit(1)

    digests_dir = sys.argv[1]
    html_path = sys.argv[2]
    data_dir = sys.argv[3]

    latest = find_latest_digest(digests_dir)
    if not latest:
        print(f"No digest files found in {digests_dir}")
        sys.exit(0)

    date, lookback = parse_date_lookback(latest.name)
    if not date:
        print(f"Could not parse date from {latest.name}")
        sys.exit(1)

    with open(latest, 'r', encoding='utf-8') as f:
        content = f.read()

    summary = extract_section(content, 'Summary')
    per_repo = extract_section(content, 'Per-Repo Activity')
    repo_names = extract_repo_names(per_repo)

    digest_html = generate_digest_html(date, lookback, summary, per_repo)
    inject_into_html(html_path, digest_html, '<!-- DIGEST_FEED:START -->', '<!-- DIGEST_FEED:END -->')
    write_digest_json(data_dir, date, lookback, latest.name, summary, repo_names)

    print(f"Digest feed updated from {latest.name}")


if __name__ == '__main__':
    main()
