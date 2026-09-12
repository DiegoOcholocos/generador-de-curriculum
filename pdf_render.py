"""
PDF generation via Playwright, rendering the exact same HTML/CSS as the
browser live preview (templates/cv_render.html + static/cv.css).

This replaces the old reportlab-based pdf_generator.py, which drew the CV by
hand on a fixed-size canvas with no page breaks: any content that didn't fit
on one A4 page was silently dropped (see the `if my < 55: break` guards that
used to live there). Because a real browser engine performs the print layout
here, long CVs now correctly flow onto additional pages instead of losing
content.
"""
import asyncio
import os
import re
from playwright.async_api import async_playwright

from themes import resolve_theme, i18n_for, level_label

BASE_DIR = os.path.dirname(__file__)
CSS_PATH = os.path.join(BASE_DIR, 'static', 'cv.css')

_PHOTO_RE = re.compile(r'^data:image/(png|jpe?g|webp);base64,[A-Za-z0-9+/=]+$', re.I)

A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
DESIGN_WIDTH_PX = 600
# Scale factor from the design's CSS-pixel mockup (600px wide, matching the
# on-screen preview) up to A4 at the standard 96 CSS-px/inch used for print.
PDF_SCALE = round((A4_WIDTH_MM * 96 / 25.4) / DESIGN_WIDTH_PX, 4)

_DO_NOT_SHOW = {'— No mostrar —', '- Do not show -'}


def _safe_photo(photo):
    if photo and _PHOTO_RE.match(photo):
        return photo
    return None


def _skill_level(sk):
    try:
        return max(1, min(5, int(sk.get('level') or sk.get('level_speak') or 3)))
    except (TypeError, ValueError):
        return 3


def build_context(data):
    t = i18n_for(data.get('lang', 'es'))
    cfg = resolve_theme(data.get('template', ''))
    personal = data.get('personal', {}) or {}

    name = (personal.get('name') or '').strip() or t['def_name']
    initials = ''.join(p[0].upper() for p in name.split()[:2] if p)

    contacts = []
    if personal.get('email'):
        contacts.append(('✉', personal['email']))
    if personal.get('phone'):
        contacts.append(('✆', personal['phone']))
    addr = personal.get('address') or personal.get('location')
    if addr:
        contacts.append(('⌖', addr))
    if personal.get('linkedin'):
        contacts.append(('in', personal['linkedin']))
    if personal.get('website'):
        contacts.append(('◈', personal['website']))
    if personal.get('dni'):
        contacts.append(('🪪', 'DNI ' + personal['dni']))
    if personal.get('birthdate'):
        contacts.append(('📅', personal['birthdate']))
    if personal.get('nationality'):
        contacts.append(('🌎', personal['nationality']))
    gender = personal.get('gender', '')
    if gender and gender not in _DO_NOT_SHOW:
        contacts.append(('👤', gender))

    skills = [{'name': sk.get('name', ''), 'level': _skill_level(sk)}
              for sk in data.get('skills', []) if sk.get('name')]

    languages = [{'name': lg.get('name', ''),
                  'level_label': level_label(lg.get('level') or lg.get('speak') or 'B2')}
                 for lg in data.get('languages', []) if lg.get('name')]

    experience = [{
        'position': e.get('position', ''), 'company': e.get('company', ''),
        'start_date': e.get('start_date', ''), 'end_date': e.get('end_date') or t['present'],
        'description': e.get('description', ''),
    } for e in data.get('experience', [])]

    education = [{
        'degree': e.get('degree', ''), 'institution': e.get('institution', ''),
        'start_date': e.get('start_date', ''), 'end_date': e.get('end_date') or t['present'],
    } for e in data.get('education', [])]

    courses = [{'name': c.get('name', ''), 'institution': c.get('institution', ''),
                'year': c.get('year', '')} for c in data.get('courses', []) if c.get('name')]

    recommendations = [{'name': r.get('name', ''), 'position': r.get('position', ''),
                         'text': r.get('text', '')} for r in data.get('recommendations', [])
                        if r.get('name') or r.get('text')]

    projects = [{'name': p.get('name', ''), 'description': p.get('description', ''),
                 'tech': p.get('tech', ''), 'link': p.get('link', '')}
                for p in data.get('projects', []) if p.get('name')]

    return {
        'lang': data.get('lang', 'es'), 't': t, 'cfg': cfg,
        'name': name, 'title': personal.get('title', ''), 'initials': initials,
        'photo_src': _safe_photo(personal.get('photo')),
        'contacts': contacts, 'summary': (data.get('summary') or '').strip(),
        'skills': skills, 'languages': languages, 'experience': experience,
        'education': education, 'courses': courses, 'recommendations': recommendations,
        'projects': projects, 'hobbies': (data.get('hobbies') or '').strip(),
    }


async def _render_pdf_async(html: str) -> bytes:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page(viewport={'width': DESIGN_WIDTH_PX, 'height': 900})
            await page.set_content(html, wait_until='load')
            pdf_bytes = await page.pdf(
                width=f'{A4_WIDTH_MM}mm', height=f'{A4_HEIGHT_MM}mm',
                scale=PDF_SCALE, print_background=True,
                margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'},
            )
        finally:
            await browser.close()
    return pdf_bytes


def generate_cv_pdf(env, data):
    """Render data with cv_render.html and print it to PDF bytes via Playwright.

    Uses Playwright's *async* API driven by `asyncio.run()`, not the sync
    API. The sync API is implemented on top of greenlet, which switches
    stacks between the caller's thread and Playwright's internal driver
    thread — under Werkzeug's dev server this failed with "cannot switch to
    a different thread (which happens to have exited)" on every single
    request (not just repeated ones), which pointed at a greenlet
    incompatibility with this environment's Python version rather than
    anything about reusing state across requests. `asyncio.run()` sidesteps
    greenlet entirely by giving each call its own fresh event loop.
    """
    with open(CSS_PATH, encoding='utf-8') as f:
        css = f.read()
    context = build_context(data)
    html = env.get_template('cv_render.html').render(css=css, **context)
    return asyncio.run(_render_pdf_async(html))
