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

from typography import outline_svg
from profile_design import start, text, frame, BG, SURFACE, INK, MUTED, MINT, BRIGHT, BORDER
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
    # The present distribution has four substantive languages (>=2%) and a long
    # tail below 2%. Keep that tail off the card without renormalizing the shares.
    languages = [(name, value/total_bytes) for name, value in totals.most_common() if value/total_bytes >= .02][:4]
    return {'snapshot_date': today.isoformat(),
            'calendar_start':min(counts).isoformat(), 'calendar_end':max(counts).isoformat(),
            'contributions':sum(recent.values()),
            'active_days':sum(value>0 for value in recent.values()),
            'languages':languages, 'language_basis':'Code bytes in owned public non-fork project repos; excludes the profile repository.'}


def overview(summary, mobile=False, compact=False):
    show_activity=summary['contributions']>=10 and summary['active_days']>=10
    w, h = (320, 456 if show_activity else 220) if mobile else ((600 if compact else 800), 220)
    card_width = 320 if mobile else ((w-16)/2 if show_activity else w)
    svg = start(w, h, 'GitHub activity and repository languages' if show_activity else 'Repository languages',
                (f"{summary['contributions']} contributions across {summary['active_days']} active days in the past year. " if show_activity else '')
                + '; '.join(f'{name}: {share:.1%}' for name,share in summary['languages'])
                + '. ' + summary['language_basis'])
    for index,panel in enumerate((0,1) if show_activity else (1,)):
        x, y = (0, index*236) if mobile else (index*(card_width+16), 0)
        svg += f'<g transform="translate({x} {y})">' + frame(card_width,220)
        svg += text('GitHub activity' if panel==0 else 'Repository languages',22,32,17,INK,650)
        if panel==0:
            metrics=[('Contributions',summary['contributions']),('Active days',summary['active_days'])]
            for i,(label,value) in enumerate(metrics):
                if value < 10:continue
                yy=87+i*51
                svg += text(label,22,yy-3,14.5,MUTED,450)
                svg += text(f'{value:,}',card_width-22,yy,29,MINT if i==0 else INK,650,anchor='end',spacing=-.6)
            svg += f'<path d="M22 105h{card_width-44}" stroke="{BORDER}"/>'
            svg += text('Past 12 months',22,179,12.5,MUTED,450)
            svg += text('Snapshot '+summary['snapshot_date'],22,201,14,MUTED,mono=True)
        else:
            for i,(name,share) in enumerate(summary['languages']):
                yy=60+i*35
                svg+=text(name,22,yy,14,INK,500)
                svg+=text(f'{share:.1%}',card_width-22,yy,12.5,MUTED,anchor='end')
                svg+=f'<rect x="22" y="{yy+8}" width="{card_width-44}" height="5" rx="2.5" fill="#21332a"/>'
                svg+=f'<rect x="22" y="{yy+8}" width="{(card_width-44)*share:.2f}" height="5" rx="2.5" fill="{MINT}" opacity="{1-i*.14}"/>'
            svg+=text('Owned public repos · code bytes',22,201,14,MUTED,450)
        svg+='</g>'
    return outline_svg(svg+'</svg>')


def contribution_frame(source, first_date, last_date, mobile=False, compact=False):
    original=ET.fromstring(source)
    w,h=(320,148) if mobile else ((600,210) if compact else (800,244))
    svg=start(w,h,'Contribution trail', 'An animated snake follows the actual GitHub contribution calendar for the past year. Empty days remain empty. Open the full graphic to inspect the annual pattern.')+frame(w,h)
    svg+=text('Contribution trail',16 if mobile else 22,28 if mobile else 31,16.5,INK,650)
    if not mobile:svg+=text('PAST YEAR',w-22,31,12.5,MUTED,mono=True,anchor='end')
    view_x,view_y,view_w,view_h=map(float,original.get('viewBox').split())
    graph_width=w-(20 if mobile else 32)
    original.set('x','10' if mobile else '16');original.set('y','37' if mobile else '47')
    original.set('width',str(graph_width));original.set('height',str(graph_width*view_h/view_w))
    # Keep the generated cells and their animation intact. Only frame and label it.
    for style in original.findall('{http://www.w3.org/2000/svg}style'):
        palette=':root{--cb:#263a2d;--cs:#c5f5df;--ce:#16221c;--c0:#16221c;--c1:#294535;--c2:#427056;--c3:#6ba287;--c4:#9bd8bc}'
        style.text=re.sub(r':root\{[^}]*\}',palette,style.text,count=1)
        style.text += '@media(prefers-reduced-motion:reduce){*{animation:none!important}}'
    if not mobile:
        # Mark real calendar boundaries on the same weekly columns as snk.
        previous_month=None
        for i in range((last_date-first_date).days+1):
            day=first_date+timedelta(days=i)
            if day.month!=previous_month:
                column=i//7
                if column<=52:
                    x=16+(column*16-view_x)*graph_width/view_w
                    svg+=text(day.strftime('%b'),x,51,13 if not compact else 12,MUTED,450)
                previous_month=day.month
    svg+=ET.tostring(original,encoding='unicode')
    if mobile:svg+=text('Past year · open full graph',16,132,14,MUTED,450)
    else:
        yy=h-16
        svg+=text('Less',w-174,yy,12,MUTED,450)
        for i,color in enumerate(['#16221c','#294535','#427056','#6ba287',MINT]):
            svg+=f'<rect x="{w-139+i*16}" y="{yy-10}" width="11" height="11" rx="2" fill="{color}"/>'
        svg+=text('More',w-53,yy,12,MUTED,450)
    return outline_svg(svg+'</svg>')


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
