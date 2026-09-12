"""
Single source of truth for CV color themes and CV-field translations.

Both the browser preview (via TPLS, injected into index.html as JSON) and the
server-side PDF renderer (via cv_render.html) read from THEMES, so a theme can
no longer drift between what the user sees on screen and what ends up in the
PDF the way it used to (see the old OLD_NAMES compatibility shim this file
replaces).
"""

THEMES = [
    {'id': 'clasica_azul', 'label': 'Clásica',  'sb': '#2c3e50', 'acc': '#2980b9', 'light': False, 'layout': 'sidebar'},
    {'id': 'moderna_roja', 'label': 'Moderna',   'sb': '#1a1a2e', 'acc': '#e94560', 'light': False, 'layout': 'sidebar'},
    {'id': 'elegante_oro', 'label': 'Elegante',  'sb': '#1b1b1b', 'acc': '#c9a84c', 'light': False, 'layout': 'sidebar'},
    {'id': 'oceano',       'label': 'Océano',    'sb': '#0d3b5e', 'acc': '#00b4d8', 'light': False, 'layout': 'sidebar'},
    {'id': 'bosque',       'label': 'Bosque',    'sb': '#1b4332', 'acc': '#74c69d', 'light': False, 'layout': 'sidebar'},
    {'id': 'carbon',       'label': 'Carbón',    'sb': '#1c1c1c', 'acc': '#ff6b35', 'light': False, 'layout': 'sidebar'},
    {'id': 'aurora',       'label': 'Aurora',    'sb': '#2b2d42', 'acc': '#ef233c', 'light': False, 'layout': 'sidebar'},
    {'id': 'violeta',      'label': 'Violeta',   'sb': '#4a235a', 'acc': '#c77dff', 'light': False, 'layout': 'sidebar'},
    {'id': 'minimalista',  'label': 'Minimal',   'sb': '#f5f5f5', 'acc': '#222222', 'light': True,  'layout': 'sidebar'},
    {'id': 'pastel_rosa',  'label': 'Pastel',    'sb': '#fde8ec', 'acc': '#c9485b', 'light': True,  'layout': 'sidebar'},
    # Single-column, no sidebar, no skill-level graphics — safe for ATS resume
    # parsers, which often mis-read multi-column layouts and can't interpret
    # bar-chart skill meters at all.
    {'id': 'ats_simple',   'label': 'ATS',       'sb': '#ffffff', 'acc': '#2c3e50', 'light': True,  'layout': 'single'},
]

THEMES_BY_ID = {t['id']: t for t in THEMES}
DEFAULT_THEME = 'clasica_azul'

# Legacy theme ids saved in older profiles, mapped to the current ids above.
OLD_THEME_NAMES = {
    'moderna': 'moderna_roja', 'clasica': 'clasica_azul', 'elegante': 'elegante_oro',
    'creativa': 'violeta', 'pastel': 'pastel_rosa',
}


def resolve_theme(tpl_id):
    tpl_id = OLD_THEME_NAMES.get(tpl_id, tpl_id)
    return THEMES_BY_ID.get(tpl_id, THEMES_BY_ID[DEFAULT_THEME])


I18N = {
    'es': {
        'personal': 'Datos Personales', 'email': 'Email', 'phone': 'Teléfono',
        'address': 'Dirección', 'linkedin': 'LinkedIn', 'website': 'GitHub/Web',
        'dni': 'DNI', 'birthdate': 'Nacimiento', 'nationality': 'Nacion.',
        'gender': 'Género', 'skills': 'Competencias', 'languages': 'Idiomas',
        'interests': 'Intereses', 'profile': 'Perfil', 'experience': 'Experiencia',
        'education': 'Formación', 'courses': 'Cursos y Certificaciones',
        'recommendations': 'Recomendaciones', 'present': 'Presente',
        'def_name': 'Tu Nombre', 'projects': 'Proyectos',
    },
    'en': {
        'personal': 'Personal Details', 'email': 'Email', 'phone': 'Phone',
        'address': 'Address', 'linkedin': 'LinkedIn', 'website': 'GitHub/Web',
        'dni': 'ID Number', 'birthdate': 'Birthdate', 'nationality': 'Nationality',
        'gender': 'Gender', 'skills': 'Skills', 'languages': 'Languages',
        'interests': 'Interests', 'profile': 'Profile', 'experience': 'Experience',
        'education': 'Education', 'courses': 'Courses & Certifications',
        'recommendations': 'Recommendations', 'present': 'Present',
        'def_name': 'Your Name', 'projects': 'Projects',
    },
}


def i18n_for(lang):
    return I18N.get(lang, I18N['es'])


def level_label(v):
    """Normalize a free-form skill/language level into a short CEFR-ish tag."""
    if not v:
        return 'B2'
    raw = str(v).lower().split('–')[0].split('-')[0].strip().split()[0]
    MAP = {'nativo': 'Nativo', 'native': 'Nativo', 'c2': 'C2', 'c1': 'C1',
           'b2': 'B2', 'b1': 'B1', 'a2': 'A2', 'a1': 'A1',
           '5': 'Nativo', '4': 'C1', '3': 'B2', '2': 'B1', '1': 'A2'}
    return MAP.get(raw, raw.upper()[:6])
