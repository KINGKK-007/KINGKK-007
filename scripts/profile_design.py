#!/usr/bin/env python3
"""Generate the self-contained charcoal-and-mint profile artwork."""

import argparse
from copy import deepcopy
from hashlib import sha256
from html import escape
from math import ceil, exp, sin, cos, pi
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from typography import outline_svg, text_width

ROOT = Path(__file__).resolve().parents[1] / 'assets'
NS = 'http://www.w3.org/2000/svg'
MONO, SANS = 'JetBrains Mono, monospace', 'Manrope, sans-serif'
BG, SURFACE, SURFACE_END = '#0f1613', '#131c17', '#0f1613'
INK, INK2, MUTED, DIM = '#e6edf3', '#c3ccd5', '#a7b2bc', '#8795a1'
MINT, BRIGHT, DEEP, BORDER = '#9bd8bc', '#c5f5df', '#315d46', '#2b3a32'
CHIP = '#15211b'
SPACING = (4, 8, 12, 16, 24, 32)
CARD_GAP, SECTION_GAP = 16, 40
RADIUS, CHIP_RADIUS, ICON_RADIUS, SOCIAL_RADIUS = 12, 8, 10, 10
WIDTHS = {'desktop': 800, 'compact': 600, 'mobile': 320}
PROFILE = {
    'availability_text': None,
    'include_aic': True,  # Anonymous HTTP 200 verified before adding this card.
    'hero': {
        'label': '/ KINGKK-007', 'name': 'Kanav Kumar',
        'tagline': 'Backend. Systems. Applied AI.',
        'mobile_tagline': ['Backend. Systems.', 'Applied AI.'],
        'college': 'CSE @ IIIT Bangalore · 2028',
        'description': 'CSE at IIIT Bangalore, class of 2028. Backend engineering, systems and applied AI. A mint planet above a restrained contour landscape.',
        'alt': '/ KINGKK-007. Kanav Kumar. Backend. Systems. Applied AI. CSE @ IIIT Bangalore · 2028.',
    },
    'socials': [('linkedin', 'LinkedIn'), ('email', 'Email'), ('x', 'X'), ('instagram', 'Instagram'), ('dev', 'DEV')],
    'featured': {
        'title': 'PitchPerfect', 'label': 'FEATURED PROJECT',
        'description': 'Mock interviews tailored to your résumé and role, with live audio/video feedback and post-session reports.',
        'stack': ['Next.js', 'FastAPI', 'PostgreSQL', 'Redis', 'Docker', 'Gemini', 'Whisper'],
        'mobile_stack': ['Next.js', 'FastAPI', 'PostgreSQL', 'Redis', 'Docker'],
        'action': 'Explore the repository', 'illustration_caption': 'listen / reflect / improve',
    },
    'projects': [
        ('smartcampus', 'SmartCampus', 'Course enrollment, notifications and campus events.', ['Spring Boot', 'MySQL', 'Flyway'], 'campus', 'https://github.com/Jdsb06/SmartCampus'),
        ('signbridge', 'SignBridge 3D', 'Gesture recognition and 3D avatars for accessible communication.', ['Next.js', 'Gemini', 'MediaPipe'], 'gesture', 'https://github.com/DayalGupta03/Sign_Bridge1'),
        ('mini-swiggy', 'Mini-Swiggy', 'Concurrent orders, worker processes and safe file access in C.', ['C', 'pthreads', 'TCP', 'IPC'], 'network', 'https://github.com/KINGKK-007/Mini-Swiggy'),
        ('aic', 'AIC', 'OpenEnv incident-response environment with verifiable rewards and 0-1 task graders.', ['FastAPI', 'OpenEnv', 'TRL GRPO', 'Unsloth'], 'response', 'https://github.com/COolAlien35/AIC'),
    ],
    'project_actions': [('source', 'View source', False), ('source-half', 'Source', True), ('demo-half', 'Live demo', True)],
    'toolkit_title': 'My toolkit',
    'technologies': [
        ('Languages', [('java', 'Java'), ('cpp', 'C++'), ('c', 'C'), ('python', 'Python'), ('sql', 'SQL'), ('javascript', 'JavaScript')]),
        ('Frameworks', [('spring', 'Spring Boot'), ('react', 'React'), ('nextjs', 'Next.js'), ('fastapi', 'FastAPI')]),
        ('Tools & data', [('docker', 'Docker'), ('postgresql', 'PostgreSQL'), ('mysql', 'MySQL'), ('git', 'Git'), ('linux', 'Linux'), ('postman', 'Postman')]),
    ],
    'milestones_title': 'Along the way',
    'milestones': [
        ('HackXIOS 2K25', '7 / 2,300', 'Ranked 7th overall'),
        ('Meta PyTorch OpenEnv', 'Finalist', '12,000+ teams · 2026'),
        ('Novo Nordisk GBS', 'Pre-finalist', 'Hackathon 2025'),
    ],
    'footer': ['> Always curious. Always building.', 'Ctrl + Z is a lifestyle.'],
    'sections': [('selected-work', 'SELECTED WORK', 'Selected work'), ('toolkit', 'MY TOOLKIT', 'My toolkit'), ('on-github', 'ON GITHUB', 'On GitHub'), ('along-the-way', 'ALONG THE WAY', 'Along the way')],
    'stats': {
        'activity_title': 'GitHub activity', 'languages_title': 'Repository languages',
        'contributions_label': 'Contributions', 'active_days_label': 'Active days',
        'provenance': 'Public activity · past 12 months · updated {snapshot_date}',
        'language_caption': 'Owned public repos · code bytes', 'other_label': 'Other',
        'trail_title': 'Contribution trail',
        'trail_desc': 'An animated snake follows the actual GitHub contribution calendar for the past year. Empty days remain empty. Open the full graphic to inspect the annual pattern.',
        'period_label': 'PAST YEAR', 'less_label': 'Less', 'more_label': 'More',
        'open_graph_label': 'Open full graph',
    },
}
# Stable aliases for scripts importing the old public design API.
PROJECTS = [tuple(p[:3]) + (' · '.join(p[3]), p[4]) for p in PROFILE['projects'] if p[0] != 'aic']
TECH = PROFILE['technologies']
SECTIONS = PROFILE['sections']


def start(width, height, title, desc=None):
    return f'<svg xmlns="{NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc or title)}</desc>'


def text(value, x, y, size=16, color=INK, weight=500, mono=False, anchor='start', spacing=0):
    return f'<text x="{x}" y="{y}" font-family="{MONO if mono else SANS}" font-size="{size}" font-weight="{weight}" letter-spacing="{spacing}" text-anchor="{anchor}" fill="{color}">{escape(value)}</text>'


def top_highlight(width, uid='card'):
    return f'<defs><linearGradient id="{uid}-edge"><stop stop-color="{MINT}" stop-opacity="0"/><stop offset=".5" stop-color="{MINT}" stop-opacity=".3"/><stop offset="1" stop-color="{MINT}" stop-opacity="0"/></linearGradient></defs><path d="M12 1H{width-12}" stroke="url(#{uid}-edge)"/>'


def card(width, height, featured=False, radius=RADIUS, uid='card'):
    return (f'<defs><linearGradient id="{uid}-surface" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{SURFACE}"/><stop offset="1" stop-color="{SURFACE_END}"/></linearGradient></defs>'
            f'<rect data-card="true" x=".5" y=".5" width="{width-1}" height="{height-1}" rx="{radius}" fill="url(#{uid}-surface)" stroke="{MINT if featured else BORDER}" stroke-width="1" stroke-opacity="{.45 if featured else 1}"/>' + top_highlight(width, uid))


def frame(width, height, featured=False):
    return card(width, height, featured)


def chip(label, x, y, width=None, logo=None, size=13):
    allowance = 44 if logo else 20
    width = width or ceil(text_width(label, size, 500, 'sans' if logo else 'mono')+allowance)
    result=f'<g data-chip="{escape(label, quote=True)}"><rect x="{x}" y="{y}" width="{width}" height="32" rx="{CHIP_RADIUS}" fill="{CHIP}" stroke="{BORDER}"/>'
    if logo:result+=tech_logo(logo,x+10,y+7)
    result+=text(label,x+(36 if logo else 10),y+21,size,INK2,500,mono=not logo)
    return result+'</g>'


def flow(items, max_width, size=13, gap=8, logos=False):
    """Return label/x/y/width rows with no split labels or trailing separators."""
    x=y=0; placements=[]
    for item in items:
        logo,label=item if logos else (None,item)
        width=ceil(text_width(label,size,500,'sans' if logos else 'mono')+(44 if logos else 20))
        if width>max_width:raise ValueError(f'Chip {label!r} exceeds {max_width}px')
        if x and x+width>max_width:x=0;y+=32+gap
        placements.append((logo,label,x,y,width));x+=width+gap
    return placements, y+32 if placements else 0


def chips(items,x,y,max_width,size=13,gap=8,logos=False):
    placements,height=flow(items,max_width,size,gap,logos)
    return ''.join(chip(label,x+xx,y+yy,width,logo,size) for logo,label,xx,yy,width in placements),height


def icon_tile(kind,x,y):
    return f'<rect x="{x}" y="{y}" width="36" height="36" rx="{ICON_RADIUS}" fill="{MINT}" fill-opacity=".1"/>'+icon(kind,x+7,y+7,22,MINT)


def action_pill(label,x,y,width=None):
    width=width or ceil(text_width(label,14,600)+48)
    return (f'<g data-action="{escape(label, quote=True)}"><rect x="{x}" y="{y}" width="{width}" height="36" rx="18" fill="{CHIP}" stroke="{MINT}" stroke-opacity=".45"/>'
            +text(label,x+14,y+23,14,BRIGHT,600)+arrow(x+width-25,y+13,BRIGHT)+'</g>')


def section_rule(x,y,width,uid,light=False,reverse=False):
    color='#c9d6ce' if light else BORDER
    a,b=('0','1') if reverse else ('1','0')
    return f'<defs><linearGradient id="{uid}"><stop stop-color="{color}" stop-opacity="{a}"/><stop offset="1" stop-color="{color}" stop-opacity="{b}"/></linearGradient></defs><path d="M{x} {y}h{width}" stroke="url(#{uid})"/>'


def write(relative, svg):
    path=ROOT/relative;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(outline_svg(svg+'</svg>'))


def wrap(value,width,size=16,weight=450,mono=False):
    lines=[];line='';separator=' · ' if mono else ' '
    for word in value.split(separator):
        candidate=separator.join([line,word]) if line else word
        if line and text_width(candidate,size,weight,'mono' if mono else 'sans')>width:lines.append(line);line=word
        else:line=candidate
    if line:lines.append(line)
    return lines


def icon(kind,x,y,size=24,color=MINT):
    paths={
        'network':'<rect x="8" y="2" width="8" height="6" rx="1"/><path d="M12 8v5M4 13h16M4 13v3m16-3v3"/><rect x="1" y="16" width="6" height="6" rx="1"/><rect x="17" y="16" width="6" height="6" rx="1"/>',
        'gesture':'<path d="M7 12V5a1.5 1.5 0 0 1 3 0v6-8a1.5 1.5 0 0 1 3 0v8-6a1.5 1.5 0 0 1 3 0v8-5a1.5 1.5 0 0 1 3 0v7c0 4-3 7-7 7-3 0-5-2-7-5l-2-3a1.5 1.5 0 0 1 2-2l2 2"/>',
        'campus':'<path d="m2 8 10-6 10 6M4 9h16M4 21h16M7 10v8m5-8v8m5-8v8M2 22h20"/>',
        'trophy':'<path d="M6 3h12v7a6 6 0 0 1-12 0zm0 3H2v3a5 5 0 0 0 5 5m11-8h4v3a5 5 0 0 0-5 5m-5 2v5m-5 0h10"/>',
        'mic':'<rect x="8" y="2" width="8" height="13" rx="4"/><path d="M5 10v2a7 7 0 0 0 14 0v-2m-7 9v3m-4 0h8"/>',
        'response':'<path d="M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6zM8 12h3l2-4v8l2-4h2"/>',
    }
    return f'<g transform="translate({x} {y}) scale({size/24})" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{paths[kind]}</g>'


def arrow(x,y,color=MINT):
    return f'<path d="m{x} {y+9} 9-9m-9 0h9v9" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'


def motion_style(extra=''):
    return ('<style>@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}.cursor{animation:blink 1s step-end infinite}'
            '@keyframes twinkle{0%,100%{opacity:.35}50%{opacity:.8}}.star{animation:twinkle 7s ease-in-out infinite}'
            '@keyframes pulse{0%,100%{opacity:.5}50%{opacity:1}}.status-dot{animation:pulse 3s ease-in-out infinite}'
            +extra+'@media(prefers-reduced-motion:reduce){.cursor,.star,.status-dot{animation:none!important;opacity:1}}</style>')


def tech_logo(name,x,y):
    root=ET.parse(ROOT/'badges'/f'{name}.svg').getroot()
    logo=deepcopy(root.find(f'{{{NS}}}svg'))
    logo.set('x',str(x));logo.set('y',str(y));logo.set('width','18');logo.set('height','18')
    logo.set('preserveAspectRatio','xMidYMid meet');logo.set('fill',MUTED)
    # Derive tight optical bounds from actual geometry, then use equal 1px margins.
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.svgLib.path import parse_path
    bounds=[]
    for element in logo.iter():
        if element.tag==f'{{{NS}}}path' and element.get('d'):
            pen=BoundsPen(None);parse_path(element.get('d'),pen)
            if pen.bounds:bounds.append(pen.bounds)
        if element.get('fill') not in (None,'none'):element.set('fill',MUTED)
        if element.get('stroke') not in (None,'none'):element.set('stroke',MUTED)
    # Explicit circles/ellipses/rects need their bounds too (mail/LinkedIn/SQL).
    for e in logo.iter():
        tag=e.tag.rsplit('}',1)[-1]
        if tag=='rect':
            xx,yy=float(e.get('x',0)),float(e.get('y',0));bounds.append((xx,yy,xx+float(e.get('width',0)),yy+float(e.get('height',0))))
        elif tag in ('circle','ellipse'):
            cx,cy=float(e.get('cx',0)),float(e.get('cy',0));rx=float(e.get('r',e.get('rx',0)));ry=float(e.get('r',e.get('ry',0)));bounds.append((cx-rx,cy-ry,cx+rx,cy+ry))
    if bounds:
        left=min(b[0] for b in bounds);top=min(b[1] for b in bounds);right=max(b[2] for b in bounds);bottom=max(b[3] for b in bounds)
        side=max(right-left,bottom-top)*1.125;logo.set('viewBox',f'{(left+right-side)/2:g} {(top+bottom-side)/2:g} {side:g} {side:g}')
    # LinkedIn's negative-space mark must stay dark against its pale square.
    if name=='linkedin':
        for e in logo.findall(f'{{{NS}}}g'):e.set('fill',BG)
        for e in logo.findall(f'{{{NS}}}g/*'):
            if e.get('fill'):e.set('fill',BG)
    return ET.tostring(logo,encoding='unicode')



def badge(relative, label, mark=None, accent=False):
    width = max(72, ceil(text_width(label, 12, 500, 'mono') + 52))
    svg = start(width, 36, label) + frame(width, 36)
    if accent:
        svg += f'<rect x=".5" y=".5" width="{width-1}" height="35" rx="10" fill="#17271e" stroke="#456b55"/>'
    if mark:
        root = ET.parse(ROOT / 'badges' / f'{mark}.svg').getroot()
        logo = root.find(f'{{{NS}}}svg')
        logo.set('x', '12'); logo.set('y', '9'); logo.set('width', '18'); logo.set('height', '18')
        logo.set('fill', MUTED)
        svg += ET.tostring(logo, encoding='unicode')
    svg += text(label, 39 if mark else 15, 23, 12, BRIGHT if accent else MUTED, mono=True)
    if not mark:
        svg += arrow(width-21, 13)
    write(relative, svg)

def socials():
    for name, label in [('linkedin', 'LinkedIn'), ('email', 'Email'), ('x', 'X'), ('instagram', 'Instagram'), ('dev', 'DEV')]:
        badge(f'badges/{name}.svg', label, name, True)

def banners():
    hero=PROFILE['hero']
    for dark in (True,False):
        suffix='dark' if dark else 'light'
        for mode,w in WIDTHS.items():
            mobile=mode=='mobile';compact=mode=='compact';h=288 if mobile else 280
            cx,cy,r=(270,78,29) if mobile else ((500,113,43) if compact else (660,115,55))
            rx,ry=(43,14) if mobile else ((69,22) if compact else (91,29))
            svg=start(w,h,hero['name'],hero['description'])+card(w,h)+motion_style()
            svg+=f'<defs><clipPath id="scene"><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="12"/></clipPath><pattern id="dots" width="16" height="16" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r=".7" fill="{MINT}"/></pattern><radialGradient id="glow"><stop stop-color="{MINT}" stop-opacity=".1"/><stop offset="1" stop-color="{MINT}" stop-opacity="0"/></radialGradient><linearGradient id="planet" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{BRIGHT}"/><stop offset=".5" stop-color="{MINT}"/><stop offset="1" stop-color="{DEEP}"/></linearGradient></defs>'
            svg+=f'<g clip-path="url(#scene)"><rect x="1" y="1" width="{w-2}" height="{h-2}" fill="url(#dots)" opacity=".04"/>'
            for i in range(3):svg+=f'<circle cx="{(22 if mobile else 28)+i*10}" cy="20" r="2" fill="{MINT}" opacity="{.35+i*.12}"/>'
            svg+=f'<ellipse cx="{cx}" cy="{cy}" rx="{r*3}" ry="{r*2.4}" fill="url(#glow)"/>'
            stars=[(212,48),(301,147),(237,126)] if mobile else ([(460,50),(563,179),(414,88)] if compact else [(590,52),(756,174),(543,89)])
            for i,(sx,sy) in enumerate(stars):svg+=f'<circle class="star" cx="{sx}" cy="{sy}" r="1.1" fill="{MINT}" style="animation-duration:{6+i}s;animation-delay:-{i*2}s"/>'
            svg+=f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" transform="rotate(-26 {cx} {cy})" fill="none" stroke="{MINT}" stroke-opacity=".35"/><circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#planet)"/>'
            angle=-26*pi/180;lx,ly=cx-rx*cos(angle),cy-rx*sin(angle);rrx,rry=cx+rx*cos(angle),cy+rx*sin(angle)
            svg+=f'<path d="M{lx:.2f} {ly:.2f}A{rx} {ry} -26 0 0 {rrx:.2f} {rry:.2f}" fill="none" stroke="{MINT}" stroke-opacity=".75" stroke-width="1.1"/>'
            left=180 if mobile else (360 if compact else 450)
            for row in range(12):
                points=[]
                for col in range(65):
                    xx=left+col*(w-left)/64;yy=h-22+row*3-20*exp(-((xx-(w-55))/42)**2)+7*sin((xx-left)/48);points.append(f'{xx:.1f},{yy:.1f}')
                svg+=f'<polyline points="{" ".join(points)}" fill="none" stroke="{MINT}" stroke-width=".7" opacity="{.16-row*.006:.3f}"/>'
            x=22 if mobile else 28;label_y=53
            svg+=text(hero['label'],x,label_y,13,MUTED,500,mono=True,spacing=.4)
            cursor_x=x+text_width(hero['label'],13,500,'mono',spacing=.4)+8
            svg+=f'<rect class="cursor" x="{cursor_x}" y="{label_y-11}" width="4" height="13" fill="{MINT}"/>'
            name_size=40 if mobile else (46 if compact else 59);name_y=140 if mobile else 135
            svg+=text(hero['name'],x-2,name_y,name_size,INK,750,spacing=-1.9)
            name_width=text_width(hero['name'],name_size,750,spacing=-1.9)
            svg+=text('.',x+name_width,name_y,name_size,MINT,750)
            for i,line in enumerate(hero['mobile_tagline'] if mobile else [hero['tagline']]):svg+=text(line,x,(178 if mobile else 179)+i*25,17.5 if mobile else (18 if compact else 20),INK2)
            svg+=text(hero['college'],x,245 if mobile else 230,14 if mobile else 16,MUTED)
            if PROFILE['availability_text']:
                label=PROFILE['availability_text'];lines=wrap(label,w-2*x-24,13,500)
                # This opt-in status occupies its own appended row, below college.
                yy=h+8;status_h=30+18*len(lines)
                svg+=f'<circle class="status-dot" cx="{x+4}" cy="{yy+12}" r="3" fill="{MINT}"/>'
                for i,line in enumerate(lines):svg+=text(line,x+16,yy+16+i*18,13,MINT)
                # Extend the viewBox/card together rather than clipping optional copy.
                svg=svg.replace(f'height="{h}" viewBox="0 0 {w} {h}"',f'height="{h+status_h}" viewBox="0 0 {w} {h+status_h}"',1)
                svg=svg.replace(f'width="{w-1}" height="{h-1}" rx="12"',f'width="{w-1}" height="{h+status_h-1}" rx="12"',1)
                svg=svg.replace(f'height="{h-2}" rx="12"',f'height="{h+status_h-2}" rx="12"',1)
            svg+='</g>';write(f'header-{suffix}{"" if mode=="desktop" else "-"+mode}.svg',svg)

def featured():
    desc = 'Mock interviews tailored to your résumé and role, with live audio/video feedback and post-session reports.'
    for mode in ('desktop','compact','mobile'):
        mobile, compact=mode=='mobile',mode=='compact'
        w = 320 if mobile else (600 if compact else 800)
        size = 17.5 if mobile else 17
        desc_lines=wrap(desc,w-44 if mobile else (544 if compact else 470),size)
        desc_y=114 if mobile else 117
        stack_y=desc_y+25*len(desc_lines)+18 if mobile else 183
        h=stack_y+66 if mobile else 244
        svg = start(w, h, 'PitchPerfect — featured project', desc + ' Next.js, FastAPI, PostgreSQL, Redis and Docker. Open the project repository.') + frame(w, h, True)
        x = 22 if mobile else 28
        svg += text('FEATURED PROJECT', x, 32, 13, MINT, mono=True, spacing=.35)
        svg += text('PitchPerfect', x, 78 if mobile else 83, 35 if mobile else 37, INK, 700, spacing=-1)
        y = desc_y
        for line in desc_lines:
            svg += text(line, x, y, size, MUTED, 450); y += 25
        y = stack_y
        svg += text('Next.js · FastAPI · PostgreSQL', x, y, 13.5, MUTED, mono=True)
        svg += text('Redis · Docker' if mobile else 'Redis · Docker · Gemini · Whisper', x, y+22, 13.5, MUTED, mono=True)
        svg += text('Explore the repository', x, h-17, 13, BRIGHT, 600)
        svg += arrow(x+157, h-27, BRIGHT)
        if mobile or compact:
            svg += icon('mic', w-48, 21, 24)
        else:
            # An interview-specific illustration, not a fake product screenshot.
            svg += '<rect x="551" y="40" width="219" height="164" rx="9" fill="#0d1511" stroke="#28352f"/>'
            svg += '<path d="M551 67h219" stroke="#28352f"/>'
            for i in range(3):svg += f'<circle cx="{568+i*9}" cy="54" r="2" fill="#5c7969"/>'
            svg += icon('mic', 586, 93, 31, MINT)
            for i, bar in enumerate([8, 15, 25, 11, 34, 22, 40, 18, 29, 12]):
                svg += f'<rect x="{634+i*10}" y="{116-bar/2}" width="3" height="{bar}" rx="1.5" fill="{MINT}" opacity=".75"/>'
            svg += text('listen / reflect / improve', 660, 172, 11.5, MUTED, mono=True, anchor='middle')
        write(f'projects/pitchperfect{"" if mode=="desktop" else "-"+mode}.svg', svg)

def projects():
    # Native GitHub table cells frame each card and keep its two real links together.
    # Their 28px total padding gives 400px desktop / 254px compact card widths.
    for mode, w in [('desktop',372), ('compact',226), ('mobile',280), ('narrow',210)]:
        suffix = '' if mode=='desktop' else '-'+mode
        inset = 18 if w>=280 else 12
        desc_size, stack_size = 16.5, 14
        description_rows = max(len(wrap(p[2],w-2*inset,desc_size)) for p in PROJECTS)
        stack_rows = max(len(wrap(p[3],w-2*inset,stack_size,500,mono=True)) for p in PROJECTS)
        stack_y = 80+(description_rows-1)*24+33
        height = stack_y+(stack_rows-1)*22+23
        for filename, title, desc, stack, kind in PROJECTS:
            svg = start(w,height,title,desc+' '+stack+'. Open the repository.')
            svg += f'<rect width="{w}" height="{height}" fill="{BG}"/>'
            svg += icon(kind,inset,20,22,MUTED)
            svg += text(title,inset+32,39,24 if w>=280 else 21,INK,650,spacing=-.45)
            for i,line in enumerate(wrap(desc,w-2*inset,desc_size)):
                svg += text(line,inset,80+i*24,desc_size,MUTED,450)
            for i,line in enumerate(wrap(stack,w-2*inset,stack_size,500,mono=True)):
                svg += text(line,inset,stack_y+i*22,stack_size,MUTED,mono=True)
            write(f'projects/{filename}{suffix}.svg',svg)

        for name,label,half in [('source','View source',False),('source-half','Source',True),('demo-half','Live demo',True)]:
            width = w/2 if half else w
            svg = start(width,46,label,'Open the live SignBridge demo.' if name=='demo-half' else 'Open the project repository.')
            svg += f'<rect width="{width}" height="46" fill="{BG}"/><path d="M0 .5h{width}" stroke="{BORDER}"/>'
            if name=='demo-half':svg += f'<path d="M.5 0v46" stroke="{BORDER}"/>'
            x = 12 if half else inset
            svg += text(label,x,29,14,MINT,600)
            svg += arrow(width-22,19,MINT)
            write(f'projects/{name}{suffix}.svg',svg)

def toolkit():
    for mode in ('desktop','compact','mobile'):
        mobile, compact=mode=='mobile',mode=='compact'
        w = 320 if mobile else (600 if compact else 800)
        category_columns = [2 if mobile else (2 if compact and len(items)==4 else 3 if compact else len(items)) for _,items in TECH]
        left = 20 if mobile else 24
        top = 0
        row_heights = [54+ceil(len(items)/columns)*32 for (_,items),columns in zip(TECH,category_columns)]
        h = sum(row_heights)
        svg = start(w, h, 'My toolkit', '; '.join(category + ': ' + ', '.join(label for _,label in items) for category,items in TECH)) + frame(w, h)
        for row,(category,items) in enumerate(TECH):
            columns = category_columns[row]
            svg += text(category.upper(),left,top+28,14,MINT if row==1 else MUTED,mono=True,spacing=.15)
            if columns == len(items):
                widths = [25 + text_width(label, 16, 550 if row==1 else 450) for _, label in items]
                gap = (w - 2*left - sum(widths)) / (len(items) - 1)
                x = left
                for (name, label), width in zip(items, widths):
                    y = top + 46
                    svg += tech_logo(name, round(x), y)
                    svg += text(label, round(x + 25), y + 14, 16, INK, 550 if row==1 else 450)
                    x += width + gap
            else:
                cell = (w-2*left)/columns
                for i,(name,label) in enumerate(items):
                    x = left+(i%columns)*cell
                    y = top+46+(i//columns)*32
                    svg += tech_logo(name,x,y)
                    svg += text(label,x+25,y+14,16,INK,550 if row==1 else 450)
            top += row_heights[row]
            if row<2:svg += f'<path d="M{left} {top}h{w-2*left}" stroke="{BORDER}"/>'
        write(f'editorial/toolkit{"" if mode=="desktop" else "-"+mode}.svg',svg)

def milestones():
    data=[('hackxios','HackXIOS 2K25','7 / 2,300','Ranked 7th overall',True),
          ('openenv','Meta PyTorch OpenEnv','Finalist','12,000+ teams · 2026',False),
          ('novo-nordisk','Novo Nordisk GBS','Pre-finalist','Hackathon 2025',False)]
    for name,title,result,caption,main in data:
        svg=start(260,120,title,result+'. '+caption)+frame(260,120)
        svg+=icon('trophy',20,19,22,MINT if main else MUTED)
        svg+=text(title,50,35,13.4,INK,600)
        svg+=text(result,20,77,27 if main else 24,BRIGHT if main else INK,650,spacing=-.7)
        svg+=text(caption,20,104,12.5,MUTED,450)
        if main:svg+=f'<path d="M1 20v80" stroke="{MINT}" stroke-width="2"/>'
        write(f'milestones/{name}.svg',svg)

def footer():
    svg=start(800,80,'Always curious. Always building.','A quiet terminal sign-off. Ctrl + Z is a lifestyle.')
    svg+=f'<rect width="800" height="80" fill="{BG}"/><path d="M0 .5h800" stroke="{BORDER}"/>'
    svg+=text('> Always curious. Always building.',400,38,15,INK,mono=True,anchor='middle')
    svg+=f'<rect x="563" y="26" width="5" height="14" fill="{MINT}" opacity=".75"/>'
    svg+=text('Ctrl + Z is a lifestyle.',400,62,12.5,MUTED,mono=True,anchor='middle')
    write('editorial/footer.svg',svg)
    compact=start(600,80,'Always curious. Always building.','Ctrl + Z is a lifestyle.')
    compact+=f'<rect width="600" height="80" fill="{BG}"/><path d="M0 .5h600" stroke="{BORDER}"/>'
    compact+=text('> Always curious. Always building.',300,38,15,INK,mono=True,anchor='middle')
    compact+=f'<rect x="463" y="26" width="5" height="14" fill="{MINT}" opacity=".75"/>'
    compact+=text('Ctrl + Z is a lifestyle.',300,62,12.5,MUTED,mono=True,anchor='middle')
    write('editorial/footer-compact.svg',compact)
    mobile=start(360,80,'Always curious. Always building.','Ctrl + Z is a lifestyle.')
    mobile+=f'<rect width="360" height="80" fill="{BG}"/><path d="M0 .5h360" stroke="{BORDER}"/>'
    mobile+=text('> Always curious. Always building.',180,38,14.5,INK,mono=True,anchor='middle')
    mobile+=text('Ctrl + Z is a lifestyle.',180,62,12.5,MUTED,mono=True,anchor='middle')
    write('editorial/footer-mobile.svg',mobile)

def sections():
    for filename,label,desc in PROFILE['sections']:
        for mode,w in WIDTHS.items():
            for dark in (True,False):
                suffix='' if dark else '-light';variant='' if mode=='desktop' else '-'+mode
                accent=MINT if dark else '#35745a';ink=INK if dark else '#182b23'
                width=text_width('> '+label,13,600,'mono',spacing=.4);left=(w-width)/2
                svg=start(w,44,desc)
                rule_w=max(0,left-16)
                svg+=section_rule(0,22,rule_w,'left-rule',not dark,True)+section_rule(w-rule_w,22,rule_w,'right-rule',not dark)
                svg+=text('>',left,27,13,accent,600,mono=True,spacing=.4)
                svg+=text(label,left+text_width('> ',13,600,'mono',spacing=.4),27,13,ink,600,mono=True,spacing=.4)
                write(f'sections/{filename}{suffix}{variant}.svg',svg)

def version_readme_assets():
    """Give changed design assets fresh URLs without renaming editable files."""
    readme = ROOT.parent / 'README.md'

    def version(match):
        prefix, relative, suffix = match.groups()
        # The workflow refreshes dated data snapshots independently of the design.
        if relative.startswith('./assets/stats/'):
            return prefix + relative + suffix
        fingerprint = sha256((ROOT.parent / relative).read_bytes()).hexdigest()[:10]
        return f'{prefix}{relative}?v={fingerprint}{suffix}'

    source = readme.read_text()
    revised = re.sub(r'((?:src|srcset)=")(\./assets/[^"?]+)(?:\?v=[^"]+)?(")', version, source)
    if revised != source:
        readme.write_text(revised)

def main():
    generators={'socials':socials,'banners':banners,'featured':featured,'projects':projects,'toolkit':toolkit,'milestones':milestones,'footer':footer,'sections':sections}
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--only',choices=generators)
    args=parser.parse_args()
    for name,generate in generators.items():
        if not args.only or args.only==name:generate()
    version_readme_assets()
    print('Generated '+(args.only or 'all static profile artwork')+'.')

if __name__ == '__main__':
    main()
