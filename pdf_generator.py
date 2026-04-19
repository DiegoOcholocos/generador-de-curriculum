"""
CVDiego8 Pro — PDF Generator v5 (i18n)
Fixes:
- Multi-language support (EN/ES)
- Datos personales: etiqueta completa + valor en línea de abajo si no entra
- Competencias: 2 columnas con barras alineadas, sin truncamiento
- Layout más holgado y consistente
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io, base64, tempfile, os

W, H = A4

THEMES = {
    'clasica_azul':  ('#2c3e50', '#2980b9', '#2d2d2d', '#888888'),
    'moderna_roja':  ('#1a1a2e', '#e94560', '#2d2d2d', '#888888'),
    'elegante_oro':  ('#1b1b1b', '#c9a84c', '#1b1b1b', '#888888'),
    'oceano':        ('#0d3b5e', '#00b4d8', '#1a2a3a', '#777777'),
    'bosque':        ('#1b4332', '#74c69d', '#1b2e22', '#777777'),
    'carbon':        ('#1c1c1c', '#ff6b35', '#1a1a1a', '#888888'),
    'aurora':        ('#2b2d42', '#ef233c', '#2b2d42', '#888888'),
    'violeta':       ('#4a235a', '#c77dff', '#2d1b38', '#999999'),
    'minimalista':   ('#f5f5f5', '#222222', '#222222', '#999999'),
    'pastel_rosa':   ('#fde8ec', '#c9485b', '#3a1520', '#aaaaaa'),
}
LIGHT_SB = {'minimalista', 'pastel_rosa'}
OLD_NAMES = {
    'moderna':'moderna_roja','clasica':'clasica_azul','elegante':'elegante_oro',
    'creativa':'violeta','oceano':'oceano','bosque':'bosque','carbon':'carbon',
    'aurora':'aurora','minimalista':'minimalista','pastel':'pastel_rosa'
}

I18N = {
    'es': {
        'personal': 'Datos Personales', 'email': 'Email', 'phone': 'Teléfono',
        'address': 'Dirección', 'linkedin': 'LinkedIn', 'website': 'GitHub/Web',
        'dni': 'DNI', 'birthdate': 'Nacimiento', 'nationality': 'Nacion.',
        'gender': 'Género', 'skills': 'Competencias', 'languages': 'Idiomas',
        'interests': 'Intereses', 'profile': 'Perfil', 'experience': 'Experiencia',
        'education': 'Formación', 'courses': 'Cursos y Certificaciones',
        'recommendations': 'Recomendaciones', 'present': 'Presente',
        'def_name': 'Tu Nombre'
    },
    'en': {
        'personal': 'Personal Details', 'email': 'Email', 'phone': 'Phone',
        'address': 'Address', 'linkedin': 'LinkedIn', 'website': 'GitHub/Web',
        'dni': 'ID Number', 'birthdate': 'Birthdate', 'nationality': 'Nationality',
        'gender': 'Gender', 'skills': 'Skills', 'languages': 'Languages',
        'interests': 'Interests', 'profile': 'Profile', 'experience': 'Experience',
        'education': 'Education', 'courses': 'Courses & Certifications',
        'recommendations': 'Recommendations', 'present': 'Present',
        'def_name': 'Your Name'
    }
}

def _c(h):       return colors.HexColor(h)
def _s(v, d=''): return str(v).strip() if v else d

def generate_cv_pdf(data):
    tpl = data.get('template', 'clasica_azul')
    tpl = OLD_NAMES.get(tpl, tpl)
    if tpl not in THEMES: tpl = 'clasica_azul'
    sb, acc, txt, mut = THEMES[tpl]
    light = tpl in LIGHT_SB
    lang = data.get('lang', 'es')
    buf = io.BytesIO()
    _draw(buf, data, tpl, sb, acc, txt, mut, light, lang)
    buf.seek(0)
    return buf

# ── helpers ───────────────────────────────────────────────────────────────────

def _wrap(cv, text, x, y, mw, font, sz, col, lh=None):
    if not text: return y
    lh = lh or sz + 3
    cv.setFont(font, sz); cv.setFillColor(col)
    words = str(text).split(); line = ''
    for w in words:
        t = (line + ' ' + w).strip()
        if cv.stringWidth(t, font, sz) <= mw: line = t
        else:
            if y < 30: return y
            cv.drawString(x, y, line); y -= lh; line = w
    if line and y >= 30: cv.drawString(x, y, line); y -= lh
    return y

def _seg_bar(cv, x, y, lv, w, acc, bg):
    """Draw 5-segment skill bar."""
    if w <= 0: return
    seg = (w - 4) / 5
    for i in range(5):
        cv.setFillColor(_c(acc if i < lv else bg))
        cv.roundRect(x + i*(seg+1), y, seg, 4, 1, fill=1, stroke=0)

def _level_label(v):
    if not v: return 'B2'
    raw = str(v).lower().split('–')[0].split('-')[0].strip().split()[0]
    MAP = {'nativo':'Nativo','native':'Nativo','c2':'C2','c1':'C1',
           'b2':'B2','b1':'B1','a2':'A2','a1':'A1',
           '5':'Nativo','4':'C1','3':'B2','2':'B1','1':'A2'}
    return MAP.get(raw, raw.upper()[:6])

def _decode_photo(b64):
    if not b64: return None
    try:
        hdr, dat = b64.split(',',1) if ',' in b64 else ('',b64)
        suf = '.png' if 'png' in hdr else '.jpg'
        raw = base64.b64decode(dat)
        f = tempfile.NamedTemporaryFile(delete=False, suffix=suf)
        f.write(raw); f.close()
        return f.name
    except: return None

def _split_lines(cv, text, font, sz, max_w):
    """Split text into lines fitting max_w."""
    if not text: return ['']
    if cv.stringWidth(text, font, sz) <= max_w:
        return [text]
    words = text.split(); lines = []; line = ''
    for w in words:
        t = (line + ' ' + w).strip()
        if cv.stringWidth(t, font, sz) <= max_w: line = t
        else:
            if line: lines.append(line)
            line = w
    if line: lines.append(line)
    return lines or [text]

# ── main draw ─────────────────────────────────────────────────────────────────

def _draw(buf, data, tpl, sb_col, acc_col, txt_col, mut_col, light, lang):
    t = I18N.get(lang, I18N['es'])
    personal = data.get('personal', {})
    summary  = _s(data.get('summary',''))
    exps     = data.get('experience', [])
    edus     = data.get('education', [])
    skills   = data.get('skills', [])
    langs    = data.get('languages', [])
    courses  = data.get('courses', [])
    recs     = data.get('recommendations', [])
    hobbies  = _s(data.get('hobbies',''))

    cv  = canvas.Canvas(buf, pagesize=A4)
    SW  = 190        # sidebar width
    SM  = 13         # sidebar margin
    SIW = SW - SM*2  # sidebar inner width

    sb_txt    = colors.white if not light else _c('#1a1a1a')
    sb_dim    = _c('#bbbbbb') if not light else _c('#666666')
    sb_bar_bg = '#ffffff22' if not light else '#cccccc'
    sb_line   = _c('#ffffff18') if not light else _c('#cccccc')

    # ── Backgrounds ───────────────────────────────────────────────────────────
    cv.setFillColor(_c(sb_col)); cv.rect(0, 0, SW, H, fill=1, stroke=0)
    cv.setFillColor(colors.white); cv.rect(SW, 0, W-SW, H, fill=1, stroke=0)

    # ── Avatar ────────────────────────────────────────────────────────────────
    name     = _s(personal.get('name'), t['def_name'])
    initials = ''.join(p[0].upper() for p in name.split()[:2])
    title_p  = _s(personal.get('title'))
    ar = 42
    ax = SW // 2
    ay = int(H - 16 - ar)

    # white circle background (so photo bg is always white inside circle)
    cv.setFillColor(colors.white)
    cv.circle(ax, ay, ar, fill=1, stroke=0)

    photo_path = _decode_photo(personal.get('photo'))
    drew_photo = False
    if photo_path:
        try:
            cv.saveState()
            pp = cv.beginPath(); pp.circle(ax, ay, ar)
            cv.clipPath(pp, stroke=0, fill=0)
            cv.drawImage(photo_path, ax-ar, ay-ar, ar*2, ar*2,
                         preserveAspectRatio=True, anchor='c')
            cv.restoreState()
            drew_photo = True
        except: pass
        try: os.unlink(photo_path)
        except: pass

    if not drew_photo:
        cv.setFillColor(_c(acc_col)); cv.circle(ax, ay, ar, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont('Helvetica-Bold', 17)
        cv.drawCentredString(ax, ay-6, initials)

    # accent ring
    cv.setStrokeColor(_c(acc_col)); cv.setLineWidth(2.5)
    cv.circle(ax, ay, ar+3, fill=0, stroke=1)

    # name below avatar
    sy = ay - ar - 12
    cv.setFillColor(sb_txt); cv.setFont('Helvetica-Bold', 9.5)
    for ln in _split_lines(cv, name, 'Helvetica-Bold', 9.5, SIW):
        cv.drawCentredString(SW//2, sy, ln); sy -= 11

    # title
    cv.setFillColor(_c(acc_col)); cv.setFont('Helvetica', 8)
    for ln in _split_lines(cv, title_p, 'Helvetica', 8, SIW):
        cv.drawCentredString(SW//2, sy, ln); sy -= 10
    sy -= 4

    # thin divider
    cv.setStrokeColor(sb_line); cv.setLineWidth(0.4)
    cv.line(SM, sy, SW-SM, sy); sy -= 10

    # ── Sidebar section helpers ───────────────────────────────────────────────

    def sb_sec(title):
        nonlocal sy
        if sy < 50: return
        cv.setFillColor(_c(acc_col)); cv.setFont('Helvetica-Bold', 7.5)
        cv.drawString(SM, sy, title.upper()); sy -= 3
        cv.setStrokeColor(sb_line); cv.setLineWidth(0.3)
        cv.line(SM, sy, SW-SM, sy); sy -= 9

    def sb_field(label, value):
        """Draw label bold, then value — on same line if fits, else next line."""
        nonlocal sy
        if sy < 40 or not value: return
        lbl = label + ':'
        lbl_w = cv.stringWidth(lbl, 'Helvetica-Bold', 7.5) + 4
        val_w = cv.stringWidth(value, 'Helvetica', 7.5)

        cv.setFillColor(_c(acc_col)); cv.setFont('Helvetica-Bold', 7.5)
        cv.drawString(SM, sy, lbl)

        if lbl_w + val_w <= SIW:
            # fits on same line
            cv.setFillColor(sb_txt); cv.setFont('Helvetica', 7.5)
            cv.drawString(SM + lbl_w, sy, value)
            sy -= 10
        else:
            # label on first line, value wrapped on subsequent lines
            sy -= 10
            sy = _wrap(cv, value, SM + 6, sy, SIW - 6,
                       'Helvetica', 7.5, sb_txt, 9)
        sy -= 1

    # ── Datos personales ──────────────────────────────────────────────────────
    sb_sec(t['personal'])
    if personal.get('email'):       sb_field(t['email'],       personal['email'])
    if personal.get('phone'):       sb_field(t['phone'],    personal['phone'])
    addr = personal.get('address') or personal.get('location','')
    if addr:                        sb_field(t['address'],   addr)
    if personal.get('linkedin'):    sb_field(t['linkedin'],    personal['linkedin'])
    if personal.get('website'):     sb_field(t['website'],  personal['website'])
    if personal.get('dni'):         sb_field(t['dni'],         personal['dni'])
    if personal.get('birthdate'):   sb_field(t['birthdate'],  personal['birthdate'])
    if personal.get('nationality'): sb_field(t['nationality'],     personal['nationality'])
    g = personal.get('gender','')
    if g and g not in ('','— No mostrar —', '- Do not show -'):
        sb_field(t['gender'], g)
    sy -= 3

    # ── Competencias — 2 columnas ─────────────────────────────────────────────
    if skills and sy > 60:
        sb_sec(t['skills'])
        col_w  = (SIW - 8) // 2   # width per column
        bar_w  = col_w - 2        # bar width
        col2x  = SM + col_w + 8   # x of right column

        half   = (len(skills) + 1) // 2
        left_skills  = skills[:half]
        right_skills = skills[half:half*2]

        start_sy = sy
        # draw left column
        for sk in left_skills:
            if sy < 45: break
            lv = int(sk.get('level') or sk.get('level_speak') or 3)
            nm = _s(sk.get('name'))
            cv.setFillColor(sb_txt); cv.setFont('Helvetica', 7)
            # truncate name to fit column
            while nm and cv.stringWidth(nm, 'Helvetica', 7) > col_w - 2:
                nm = nm[:-1]
            cv.drawString(SM, sy, nm)
            _seg_bar(cv, SM, sy - 6, lv, bar_w, acc_col, sb_bar_bg)
            sy -= 20

        # draw right column from same starting y
        sy2 = start_sy
        for sk in right_skills:
            if sy2 < 45: break
            lv = int(sk.get('level') or sk.get('level_speak') or 3)
            nm = _s(sk.get('name'))
            cv.setFillColor(sb_txt); cv.setFont('Helvetica', 7)
            while nm and cv.stringWidth(nm, 'Helvetica', 7) > col_w - 2:
                nm = nm[:-1]
            cv.drawString(col2x, sy2, nm)
            _seg_bar(cv, col2x, sy2 - 6, lv, bar_w, acc_col, sb_bar_bg)
            sy2 -= 20

        sy = min(sy, sy2) - 3

    # ── Idiomas ───────────────────────────────────────────────────────────────
    if langs and sy > 50:
        sb_sec(t['languages'])
        for lg in langs:
            if sy < 40: break
            lv_str = _level_label(lg.get('level') or lg.get('speak') or 'B2')
            cv.setFillColor(sb_txt); cv.setFont('Helvetica', 8)
            cv.drawString(SM, sy, _s(lg.get('name')))
            tag_w = cv.stringWidth(lv_str, 'Helvetica-Bold', 7) + 8
            tx = SW - SM - tag_w
            cv.setFillColor(_c(acc_col))
            cv.roundRect(tx, sy-2, tag_w, 10, 2, fill=1, stroke=0)
            cv.setFillColor(colors.white); cv.setFont('Helvetica-Bold', 7)
            cv.drawString(tx+4, sy+1, lv_str)
            sy -= 13

    # ── Intereses ─────────────────────────────────────────────────────────────
    if hobbies and sy > 50:
        sy -= 2; sb_sec(t['interests'])
        sy = _wrap(cv, hobbies, SM, sy, SIW, 'Helvetica', 7.5, sb_dim, 10)

    # ── Recomendaciones (Sidebar) ─────────────────────────────────────────────
    if recs and sy > 60:
        sy -= 2; sb_sec(t['recommendations'])
        for rec in recs[:2]:
            if sy < 40: break
            rname = _s(rec.get('name'))
            rpos  = _s(rec.get('position'))
            rtxt  = _s(rec.get('text'))
            if not rname and not rtxt: continue
            cv.setFillColor(sb_txt); cv.setFont('Helvetica-Bold', 7.5)
            cv.drawString(SM, sy, rname); sy -= 9
            if rpos:
                cv.setFillColor(_c(acc_col)); cv.setFont('Helvetica-Oblique', 7)
                cv.drawString(SM, sy, rpos); sy -= 8
            if rtxt:
                sy = _wrap(cv, f'"{rtxt}"', SM, sy, SIW, 'Helvetica', 7, sb_dim, 9)
            sy -= 5

    # ══════════════════════════════════════════════════════════════════════════
    # MAIN CONTENT
    # ══════════════════════════════════════════════════════════════════════════
    MX  = SW + 16
    MRX = W - 14
    MW  = MRX - MX
    my  = H - 20

    # Big name header
    cv.setFillColor(_c(txt_col)); cv.setFont('Helvetica-Bold', 20)
    # wrap long names
    for ln in _split_lines(cv, name, 'Helvetica-Bold', 20, MW):
        cv.drawString(MX, my, ln); my -= 16
    cv.setFillColor(_c(acc_col)); cv.setFont('Helvetica', 10)
    cv.drawString(MX, my, title_p); my -= 8
    cv.setStrokeColor(_c(acc_col)); cv.setLineWidth(1.5)
    cv.line(MX, my, MRX, my); my -= 13

    def m_sec(title):
        nonlocal my
        my -= 3
        cv.setFillColor(_c(acc_col)); cv.setFont('Helvetica-Bold', 9.5)
        cv.drawString(MX, my, title); my -= 4
        cv.setStrokeColor(_c(acc_col)); cv.setLineWidth(0.8)
        cv.line(MX, my, MRX, my); my -= 11

    def m_wrap(text, sz=8.5, bold=False, col=None, ind=0):
        nonlocal my
        font = 'Helvetica-Bold' if bold else 'Helvetica'
        c    = col if col else _c(txt_col)
        my   = _wrap(cv, text, MX+ind, my, MW-ind, font, sz, c, sz+3)

    # Perfil
    if summary:
        m_sec(t['profile'])
        m_wrap(summary, 8.5)

    # Experiencia
    if exps:
        m_sec(t['experience'])
        for exp in exps:
            if my < 55: break
            pos  = _s(exp.get('position'))
            co   = _s(exp.get('company'))
            sd   = _s(exp.get('start_date'))
            ed   = _s(exp.get('end_date'), t['present'])
            desc = _s(exp.get('description'))
            ds   = f"{sd} - {ed}"

            cv.setFont('Helvetica-Bold', 9.5); cv.setFillColor(_c(txt_col))
            cv.drawString(MX, my, pos)
            cv.setFont('Helvetica', 7.5); cv.setFillColor(_c(mut_col))
            cv.drawRightString(MRX, my, ds)
            my -= 12
            cv.setFont('Helvetica-Oblique', 8.5); cv.setFillColor(_c(acc_col))
            cv.drawString(MX, my, co); my -= 11
            if desc:
                my = _wrap(cv, desc, MX, my, MW, 'Helvetica', 8, _c('#444444'), 10)
            my -= 5

    # Formación
    if edus:
        m_sec(t['education'])
        for edu in edus:
            if my < 55: break
            cv.setFont('Helvetica-Bold', 9.5); cv.setFillColor(_c(txt_col))
            cv.drawString(MX, my, _s(edu.get('degree')))
            ds = f"{_s(edu.get('start_date'))} - { _s(edu.get('end_date'), t['present']) }"
            cv.setFont('Helvetica', 7.5); cv.setFillColor(_c(mut_col))
            cv.drawRightString(MRX, my, ds); my -= 12
            cv.setFont('Helvetica-Oblique', 8.5); cv.setFillColor(_c(acc_col))
            cv.drawString(MX, my, _s(edu.get('institution'))); my -= 11

    # Cursos
    if courses:
        m_sec(t['courses'])
        for co in courses:
            if my < 55: break
            cv.setFillColor(_c(acc_col)); cv.circle(MX+3, my+3, 2.5, fill=1, stroke=0)
            cv.setFont('Helvetica', 8.5); cv.setFillColor(_c(txt_col))
            cv.drawString(MX+10, my, _s(co.get('name')))
            yr = _s(co.get('year'))
            if yr:
                cv.setFont('Helvetica', 7.5); cv.setFillColor(_c(mut_col))
                cv.drawRightString(MRX, my, yr)
            my -= 11
            inst = _s(co.get('institution'))
            if inst:
                cv.setFont('Helvetica-Oblique', 7.5); cv.setFillColor(_c(mut_col))
                cv.drawString(MX+10, my, inst); my -= 10
            else:
                my -= 1

    cv.save()


def _split_lines(cv, text, font, sz, max_w):
    if not text: return ['']
    if cv.stringWidth(text, font, sz) <= max_w:
        return [text]
    words = text.split(); lines = []; line = ''
    for w in words:
        t = (line + ' ' + w).strip()
        if cv.stringWidth(t, font, sz) <= max_w: line = t
        else:
            if line: lines.append(line)
            line = w
    if line: lines.append(line)
    return lines or [text]
