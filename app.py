from flask import Flask, render_template, request, send_file, jsonify
import io, json, os, csv
from pdf_render import generate_cv_pdf
import storage
from themes import THEMES

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024  # 12 MB: covers a base64 photo + form data

storage.init_db()

CSV_FIELDS = {
    'personal': ['name', 'title', 'email', 'phone', 'location', 'linkedin',
                 'website', 'dni', 'birthdate', 'nationality', 'address', 'gender'],
    'experience': ['position', 'company', 'start_date', 'end_date', 'description'],
    'project': ['name', 'tech', 'link', 'description'],
    'education': ['degree', 'institution', 'start_date', 'end_date'],
    'skill': ['name', 'level_speak', 'level_read'],
    'language': ['name', 'speak', 'read'],
    'course': ['name', 'institution', 'year'],
    'recommendation': ['name', 'position', 'company', 'text'],
}
CSV_SECTION_ALIASES = {
    'skills': 'skill', 'languages': 'language', 'idioma': 'language',
    'courses': 'course', 'recommendations': 'recommendation', 'projects': 'project',
}


@app.route('/profiles', methods=['GET'])
def list_profiles():
    profiles = [{
        'id': p['id'], 'name': p['name'] or 'Sin nombre', 'cv_name': p['cv_name'] or '',
        'template': p['template'] or 'clasica_azul', 'updated': p['updated'] or '',
    } for p in storage.list_profiles()]
    return jsonify(profiles)


@app.route('/profiles', methods=['POST'])
def save_profile():
    data = request.get_json(force=True, silent=True) or {}
    profile_id = data.pop('_profile_id', None) or None
    profile_name = data.pop('_profile_name', None) or 'Mi CV'
    pid, name = storage.save_profile(data, profile_id=profile_id, profile_name=profile_name)
    return jsonify({'id': pid, 'name': name})


@app.route('/profiles/<profile_id>', methods=['GET'])
def load_profile(profile_id):
    data = storage.get_profile(profile_id)
    if data is None:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(data)


@app.route('/profiles/<profile_id>', methods=['DELETE'])
def delete_profile(profile_id):
    storage.delete_profile(profile_id)
    return jsonify({'ok': True})


@app.route('/profiles/<profile_id>/export', methods=['GET'])
def export_profile(profile_id):
    data = storage.get_profile(profile_id)
    if data is None:
        return jsonify({'error': 'Not found'}), 404
    data.pop('_meta', None)
    buf = io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
    buf.seek(0)
    return send_file(buf, mimetype='application/json', as_attachment=True,
                      download_name=f'cv_backup_{profile_id}.json')


@app.route('/profiles/import', methods=['POST'])
def import_profile():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file'}), 400
    try:
        data = json.load(f.stream)
    except (ValueError, UnicodeDecodeError):
        return jsonify({'error': 'JSON inválido'}), 400
    if not isinstance(data, dict):
        return jsonify({'error': 'Formato de respaldo inválido'}), 400
    data.pop('_meta', None)
    name = data.get('personal', {}).get('name') or 'CV importado'
    pid, pname = storage.save_profile(data, profile_name=name)
    return jsonify({'id': pid, 'name': pname})


def _read_csv_rows(content):
    """Header-based CSV: each row is 'seccion,campo=valor,campo=valor,...'
    or, for the downloadable template, plain 'seccion,valor1,valor2,...'
    matched positionally against CSV_FIELDS as a fallback for older files."""
    reader = csv.reader(io.StringIO(content))
    rows = [r for r in reader if r and r[0].strip() and not r[0].strip().lower().startswith('seccion')]
    return rows


def _row_to_dict(fields, row):
    out = {}
    for i, field in enumerate(fields, start=1):
        out[field] = row[i].strip() if len(row) > i else ''
    return out


def _is_header_row(sec, row):
    """A row is a header row for `sec` if every non-empty cell after the
    section name is one of that section's known field names — this is what
    lets us re-derive the column order after the user reorders columns in
    a spreadsheet, instead of always trusting a fixed position."""
    known = set(CSV_FIELDS.get(sec, []))
    if not known:
        return False
    cells = [c.strip().lower() for c in row[1:] if c.strip()]
    return bool(cells) and all(c in known for c in cells)


@app.route('/import-csv', methods=['POST'])
def import_csv():
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': 'No file'}), 400
        content = f.read().decode('utf-8-sig')
        rows = _read_csv_rows(content)
        data = {'personal': {}, 'summary': '', 'experience': [], 'projects': [], 'education': [],
                'skills': [], 'languages': [], 'courses': [], 'recommendations': [],
                'hobbies': '', 'template': 'clasica_azul'}
        # Column order per section, seeded from the default layout and
        # overridden whenever a matching header row is encountered — this is
        # what makes column reordering in a spreadsheet safe to import.
        col_order = {sec: fields[:] for sec, fields in CSV_FIELDS.items()}

        for row in rows:
            sec = CSV_SECTION_ALIASES.get(row[0].strip().lower(), row[0].strip().lower())
            if sec in CSV_FIELDS and _is_header_row(sec, row):
                col_order[sec] = [c.strip().lower() for c in row[1:]]
                continue

            if sec == 'personal':
                data['personal'] = _row_to_dict(col_order['personal'], row)
            elif sec == 'summary':
                data['summary'] = row[1].strip() if len(row) > 1 else ''
            elif sec == 'experience':
                data['experience'].append(_row_to_dict(col_order['experience'], row))
            elif sec == 'project':
                data['projects'].append(_row_to_dict(col_order['project'], row))
            elif sec == 'education':
                data['education'].append(_row_to_dict(col_order['education'], row))
            elif sec == 'skill':
                sk = _row_to_dict(col_order['skill'], row)
                sk.setdefault('level_speak', '3')
                data['skills'].append(sk)
            elif sec == 'language':
                lg = _row_to_dict(col_order['language'], row)
                lg.setdefault('speak', 'B2')
                data['languages'].append(lg)
            elif sec == 'course':
                data['courses'].append(_row_to_dict(col_order['course'], row))
            elif sec == 'recommendation':
                data['recommendations'].append(_row_to_dict(col_order['recommendation'], row))
            elif sec == 'hobbies':
                data['hobbies'] = row[1].strip() if len(row) > 1 else ''
            elif sec == 'template':
                data['template'] = (row[1].strip() if len(row) > 1 else '') or 'clasica_azul'
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/csv-template')
def csv_template():
    rows = [
        ['seccion'] + CSV_FIELDS['personal'],
        ['personal', 'Tu Nombre', 'Cargo Profesional', 'email@ejemplo.com', '+51 999 000 000',
         'Lima Peru', 'linkedin.com/in/perfil', 'github.com/usuario', '12345678', '15/03/1990',
         'Peruana', 'Calle Los Alamos 123 Lima', 'Masculino'],
        ['summary', 'Profesional con X años de experiencia en...'],
        ['experience'] + CSV_FIELDS['experience'],
        ['experience', 'Cargo', 'Empresa', 'Ene 2022', 'Presente', 'Descripción de responsabilidades'],
        ['project'] + CSV_FIELDS['project'],
        ['project', 'Sistema de Facturación', 'Next.js, AWS', 'github.com/usuario/proyecto', 'Breve descripción del proyecto'],
        ['education'] + CSV_FIELDS['education'],
        ['education', 'Ingeniería de Sistemas', 'Universidad Nacional', '2015', '2020'],
        ['skill', 'Python', '4', '5'],
        ['language', 'Inglés', 'C1', 'C2'],
        ['course', 'AWS Cloud Practitioner', 'Coursera', '2023'],
        ['recommendation', 'Juan Pérez', 'Gerente de TI', 'Tech Corp', 'Excelente profesional muy dedicado...'],
        ['hobbies', 'Fotografía, senderismo, open source'],
        ['template', 'clasica_azul'],
    ]
    out = io.StringIO()
    csv.writer(out).writerows(rows)
    buf = io.BytesIO(out.getvalue().encode('utf-8-sig'))
    buf.seek(0)
    return send_file(buf, mimetype='text/csv', as_attachment=True, download_name='plantilla_cv.csv')


@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json(force=True, silent=True) or {}
    try:
        pdf_bytes = generate_cv_pdf(app.jinja_env, data)
    except Exception as e:
        app.logger.exception('PDF generation failed')
        msg = str(e)
        if 'Executable doesn' in msg or 'playwright install' in msg:
            msg = 'Falta el navegador de Playwright. Ejecuta: playwright install chromium'
        return jsonify({'error': msg}), 500
    name = (data.get('personal', {}).get('name') or 'CV').replace(' ', '_')
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf',
                      as_attachment=True, download_name=f'CV_{name}.pdf')


MAX_PHOTO_SIDE = 1600       # px — anything larger is downscaled before processing
MAX_PHOTO_BYTES = 6 * 1024 * 1024  # 6 MB decoded


@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    """Remove uniform background from a photo and return white-bg JPEG as base64."""
    try:
        import numpy as np
        from PIL import Image, UnidentifiedImageError
        from scipy import ndimage
        import base64

        b64 = (request.get_json(force=True, silent=True) or {}).get('photo', '')
        if not b64:
            return jsonify({'error': 'No photo'}), 400

        hdr, data_b64 = b64.split(',', 1) if ',' in b64 else ('', b64)
        try:
            raw = base64.b64decode(data_b64, validate=True)
        except Exception:
            return jsonify({'error': 'Foto inválida'}), 400
        if len(raw) > MAX_PHOTO_BYTES:
            return jsonify({'error': 'Imagen demasiado grande'}), 400

        try:
            img = Image.open(io.BytesIO(raw))
            img.verify()
            img = Image.open(io.BytesIO(raw)).convert('RGBA')
        except UnidentifiedImageError:
            return jsonify({'error': 'Formato de imagen no soportado'}), 400

        if max(img.size) > MAX_PHOTO_SIDE:
            img.thumbnail((MAX_PHOTO_SIDE, MAX_PHOTO_SIDE), Image.LANCZOS)

        data = np.array(img)
        h, w = data.shape[:2]

        samples = [data[2, 2], data[2, w - 3], data[h - 3, 2], data[h - 3, w - 3],
                   data[2, w // 2], data[h - 3, w // 2]]
        bg_r = int(np.median([s[0] for s in samples]))
        bg_g = int(np.median([s[1] for s in samples]))
        bg_b = int(np.median([s[2] for s in samples]))

        r = data[:, :, 0].astype(int)
        g = data[:, :, 1].astype(int)
        b = data[:, :, 2].astype(int)
        dist = np.sqrt((r - bg_r) ** 2 + (g - bg_g) ** 2 + (b - bg_b) ** 2)

        tol = 45
        bg_mask = dist < tol

        seed = np.zeros_like(bg_mask)
        seed[0, :] = seed[-1, :] = seed[:, 0] = seed[:, -1] = True
        connected = bg_mask & seed
        for _ in range(500):
            grown = ndimage.binary_dilation(connected, iterations=1)
            new = grown & bg_mask
            if np.array_equal(new, connected):
                break
            connected = new

        result = data.copy()
        result[connected, 0] = 255
        result[connected, 1] = 255
        result[connected, 2] = 255
        result[connected, 3] = 255

        out = io.BytesIO()
        Image.fromarray(result).convert('RGB').save(out, format='JPEG', quality=92)
        out.seek(0)
        encoded = 'data:image/jpeg;base64,' + base64.b64encode(out.read()).decode()
        return jsonify({'photo': encoded})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/')
def index():
    return render_template('index.html', themes_json=json.dumps(THEMES))


if __name__ == '__main__':
    app.run(debug=bool(os.environ.get('FLASK_DEBUG')), port=5050)
