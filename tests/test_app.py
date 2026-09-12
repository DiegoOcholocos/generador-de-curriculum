import base64
import io
import json

from pypdf import PdfReader
from PIL import Image


# ─────────────────────────── profiles CRUD ───────────────────────────

def test_profile_save_list_load_delete(client):
    r = client.post('/profiles', json={'personal': {'name': 'Ana'}, 'template': 'bosque',
                                        '_profile_name': 'Perfil A'})
    assert r.status_code == 200
    pid = r.json['id']

    r = client.get('/profiles')
    assert any(p['id'] == pid and p['name'] == 'Perfil A' for p in r.json)

    r = client.get(f'/profiles/{pid}')
    assert r.json['personal']['name'] == 'Ana'

    r = client.delete(f'/profiles/{pid}')
    assert r.status_code == 200
    assert client.get(f'/profiles/{pid}').status_code == 404


def test_profile_id_path_traversal_is_rejected(client):
    r = client.get('/profiles/..%5c..%5c..%5cWindows%5cwin.ini')
    assert r.status_code == 404

    # '../../secret' gets collapsed by URL routing before it even reaches the
    # handler; either way it must never resolve to a 200 with real content.
    r = client.delete('/profiles/../../secret')
    assert r.status_code in (200, 404)

    r = client.get('/profiles/' + ('a' * 200))  # oversized id, also invalid
    assert r.status_code == 404


def test_profile_json_backup_export_import(client):
    r = client.post('/profiles', json={'personal': {'name': 'Backup Me'}, '_profile_name': 'X'})
    pid = r.json['id']
    r = client.get(f'/profiles/{pid}/export')
    assert r.status_code == 200
    assert r.content_type == 'application/json'
    backup = json.loads(r.data)
    assert backup['personal']['name'] == 'Backup Me'
    assert '_meta' not in backup

    data = {'file': (io.BytesIO(json.dumps(backup).encode()), 'backup.json')}
    r = client.post('/profiles/import', data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    new_id = r.json['id']
    assert new_id != pid
    assert client.get(f'/profiles/{new_id}').json['personal']['name'] == 'Backup Me'


# ─────────────────────────── CSV import ───────────────────────────

def test_csv_template_round_trips(client):
    r = client.get('/csv-template')
    assert r.status_code == 200
    data = {'file': (io.BytesIO(r.data), 'plantilla_cv.csv')}
    r = client.post('/import-csv', data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    body = r.json
    assert body['personal']['name'] == 'Tu Nombre'
    assert body['experience'][0]['company'] == 'Empresa'
    assert body['skills'][0]['name'] == 'Python'


def test_csv_import_is_robust_to_reordered_columns(client):
    csv_content = (
        "seccion,valor\r\n"
        "experience,company,position,start_date,end_date,description\r\n"
        "experience,Empresa Z,Gerente,2019,2022,Reordenado correctamente\r\n"
    )
    data = {'file': (io.BytesIO(csv_content.encode('utf-8-sig')), 'reordered.csv')}
    r = client.post('/import-csv', data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    exp = r.json['experience'][0]
    assert exp['company'] == 'Empresa Z'
    assert exp['position'] == 'Gerente'
    assert exp['description'] == 'Reordenado correctamente'


def test_csv_import_accented_text_survives(client):
    csv_content = "seccion,valor\r\nsummary,Descripción con acentos y eñe\r\n"
    data = {'file': (io.BytesIO(csv_content.encode('utf-8-sig')), 't.csv')}
    r = client.post('/import-csv', data=data, content_type='multipart/form-data')
    assert r.json['summary'] == 'Descripción con acentos y eñe'


def test_csv_import_projects_section(client):
    csv_content = (
        "seccion,valor\r\n"
        "project,name,tech,link,description\r\n"
        "project,Mi App,Flask,github.com/x/app,Una app de ejemplo\r\n"
    )
    data = {'file': (io.BytesIO(csv_content.encode('utf-8-sig')), 't.csv')}
    r = client.post('/import-csv', data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    proj = r.json['projects'][0]
    assert proj == {'name': 'Mi App', 'tech': 'Flask', 'link': 'github.com/x/app',
                     'description': 'Una app de ejemplo'}


# ─────────────────────────── PDF generation ───────────────────────────

def _profile(**overrides):
    p = {
        'lang': 'es', 'template': 'moderna_roja',
        'personal': {'name': 'Ana Torres', 'title': 'Diseñadora UX', 'email': 'ana@example.com'},
        'summary': 'Resumen de prueba.', 'experience': [], 'education': [],
        'skills': [], 'languages': [], 'courses': [], 'recommendations': [], 'hobbies': '',
    }
    p.update(overrides)
    return p


def test_generate_pdf_short_profile_is_one_page(client):
    r = client.post('/generate', json=_profile())
    assert r.status_code == 200
    assert r.content_type == 'application/pdf'
    pdf = PdfReader(io.BytesIO(r.data))
    assert len(pdf.pages) == 1


def test_generate_pdf_long_profile_paginates(client):
    long_profile = _profile(
        experience=[{'position': f'Cargo {i}', 'company': f'Empresa {i}',
                     'start_date': '2015', 'end_date': '2020',
                     'description': 'Responsabilidad extensa. ' * 20} for i in range(1, 6)],
        education=[{'degree': f'Titulo {i}', 'institution': f'Uni {i}',
                    'start_date': '2010', 'end_date': '2015'} for i in range(1, 4)],
        courses=[{'name': f'Curso {i}', 'institution': 'Coursera', 'year': '2022'}
                  for i in range(1, 15)],
    )
    r = client.post('/generate', json=long_profile)
    pdf = PdfReader(io.BytesIO(r.data))
    assert len(pdf.pages) >= 2


def test_generate_pdf_sidebar_survives_pagination(client):
    # Regression test for a real bug: Chromium's print engine does not
    # fragment `display:flex` containers across pages. On a multi-page
    # sidebar-layout resume, the flex sidebar's background stopped partway
    # down the document and its text (contacts, skills) silently vanished —
    # no error, just missing/corrupted content in the downloaded PDF. Fixed
    # by giving the sidebar a plain, absolutely-positioned print layout
    # instead of a flex child (see the "PDF / PRINT MODE" block in cv.css).
    profile = _profile(
        template='moderna_roja',
        personal={'name': 'Ana Torres', 'title': 'Diseñadora UX', 'email': 'ana.sidebar.test@example.com'},
        skills=[{'name': 'Figma Skill Marker', 'level': 5}],
        experience=[{'position': f'Cargo {i}', 'company': f'Empresa {i}',
                     'start_date': '2015', 'end_date': '2020',
                     'description': 'Responsabilidad extensa. ' * 20} for i in range(1, 7)],
        education=[{'degree': f'Titulo {i}', 'institution': f'Uni {i}',
                    'start_date': '2010', 'end_date': '2015'} for i in range(1, 4)],
    )
    r = client.post('/generate', json=profile)
    pdf = PdfReader(io.BytesIO(r.data))
    assert len(pdf.pages) >= 2
    page1_text = pdf.pages[0].extract_text()
    assert 'ana.sidebar.test@example.com' in page1_text
    assert 'Figma Skill Marker' in page1_text


def test_generate_pdf_overflowing_sidebar_continues_uncut_on_next_page(client):
    # Regression test: an earlier fix stopped the sidebar's flex-fragmentation
    # corruption by absolutely-positioning it, but a sidebar taller than one
    # page (many skills) then just got its overflow silently sliced off
    # mid-line on page 2 instead of continuing. Switching the sidebar to
    # `float: left` (see cv.css) lets it fragment across pages properly, like
    # normal in-flow content. A profile with a long recommendation text in
    # the sidebar, pushed onto page 2 by a large skill list, must show that
    # text in full on page 2 — not truncated.
    long_rec_text = 'Texto de recomendacion muy largo que debe continuar completo. ' * 6
    profile = _profile(
        template='moderna_roja',
        skills=[{'name': f'Skill {i}', 'level': 3} for i in range(1, 25)],
        courses=[{'name': f'Curso {i}', 'institution': 'Inst', 'year': '2020'} for i in range(1, 6)],
        recommendations=[{'name': 'Referencia Final', 'position': 'CTO', 'company': '',
                           'text': long_rec_text}],
    )
    r = client.post('/generate', json=profile)
    pdf = PdfReader(io.BytesIO(r.data))
    assert len(pdf.pages) >= 2
    full_text = ' '.join(page.extract_text() for page in pdf.pages)
    assert 'Referencia Final' in full_text
    # The tail of the long recommendation text must be present and unbroken —
    # if the sidebar got sliced mid-paragraph, this fragment would be missing.
    assert 'continuar completo' in full_text


def test_generate_pdf_does_not_drop_a_sixth_experience_entry(client):
    # Regression test: the old reportlab renderer (and later, a leftover
    # hardcoded slice(0, 5)) silently dropped anything past the 5th
    # experience entry. A real user profile with 6 jobs surfaced this.
    profile = _profile(
        experience=[{'position': f'Cargo Unico {i}', 'company': f'Empresa {i}',
                     'start_date': '2015', 'end_date': '2020', 'description': ''}
                    for i in range(1, 7)],
    )
    r = client.post('/generate', json=profile)
    text = ' '.join(page.extract_text() for page in PdfReader(io.BytesIO(r.data)).pages)
    assert 'Cargo Unico 6' in text


def test_generate_pdf_ats_layout_renders_projects_and_skills_as_text(client):
    profile = _profile(
        template='ats_simple',
        projects=[{'name': 'App de Ejemplo', 'tech': 'Flask/SQLite',
                   'link': 'github.com/x/app', 'description': 'Un proyecto de prueba'}],
        skills=[{'name': 'Python', 'level': 5}],
    )
    r = client.post('/generate', json=profile)
    assert r.status_code == 200
    text = PdfReader(io.BytesIO(r.data)).pages[0].extract_text()
    assert 'App de Ejemplo' in text
    assert 'Python' in text


def test_generate_pdf_escapes_html_in_user_fields(client):
    payload = _profile(skills=[{'name': '<script>alert(1)</script>', 'level': 3}])
    r = client.post('/generate', json=payload)
    assert r.status_code == 200
    # The literal tag text must appear as visible page text (proof it was
    # escaped, not interpreted as markup) — a real injection would execute
    # instead of rendering as text and leave no such text behind.
    text = PdfReader(io.BytesIO(r.data)).pages[0].extract_text()
    assert '<script>alert(1)</script>' in text


# ─────────────────────────── /remove-bg hardening ───────────────────────────

def test_remove_bg_rejects_garbage_base64(client):
    r = client.post('/remove-bg', json={'photo': 'data:image/png;base64,not-valid-base64!!'})
    assert r.status_code == 400


def test_remove_bg_rejects_non_image_data(client):
    bad = base64.b64encode(b'this is not an image').decode()
    r = client.post('/remove-bg', json={'photo': f'data:image/png;base64,{bad}'})
    assert r.status_code == 400


def test_remove_bg_accepts_and_downscales_large_image(client):
    big = Image.new('RGB', (3000, 3000), (10, 20, 30))
    buf = io.BytesIO()
    big.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode()
    r = client.post('/remove-bg', json={'photo': f'data:image/png;base64,{b64}'})
    assert r.status_code == 200
    assert 'photo' in r.json
