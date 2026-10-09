#!/usr/bin/env python3
"""Render small, theme-aware profile cards from public GitHub data."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

from typography import outline_svg


class ContributionCalendar(HTMLParser):
    """Join GitHub's dated calendar cells to their contribution tooltips."""

    def __init__(self):
        super().__init__()
        self.cells = {}
        self.counts = {}
        self.tooltip = None
        self.parts = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "td" and "data-date" in attributes:
            self.cells[attributes["id"]] = date.fromisoformat(attributes["data-date"])
        if tag == "tool-tip":
            self.tooltip = attributes.get("for")
            self.parts = []

    def handle_data(self, data):
        if self.tooltip:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != "tool-tip" or not self.tooltip:
            return
        text = " ".join(self.parts)
        match = re.search(r"([\d,]+) contributions?", text)
        if match:
            count = int(match[1].replace(",", ""))
        elif "No contributions" in text:
            count = 0
        else:
            raise ValueError(f"Unrecognized contribution tooltip: {text}")
        if self.tooltip in self.cells:
            self.counts[self.cells[self.tooltip]] = count
        self.tooltip = None


def fetch(url, token=None):
    headers = {"User-Agent": "KINGKK-007-profile", "Accept": "application/vnd.github+json"}
    # Only attach the workflow token to GitHub's API.
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return response.read().decode()


def public_repositories(username, token):
    repositories = []
    page = 1
    while True:
        batch = json.loads(fetch(
            f"https://api.github.com/users/{username}/repos?per_page=100&page={page}", token
        ))
        repositories.extend(batch)
        if len(batch) < 100:
            return repositories
        page += 1


def language_totals(repositories, token):
    eligible = [repo for repo in repositories if not repo["fork"] and repo["size"]]

    def languages(repo):
        return json.loads(fetch(repo["languages_url"], token))

    totals = Counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(languages, eligible):
            totals.update(result)
    return totals


def svg_start(title, description):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="238" viewBox="0 0 420 238" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<style>
:root{{--bg:#f7f9f7;--border:#d9e4dd;--text:#182d23;--muted:#526b5d;--accent:#347a5b;--track:#e4ede7;--bar:#69ac8b}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0d1117;--border:#293830;--text:#e6ede8;--muted:#92a69a;--accent:#9bd8bc;--track:#1b2821;--bar:#76ad91}}}}
text{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;fill:var(--text)}}
.label{{fill:var(--muted)}}
.muted{{fill:var(--muted)}}
</style>
<rect x=".5" y=".5" width="419" height="237" rx="10" fill="var(--bg)" stroke="var(--border)"/>
'''


def activity_card(counts, today):
    recent = {day: count for day, count in counts.items()
              if today - timedelta(days=364) <= day <= today}
    if len(recent) < 350:
        raise ValueError("The public contribution calendar is incomplete; keep the previous cards.")
    total = sum(recent.values())
    active = sum(count > 0 for count in recent.values())
    weeks = [0] * 52
    for day, count in recent.items():
        age = (today - day).days // 7
        if age < 52:
            weeks[51 - age] += count
    svg = [svg_start("GitHub activity", f"{total} contributions across {active} active days in the past year.")]
    svg.append('<text x="24" y="30" class="label" font-family="monospace" font-size="10.5" font-weight="500" letter-spacing="1.1">A LITTLE EVERY DAY</text>')
    # Keep tiny or empty headline counters off the card.
    metrics = [(total, "contributions"), (active, "active days")]
    metrics = [(value, label) for value, label in metrics if value >= 10]
    for index, (value, label) in enumerate(metrics):
        x = 24 + index * 207
        svg.append(f'<text x="{x}" y="86" font-size="46" font-weight="600" letter-spacing="-1.5">{value:,}</text>')
        svg.append(f'<text x="{x}" y="110" font-size="12.5" font-weight="450" class="muted">{label}</text>')
    if len(metrics) == 2:
        svg.append('<path d="M207 53v58" stroke="var(--border)"/>')
    if not metrics:
        svg.append('<text x="24" y="84" font-size="18">Finding my rhythm.</text>')
    maximum = max(weeks) or 1
    for index, count in enumerate(weeks):
        height = 52 * count / maximum
        x = 24 + index * 7.15
        svg.append(f'<rect x="{x:.2f}" y="{183-height:.2f}" width="4.5" height="{max(height, 1):.2f}" rx="1" fill="var(--bar)" opacity="{1 if count else .14}"/>')
    svg.append('<text x="24" y="217" class="muted" font-size="11" font-weight="450">Weekly contributions · past year</text>')
    svg.append('</svg>\n')
    return outline_svg("\n".join(svg)), {"contributions": total, "active_days": active}


def languages_card(totals):
    if not totals or sum(totals.values()) <= 0:
        raise ValueError("No language data returned; keep the previous cards.")
    total = sum(totals.values())
    top = totals.most_common(4)
    description = "; ".join(f"{name}: {amount/total:.1%}" for name, amount in top)
    svg = [svg_start("Languages in my repositories", description)]
    svg.append('<text x="24" y="30" class="label" font-family="monospace" font-size="10.5" font-weight="500" letter-spacing="1.1">LANGUAGES IN MY REPOS</text>')
    for index, (name, amount) in enumerate(top):
        y = 60 + index * 37
        ratio = amount / total
        svg.append(f'<text x="24" y="{y}" font-size="13" font-weight="500">{escape(name)}</text>')
        svg.append(f'<text x="396" y="{y}" text-anchor="end" font-size="12" font-weight="450" class="muted">{ratio:.1%}</text>')
        svg.append(f'<rect x="24" y="{y+8}" width="372" height="5" rx="2.5" fill="var(--track)"/>')
        svg.append(f'<rect x="24" y="{y+8}" width="{372*ratio:.2f}" height="5" rx="2.5" fill="var(--accent)" opacity="{1-index*.15}"/>')
    svg.append('<text x="24" y="217" class="muted" font-size="10.5" font-weight="450">Code bytes · public, non-fork repos · top 4</text>')
    svg.append('</svg>\n')
    return outline_svg("\n".join(svg))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default="KINGKK-007")
    parser.add_argument("--output", type=Path, default=Path("assets/stats"))
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9-]+", args.username):
        parser.error("Invalid GitHub username")
    token = os.environ.get("GH_PROFILE_TOKEN")
    calendar = ContributionCalendar()
    calendar.feed(fetch(f"https://github.com/users/{args.username}/contributions"))
    repositories = public_repositories(args.username, token)
    totals = language_totals(repositories, token)
    activity, summary = activity_card(calendar.counts, date.today())
    languages = languages_card(totals)
    # Fetch and validate everything before replacing either card.
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "activity.svg").write_text(activity)
    (args.output / "languages.svg").write_text(languages)
    print(json.dumps({**summary, "top_languages": dict(totals.most_common(4))}))


if __name__ == "__main__":
    main()
