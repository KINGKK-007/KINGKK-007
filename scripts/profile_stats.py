#!/usr/bin/env python3
"""Render small, theme-aware profile cards from public GitHub data."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta, datetime, timezone
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

from typography import outline_svg, text_width
from profile_design import start, text, frame, PROFILE, BG, SURFACE, INK, INK2, MUTED, DIM, MINT, BRIGHT, BORDER
import xml.etree.ElementTree as ET


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


def language_totals(repositories, token, username):
    eligible = [repo for repo in repositories if not repo["fork"] and repo["size"]
                and repo["name"].casefold() != username.casefold()]

    def languages(repo):
        return json.loads(fetch(repo["languages_url"], token))

    totals = Counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(languages, eligible):
            totals.update(result)
    return totals



def summarize(counts, today, totals):
    recent = {day: count for day, count in counts.items() if today-timedelta(days=364) <= day <= today}
    if len(recent) < 350:
        raise ValueError('Incomplete contribution calendar; preserve the last valid snapshot.')
    if not totals or sum(totals.values()) <= 0:
        raise ValueError('Empty repository language response; preserve the last valid snapshot.')
    total_bytes = sum(totals.values())
    # Preserve the existing selection and counting definition. The renderer adds
    # the unselected remainder as Other rather than renormalizing these shares.
    languages = [(name, value/total_bytes) for name, value in totals.most_common() if value/total_bytes >= .02][:4]
    return {'snapshot_date': today.isoformat(),
            'calendar_start':min(counts).isoformat(), 'calendar_end':max(counts).isoformat(),
            'contributions':sum(recent.values()),
            'active_days':sum(value>0 for value in recent.values()),
            'languages':languages, 'language_basis':'Code bytes in owned public non-fork project repos; excludes the profile repository.'}


def language_segments(summary):
    """Keep real language shares and expose every unselected byte as Other."""
    selected = [(name, float(share)) for name, share in summary['languages']]
    if any(share < 0 for _, share in selected):
        raise ValueError('Repository language shares cannot be negative.')
    remainder = 1 - sum(share for _, share in selected)
    if remainder < -1e-10:
        raise ValueError('Repository language shares exceed the full code-byte total.')
    return selected + [(PROFILE['stats']['other_label'], max(0, remainder))]


def language_percentages(segments):
    """Round displayed tenths of a percent together so the legend totals 100%."""
    exact = [share * 1000 for _, share in segments]
    rounded = [int(value) for value in exact]
    remaining = 1000 - sum(rounded)
    for index in sorted(range(len(exact)), key=lambda i: exact[i] - rounded[i], reverse=True)[:remaining]:
        rounded[index] += 1
    return [value / 10 for value in rounded]


def wrapped_lines(value, width, size=13, weight=450):
    lines, line = [], ''
    for word in value.split():
        candidate = f'{line} {word}' if line else word
        if line and text_width(candidate, size, weight) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def overview(summary, mobile=False, compact=False):
    copy = PROFILE['stats']
    show_activity = summary['contributions'] >= 10 and summary['active_days'] >= 10
    w = 320 if mobile else (600 if compact else 800)
    h = 456 if mobile and show_activity else 244
    pad = 22 if mobile else 28
    gap = 24
    panel_width = w - 2 * pad if mobile or not show_activity else (w - 2 * pad - gap) / 2
    activity_width = panel_width
    if compact and show_activity and not mobile:
        # Reserve a readable gap between TypeScript and its percentage at 600px.
        activity_width -= 12
        panel_width += 12
    segments = language_segments(summary)
    percentages = language_percentages(segments)
    title = copy['activity_title'] + ' / ' + copy['languages_title'] if show_activity else copy['languages_title']
    description = '; '.join(f'{name}: {share:.1%}' for name, share in segments) + '. ' + summary['language_basis']
    if show_activity:
        description = (f"{summary['contributions']} contributions across {summary['active_days']} active days in the past year. "
                       + description)
    svg = start(w, h, title, description) + frame(w, h)
    if show_activity:
        svg += text(copy['activity_title'], pad, 38, 17, INK, 650)
        tile_width = (activity_width - 16) / 2
        metrics = [(copy['contributions_label'], summary['contributions']),
                   (copy['active_days_label'], summary['active_days'])]
        for index, (label, value) in enumerate(metrics):
            x = pad + index * (tile_width + 16)
            svg += f'<g data-stat-tile="{escape(label)}"><rect x="{x}" y="64" width="{tile_width}" height="92" rx="12" fill="none" stroke="{BORDER}"/>'
            svg += text(f'{value:,}', x + 12, 108, 35, MINT, 650, spacing=-.6)
            svg += text(label, x + 12, 140, 13, MUTED, 450)
            svg += '</g>'
        provenance = copy['provenance'].format(snapshot_date=summary['snapshot_date'])
        for index, line in enumerate(wrapped_lines(provenance, activity_width)):
            svg += text(line, pad, 188 + index * 18, 13, MUTED, 450)
        if mobile:
            svg += f'<path d="M{pad} 232h{w-2*pad}" stroke="{BORDER}"/>'
        else:
            midpoint = pad + activity_width + gap / 2
            svg += f'<path d="M{midpoint} 28v188" stroke="{BORDER}"/>'
    language_x = pad if mobile or not show_activity else pad + activity_width + gap
    language_y = 232 if mobile and show_activity else 0
    svg += text(copy['languages_title'], language_x, language_y + 38, 17, INK, 650)
    bar_y = language_y + 66
    # Clip the whole segmented strip, so only its outer corners are rounded.
    svg += f'<defs><clipPath id="language-bar"><rect x="{language_x}" y="{bar_y}" width="{panel_width}" height="8" rx="5"/></clipPath></defs>'
    svg += '<g clip-path="url(#language-bar)" data-language-bar="true">'
    ramp = [MINT, '#7db598', '#609278', '#46725a', '#315d46']
    cursor = language_x
    for index, (name, share) in enumerate(segments):
        segment_width = panel_width * share
        color = ramp[min(index, len(ramp)-1)]
        svg += f'<rect x="{cursor:.8f}" y="{bar_y}" width="{segment_width:.8f}" height="8" fill="{color}" data-language="{escape(name)}" data-share="{share:.16g}"/>'
        cursor += segment_width
    svg += '</g>'
    column_width = (panel_width - 16) / 2
    for index, ((name, _), percent) in enumerate(zip(segments, percentages)):
        x = language_x + index % 2 * (column_width + 16)
        y = language_y + 105 + index // 2 * 28
        color = ramp[min(index, len(ramp)-1)]
        svg += f'<circle cx="{x+4}" cy="{y-4}" r="4" fill="{color}"/>'
        svg += text(name, x + 14, y, 13, INK2, 500)
        svg += text(f'{percent:.1f}%', x + column_width, y, 13, MUTED, 450, anchor='end')
    for index, line in enumerate(wrapped_lines(copy['language_caption'], panel_width)):
        svg += text(line, language_x, language_y + 200 + index * 18, 13, DIM, 450)
    return outline_svg(svg + '</svg>')


def contribution_frame(source, first_date, last_date, mobile=False, compact=False):
    copy = PROFILE['stats']
    original = ET.fromstring(source)
    namespace = '{http://www.w3.org/2000/svg}'
    cells = [element for element in original.iter(namespace + 'rect') if 'c' in element.get('class', '').split()]
    if not cells:
        raise ValueError('The snake source contains no contribution calendar cells.')
    # snk createStack is an animation progress meter, not contribution data.
    # Remove its segments before framing, leaving every calendar/snake node intact.
    for parent in original.iter():
        for child in list(parent):
            if 'u' in child.get('class', '').split():
                parent.remove(child)
    w, h = (320, 172) if mobile else ((600, 220) if compact else (800, 244))
    pad = 22 if mobile else 28
    svg = start(w, h, copy['trail_title'], copy['trail_desc']) + frame(w, h)
    svg += text(copy['trail_title'], pad, 38, 16.5 if mobile else 17, INK, 650)
    svg += text(copy['period_label'], w-pad, 38, 13, MUTED, mono=True, anchor='end', spacing=.4)
    # Keep the true cell coordinates; discard the old stack's empty bottom band.
    # snk cells are 12px on a 16px pitch; the snake enters at y=-16px.
    first_cell_x = min(float(cell.get('x', 0)) for cell in cells)
    view_x = first_cell_x - 2
    view_right = max(float(cell.get('x', 0)) + float(cell.get('width', 12)) for cell in cells) + 2
    view_y = -20
    view_bottom = max(float(cell.get('y', 0)) + float(cell.get('height', 12)) for cell in cells) + 4
    view_w, view_h = view_right - view_x, view_bottom - view_y
    graph_width = w - 2 * pad
    graph_y = 72
    original.set('viewBox', f'{view_x:g} {view_y:g} {view_w:g} {view_h:g}')
    original.set('x', str(pad)); original.set('y', str(graph_y))
    original.set('width', str(graph_width)); original.set('height', str(graph_width * view_h / view_w))
    original.set('data-calendar', 'true')
    for style in original.iter(namespace + 'style'):
        palette = ':root{--cb:#263a2d;--cs:#c5f5df;--ce:#16221c;--c0:#16221c;--c1:#294535;--c2:#427056;--c3:#6ba287;--c4:#9bd8bc}'
        css = re.sub(r':root\{[^}]*\}', palette, style.text or '')
        css = re.sub(r'@keyframes u[\w-]+\{(?:[^{}]|\{[^{}]*\})*\}', '', css)
        css = re.sub(r'\.u(?:\.u[\w-]+)?\{[^}]*\}', '', css)
        # No animation means the original contribution intensities remain visible.
        # Hide the stationary snake instead of covering the first calendar cell.
        css += '@media(prefers-reduced-motion:reduce){.c{animation:none!important}.s{animation:none!important;opacity:0}}'
        style.text = css
    previous_month = None
    last_label_right = -1e9
    scale = graph_width / view_w
    for day_index in range((last_date - first_date).days + 1):
        day = first_date + timedelta(days=day_index)
        if day.month != previous_month:
            column = day_index // 7
            x = pad + (first_cell_x + column * 16 - view_x) * scale
            label = day.strftime('%b')
            label_width = text_width(label, 13, 450)
            # A mobile annual calendar cannot fit twelve 13px month labels.
            # Keep actual month-column origins and omit only colliding labels.
            if x >= last_label_right + 8 and x + label_width <= w - pad:
                svg += text(label, x, 66, 13, MUTED, 450)
                last_label_right = x + label_width
            previous_month = day.month
    svg += ET.tostring(original, encoding='unicode')
    less_width = text_width(copy['less_label'], 13, 450)
    more_width = text_width(copy['more_label'], 13, 450)
    legend_width = less_width + 12 + 75 + 12 + more_width
    legend_x = (w-legend_width)/2 if mobile else w-pad-legend_width
    legend_y = h-24
    svg += text(copy['less_label'], legend_x, legend_y, 13, MUTED, 450)
    ramp_x = legend_x + less_width + 12
    for index, color in enumerate(['#16221c', '#294535', '#427056', '#6ba287', MINT]):
        svg += f'<rect x="{ramp_x+index*16}" y="{legend_y-11}" width="11" height="11" rx="2" fill="{color}"/>'
    svg += text(copy['more_label'], ramp_x+75+12, legend_y, 13, MUTED, 450)
    return outline_svg(svg + '</svg>')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username',default='KINGKK-007')
    parser.add_argument('--output',type=Path,default=Path('assets/stats'))
    parser.add_argument('--snake-dir',type=Path,help='Directory containing freshly generated snake-dark.svg.')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9-]+',args.username):parser.error('Invalid GitHub username')
    token=os.environ.get('GH_PROFILE_TOKEN')
    calendar=ContributionCalendar()
    calendar.feed(fetch(f'https://github.com/users/{args.username}/contributions'))
    repos=public_repositories(args.username,token)
    totals=language_totals(repos,token,args.username)
    today=datetime.now(timezone.utc).date()
    summary=summarize(calendar.counts,today,totals)
    source_dir=args.snake_dir or args.output
    snake=(source_dir/'snake-dark.svg').read_text()
    outputs={
        'overview.svg':overview(summary), 'overview-mobile.svg':overview(summary,True),
        'overview-compact.svg':overview(summary,compact=True),
        'contributions.svg':contribution_frame(snake,min(calendar.counts),max(calendar.counts)),
        'contributions-mobile.svg':contribution_frame(snake,min(calendar.counts),max(calendar.counts),True),
        'contributions-compact.svg':contribution_frame(snake,min(calendar.counts),max(calendar.counts),compact=True),
        'snapshot.json':json.dumps(summary,indent=2)+'\n',
    }
    # Fetch, validate and render all data before replacing the previous snapshot.
    args.output.mkdir(parents=True,exist_ok=True)
    for filename,content in outputs.items():(args.output/filename).write_text(content)
    print(json.dumps(summary))


if __name__=='__main__':main()
