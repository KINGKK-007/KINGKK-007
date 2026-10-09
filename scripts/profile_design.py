#!/usr/bin/env python3
"""Build the charcoal-and-mint profile assets from editable design sources."""

from html import escape
from hashlib import sha256
from math import ceil, exp, sin, cos, pi
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from typography import outline_svg, text_width

ROOT = Path(__file__).resolve().parents[1] / 'assets'
NS = 'http://www.w3.org/2000/svg'
MONO = 'JetBrains Mono, monospace'
SANS = 'Manrope, sans-serif'
BG, SURFACE, INK, MUTED = '#0d1117', '#111814', '#e6edf3', '#a7b2bc'
MINT, BRIGHT, BORDER = '#9bd8bc', '#c5f5df', '#28352f'

PROJECTS = [
    ('mini-swiggy', 'Mini-Swiggy', 'A concurrent order server with safe file access and worker processes.',
     'C · pthreads · TCP · IPC', 'network'),
    ('signbridge', 'SignBridge 3D', 'Gesture recognition and 3D avatars for accessible communication.',
     'Next.js · Gemini · MediaPipe', 'gesture'),
    ('smartcampus', 'SmartCampus', 'Course enrollment, notifications and campus events in one place.',
     'Spring Boot · MySQL · Flyway', 'campus'),
]
TECH = [
    ('Languages', [('java', 'Java'), ('c', 'C'), ('cpp', 'C++'), ('python', 'Python'), ('sql', 'SQL'), ('javascript', 'JavaScript')]),
    ('Frameworks', [('spring', 'Spring Boot'), ('react', 'React'), ('nextjs', 'Next.js'), ('fastapi', 'FastAPI')]),
    ('Tools & data', [('docker', 'Docker'), ('postgresql', 'PostgreSQL'), ('mysql', 'MySQL'), ('git', 'Git'), ('linux', 'Linux'), ('postman', 'Postman')]),
]


def start(width, height, title, desc=None):
    return f'<svg xmlns="{NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc or title)}</desc>'


def text(value, x, y, size=16, color=INK, weight=500, mono=False, anchor='start', spacing=0):
    return f'<text x="{x}" y="{y}" font-family="{MONO if mono else SANS}" font-size="{size}" font-weight="{weight}" letter-spacing="{spacing}" text-anchor="{anchor}" fill="{color}">{escape(value)}</text>'


def frame(width, height, featured=False):
    return f'<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="10" fill="{SURFACE}" stroke="{MINT if featured else BORDER}" stroke-opacity="{.6 if featured else 1}"/>'


def write(relative, svg):
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(outline_svg(svg + '</svg>'))


def wrap(value, width, size=16, weight=450):
    lines, line = [], ''
    for word in value.split():
        candidate = (line + ' ' + word).strip()
        if line and text_width(candidate, size, weight) > width:
            lines.append(line); line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def icon(kind, x, y, size=24, color=MINT):
    paths = {
        'network': '<rect x="8" y="2" width="8" height="6" rx="1"/><path d="M12 8v5M4 13h16M4 13v3m16-3v3"/><rect x="1" y="16" width="6" height="6" rx="1"/><rect x="17" y="16" width="6" height="6" rx="1"/>',
        'gesture': '<path d="M7 12V5a1.5 1.5 0 0 1 3 0v6-8a1.5 1.5 0 0 1 3 0v8-6a1.5 1.5 0 0 1 3 0v8-5a1.5 1.5 0 0 1 3 0v7c0 4-3 7-7 7-3 0-5-2-7-5l-2-3a1.5 1.5 0 0 1 2-2l2 2"/>',
        'campus': '<path d="m2 8 10-6 10 6M4 9h16M4 21h16M7 10v8m5-8v8m5-8v8M2 22h20"/>',
        'trophy': '<path d="M6 3h12v7a6 6 0 0 1-12 0zm0 3H2v3a5 5 0 0 0 5 5m11-8h4v3a5 5 0 0 1-5 5m-5 2v5m-5 0h10"/>',
        'mic': '<rect x="8" y="2" width="8" height="13" rx="4"/><path d="M5 10v2a7 7 0 0 0 14 0v-2m-7 9v3m-4 0h8"/>',
    }
    return f'<g transform="translate({x} {y}) scale({size/24})" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{paths[kind]}</g>'


def arrow(x, y, color=MINT):
    return f'<path d="m{x} {y+9} 9-9m-9 0h9v9" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'


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
        badge(f'badges/{name}.svg', label, name, name in ('linkedin', 'email'))
    badge('badges/signbridge-live.svg', 'SignBridge · Live demo')


def banners():
    for dark in (True, False):
        suffix = 'dark' if dark else 'light'
        bg = BG if dark else '#f7faf8'
        ink = INK if dark else '#182b23'
        muted = MUTED if dark else '#52665a'
        accent = MINT if dark else '#35745a'
        border = BORDER if dark else '#d5e1d9'
        for mode in ('desktop', 'compact', 'mobile'):
            mobile, compact = mode=='mobile', mode=='compact'
            w, h = (360, 270) if mobile else ((600,252) if compact else (800, 280))
            cx, cy, r = (300, 75, 34) if mobile else ((500,109,45) if compact else (660, 115, 55))
            rx, ry = (50, 16) if mobile else ((73,23) if compact else (91, 29))
            svg = start(w, h, 'Kanav Kumar — Ghost in the Terminal', 'CS at IIIT Bangalore, class of 2028. Backend engineering, systems and applied AI. A mint planet above a restrained contour landscape.')
            svg += f'<defs><clipPath id="frame"><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="12"/></clipPath><radialGradient id="glow"><stop stop-color="{accent}" stop-opacity=".1"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient><linearGradient id="planet" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{BRIGHT if dark else "#c4ddce"}"/><stop offset=".5" stop-color="{accent}"/><stop offset="1" stop-color="{ "#315d46" if dark else "#446c54"}"/></linearGradient></defs>'
            svg += f'<g clip-path="url(#frame)"><rect width="{w}" height="{h}" fill="{bg}"/><ellipse cx="{cx}" cy="{cy}" rx="{r*3}" ry="{r*2.4}" fill="url(#glow)"/>'
            stars=[(232, 25), (345, 135), (249, 122)] if mobile else ([(460,32),(564,168),(413,83)] if compact else [(590, 38), (756, 174), (543, 89), (735, 49)])
            for sx, sy in stars:
                svg += f'<circle cx="{sx}" cy="{sy}" r="1.1" fill="{muted}" opacity=".55"/>'
            svg += f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" transform="rotate(-26 {cx} {cy})" fill="none" stroke="{accent}" stroke-opacity=".35"/><circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#planet)"/>'
            angle = -26*pi/180
            left_point = (cx-rx*cos(angle), cy-rx*sin(angle))
            right_point = (cx+rx*cos(angle), cy+rx*sin(angle))
            svg += f'<path d="M{left_point[0]:.2f} {left_point[1]:.2f}A{rx} {ry} -26 0 0 {right_point[0]:.2f} {right_point[1]:.2f}" fill="none" stroke="{accent}" stroke-opacity=".75" stroke-width="1.1"/>'
            # Twelve crisp contours; no dense moire or decorative microtext.
            left = 210 if mobile else (360 if compact else 450)
            for row in range(12):
                points = []
                for col in range(65):
                    x = left + col*(w-left)/64
                    y = h-22+row*3-20*exp(-((x-(w-55))/42)**2)+7*sin((x-left)/48)
                    points.append(f'{x:.1f},{y:.1f}')
                svg += f'<polyline points="{" ".join(points)}" fill="none" stroke="{accent}" stroke-width=".7" opacity="{.16-row*.006:.3f}"/>'
            x = 22 if mobile else (28 if compact else 38)
            svg += text('> GHOST IN THE TERMINAL' if mobile else '> KINGKK-007 / GHOST IN THE TERMINAL', x, 34 if mobile else 43, 14 if mobile else 12.5, muted, mono=True, spacing=.3)
            name_size=40 if mobile else (46 if compact else 59)
            name_y=139 if mobile else (122 if compact else 128)
            svg += text('Kanav Kumar', x-2, name_y, name_size, ink, 750, spacing=-1.9)
            name_width = text_width('Kanav Kumar', name_size, 750, spacing=-1.9)
            svg += text('.', x-2+name_width+2, name_y, name_size, accent, 750)
            svg += text('Backend. Systems.' if mobile else 'Backend. Systems. Applied AI.', x, 175 if mobile else (161 if compact else 169), 17.5 if mobile else (18 if compact else 20), muted, 500)
            if mobile:
                svg += text('Applied AI.', x, 200, 17.5, muted, 500)
            svg += text('CS @ IIIT Bangalore · 2028', x, 238 if mobile else (216 if compact else 229), 14 if mobile else 16, muted, 500)
            svg += f'</g><rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="12" fill="none" stroke="{border}"/>'
            write(f'header-{suffix}{"" if mode=="desktop" else "-"+mode}.svg', svg)


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
        svg += text('FEATURED PROJECT', x, 32, 12, MINT, mono=True, spacing=.5)
        svg += text('PitchPerfect', x, 78 if mobile else 83, 35 if mobile else 37, INK, 700, spacing=-1)
        y = desc_y
        for line in desc_lines:
            svg += text(line, x, y, size, MUTED, 450); y += 25
        y = stack_y
        svg += text('Next.js · FastAPI · PostgreSQL', x, y, 12.5, MUTED, mono=True)
        svg += text('Redis · Docker' if mobile else 'Redis · Docker · Gemini · Whisper', x, y+21, 12.5, MUTED, mono=True)
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
    for filename, title, desc, stack, kind in PROJECTS:
        svg = start(260, 204, title, desc + ' ' + stack + '. Open the project repository.') + frame(260, 204)
        svg += icon(kind, 20, 18, 24, MUTED) + arrow(221, 21)
        svg += text(title, 20, 69, 19, INK, 650, spacing=-.35)
        y = 97
        for line in wrap(desc, 220, 14.5):
            svg += text(line, 20, y, 14.5, MUTED, 450); y += 20
        svg += text(stack, 20, 166, 11.5, MUTED, mono=True)
        svg += text('View source', 20, 191, 12.5, MINT, 600)
        write(f'projects/{filename}.svg', svg)


def tech_logo(name, x, y):
    root = ET.parse(ROOT / 'badges' / f'{name}.svg').getroot()
    logo = root.find(f'{{{NS}}}svg')
    logo.set('x', str(x)); logo.set('y', str(y)); logo.set('width', '18'); logo.set('height', '18'); logo.set('fill', MUTED)
    return ET.tostring(logo, encoding='unicode')


def toolkit():
    for mode in ('desktop','compact','mobile'):
        mobile, compact=mode=='mobile',mode=='compact'
        w, h = (320,334) if mobile else ((600,264) if compact else (800, 204))
        svg = start(w, h, 'My toolkit', '; '.join(category + ': ' + ', '.join(label for _,label in items) for category,items in TECH)) + frame(w, h)
        for row, (category, items) in enumerate(TECH):
            if mobile:
                top = (0,116,208)[row]
                svg += text(category.upper(), 20, top+25, 13, MINT if row==1 else MUTED, mono=True)
                cols = 2
                for i, (name, label) in enumerate(items):
                    x = 20 + (i%cols)*144
                    y = top+42+(i//cols)*24
                    svg += tech_logo(name,x,y)
                    svg += text(label,x+25,y+14,15,INK,550 if row==1 else 450)
                if row<2:svg += f'<path d="M20 {(112,204)[row]}h280" stroke="{BORDER}"/>'
            elif compact:
                top=(0,98,166)[row]
                svg+=text(category.upper(),24,top+(52 if row!=1 else 39),12,MINT if row==1 else MUTED,mono=True)
                if row==1:
                    widths=[25+text_width(label,14.5,550) for _,label in items]
                    gap=(424-sum(widths))/3
                    x=150
                    for (name,label),width in zip(items,widths):
                        svg+=tech_logo(name,x,top+25)+text(label,x+25,top+39,14.5,INK,550)
                        x+=width+gap
                else:
                    for i,(name,label) in enumerate(items):
                        x=150+(i%3)*143;y=top+24+(i//3)*31
                        svg+=tech_logo(name,x,y)+text(label,x+25,y+14,14.5,INK,450)
                if row<2:svg+=f'<path d="M24 {(98,166)[row]}h552" stroke="{BORDER}"/>'
            else:
                top = row*68
                svg += text(category.upper(),24,top+39,12,MINT if row==1 else MUTED,mono=True)
                widths = [25+text_width(label,14.5,550 if row==1 else 450) for _,label in items]
                gap = (600-sum(widths))/(len(items)-1)
                x=174
                for (name,label), width in zip(items,widths):
                    svg += tech_logo(name,x,top+25)
                    svg += text(label,x+25,top+39,14.5,INK,550 if row==1 else 450)
                    x += width+gap
                if row<2:svg += f'<path d="M24 {top+68}h752" stroke="{BORDER}"/>'
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
    socials(); banners(); featured(); projects(); toolkit(); milestones(); footer()
    version_readme_assets()
    print('Generated hero, featured work, project cards, grouped toolkit, achievements and footer.')


if __name__=='__main__':main()
