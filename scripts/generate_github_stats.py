#!/usr/bin/env python3
"""Generate self-hosted GitHub profile statistics SVGs using the GitHub REST API."""

import html
import json
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

USERNAME = "justkiddingz"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path(__file__).resolve().parent.parent

COLORS = {
    "background": "#1a1b27", "border": "#414868", "title": "#a9b1d6",
    "text": "#c0caf5", "muted": "#565f89", "accent": "#7aa2f7",
    "green": "#9ece6a", "purple": "#bb9af7", "orange": "#e0af68",
}
LANGUAGE_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5",
    "Go": "#00ADD8", "PHP": "#4F5D95", "HTML": "#e34c26",
    "CSS": "#563d7c", "Shell": "#89e051", "Java": "#b07219",
    "C#": "#178600", "C++": "#f34b7d", "Ruby": "#701516",
    "Rust": "#dea584", "Kotlin": "#A97BFF", "Swift": "#F05138",
}


def api_get(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "justkiddingz-profile-stats",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request(API + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_repositories():
    repos = []
    page = 1
    while True:
        batch = api_get(
            f"/users/{USERNAME}/repos?type=owner&per_page=100&page={page}&sort=updated"
        )
        repos.extend(batch)
        if len(batch) < 100:
            return repos
        page += 1


def svg_start(width, height, title):
    background = COLORS["background"]
    border = COLORS["border"]
    title_color = COLORS["title"]
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        f'<rect width="{width}" height="{height}" rx="12" fill="{background}" stroke="{border}"/>',
        f'<text x="25" y="34" fill="{title_color}" font-family="Segoe UI,Arial,sans-serif" font-size="16" font-weight="600">{html.escape(title)}</text>',
    ]


def write_stats(user, repos):
    width, height = 495, 190
    total_stars = sum(repo["stargazers_count"] for repo in repos if not repo["fork"])
    total_forks = sum(repo["forks_count"] for repo in repos if not repo["fork"])
    stats = [
        ("Public repositories", user["public_repos"], COLORS["accent"]),
        ("Total stars", total_stars, COLORS["orange"]),
        ("Total forks", total_forks, COLORS["purple"]),
        ("Followers", user["followers"], COLORS["green"]),
    ]
    positions = [(25, 83), (260, 83), (25, 145), (260, 145)]
    svg = svg_start(width, height, "GitHub Statistics")
    for (label, value, color), (x, y) in zip(stats, positions):
        svg.append(f'<circle cx="{x + 7}" cy="{y - 5}" r="5" fill="{color}"/>')
        svg.append(f'<text x="{x + 21}" y="{y}" fill="{COLORS["muted"]}" font-family="Segoe UI,Arial,sans-serif" font-size="12">{html.escape(label)}</text>')
        svg.append(f'<text x="{x + 21}" y="{y + 25}" fill="{COLORS["text"]}" font-family="Segoe UI,Arial,sans-serif" font-size="20" font-weight="700">{value:,}</text>')
    svg.append("</svg>")
    (OUT / "github-stats.svg").write_text("\n".join(svg), encoding="utf-8")


def write_languages(repos):
    totals = defaultdict(int)
    for repo in repos:
        if repo["fork"] or repo["size"] == 0:
            continue
        encoded_name = urllib.parse.quote(repo["full_name"], safe="/")
        try:
            languages = api_get(f"/repos/{encoded_name}/languages")
        except Exception as error:
            print(f"Skipping languages for {repo['full_name']}: {error}")
            continue
        for language, byte_count in languages.items():
            totals[language] += byte_count

    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:6]
    width, height = 495, 190
    svg = svg_start(width, height, "Most Used Languages")
    if not ranked:
        svg.append(f'<text x="25" y="90" fill="{COLORS["muted"]}" font-family="Segoe UI,Arial,sans-serif" font-size="13">No public language data available yet.</text>')
    else:
        total = sum(value for _, value in ranked)
        bar_x, bar_y, bar_width, bar_height = 25, 57, 445, 10
        cursor = bar_x
        for language, value in ranked:
            segment = bar_width * value / total
            color = LANGUAGE_COLORS.get(language, COLORS["accent"])
            svg.append(f'<rect x="{cursor:.2f}" y="{bar_y}" width="{max(segment, 1):.2f}" height="{bar_height}" fill="{color}"/>')
            cursor += segment
        for index, (language, value) in enumerate(ranked):
            col = index % 2
            row = index // 2
            x = 25 + col * 235
            y = 94 + row * 31
            percentage = value / total * 100
            color = LANGUAGE_COLORS.get(language, COLORS["accent"])
            svg.append(f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{color}"/>')
            svg.append(f'<text x="{x + 18}" y="{y}" fill="{COLORS["text"]}" font-family="Segoe UI,Arial,sans-serif" font-size="12">{html.escape(language)}</text>')
            svg.append(f'<text x="{x + 215}" y="{y}" text-anchor="end" fill="{COLORS["muted"]}" font-family="Segoe UI,Arial,sans-serif" font-size="12">{percentage:.1f}%</text>')
    svg.append("</svg>")
    (OUT / "top-languages.svg").write_text("\n".join(svg), encoding="utf-8")


def main():
    user = api_get(f"/users/{USERNAME}")
    repos = get_repositories()
    write_stats(user, repos)
    write_languages(repos)
    print(f"Generated profile stats from {len(repos)} public repositories.")


if __name__ == "__main__":
    main()
