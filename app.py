from flask import Flask, render_template, request, send_file, jsonify
import io, json, os, uuid, csv
from datetime import datetime
from pdf_generator import generate_cv_pdf

app = Flask(__name__)
PROFILES_DIR = os.path.join(os.path.dirname(__file__), 'profiles')
os.makedirs(PROFILES_DIR, exist_ok=True)

@app.route('/profiles', methods=['GET'])
def list_profiles():
    profiles = []
    for fname in sorted(os.listdir(PROFILES_DIR)):
        if fname.endswith('.json'):
            path = os.path.join(PROFILES_DIR, fname)
            try:
                with open(path) as f:
                    data = json.load(f)
                profiles.append({
                    'id': fname[:-5],
                    'name': data.get('_meta', {}).get('profile_name', 'Sin nombre'),
                    'cv_name': data.get('personal', {}).get('name', ''),
                    'template': data.get('template', 'moderna'),
                    'updated': data.get('_meta', {}).get('updated', ''),
                })
            except Exception:
                pass
    return jsonify(profiles)

@app.route('/profiles', methods=['POST'])
def save_profile():
    data = request.get_json()
    profile_id   = data.pop('_profile_id', None) or str(uuid.uuid4())[:8]
    profile_name = data.pop('_profile_name', 'Mi CV')
    data['_meta'] = {'profile_name': profile_name, 'updated': datetime.now().strftime('%d/%m/%Y %H:%M')}
    path = os.path.join(PROFILES_DIR, f'{profile_id}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify({'id': profile_id, 'name': profile_name})

@app.route('/profiles/<profile_id>', methods=['GET'])
def load_profile(profile_id):
    path = os.path.join(PROFILES_DIR, f'{profile_id}.json')
    if not os.path.exists(path):
        return jsonify({'error': 'Not found'}), 404
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/profiles/<profile_id>', methods=['DELETE'])
def delete_profile(profile_id):
    path = os.path.join(PROFILES_DIR, f'{profile_id}.json')
    if os.path.exists(path):
        os.remove(path)
    return jsonify({'ok': True})

@app.route('/import-csv', methods=['POST'])
def import_csv():
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': 'No file'}), 400
        content = f.read().decode('utf-8-sig')
        reader  = csv.reader(io.StringIO(content))
        rows    = [r for r in reader if r and r[0].strip() and not r[0].startswith('seccion')]
        data = {'personal': {}, 'summary': '', 'experience': [], 'education': [],
                'skills': [], 'languages': [], 'courses': [], 'recommendations': [],
                'hobbies': '', 'template': 'moderna'}
        for row in rows:
            sec = row[0].strip().lower()
            def g(i, d=''): return row[i].strip() if len(row) > i else d
            if sec == 'personal':
                data['personal'] = {
                    'name': g(1), 'title': g(2), 'email': g(3),
                    'phone': g(4), 'location': g(5), 'linkedin': g(6),
                    'website': g(7), 'dni': g(8), 'birthdate': g(9),
                    'nationality': g(10), 'address': g(11), 'gender': g(12),
                }
            elif sec == 'summary':
                data['summary'] = g(1)
            elif sec == 'experience':
                data['experience'].append({'position': g(1), 'company': g(2),
                                           'start_date': g(3), 'end_date': g(4), 'description': g(5)})
            elif sec == 'education':
                data['education'].append({'degree': g(1), 'institution': g(2),
                                          'start_date': g(3), 'end_date': g(4)})
            elif sec in ('skill', 'skills'):
                data['skills'].append({'name': g(1), 'level_speak': g(2, '3'), 'level_read': g(3, '3')})
            elif sec in ('language', 'languages', 'idioma'):
                data['languages'].append({'name': g(1), 'speak': g(2, 'B2'), 'read': g(3, 'B2')})
            elif sec in ('course', 'courses'):
                data['courses'].append({'name': g(1), 'institution': g(2), 'year': g(3)})
            elif sec in ('recommendation', 'recommendations'):
                data['recommendations'].append({'name': g(1), 'position': g(2),
                                                'company': g(3), 'text': g(4)})
            elif sec == 'hobbies':
                data['hobbies'] = g(1)
            elif sec == 'template':
                data['template'] = g(1) or 'moderna'
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/csv-template')
def csv_template():
    rows = [
        ['seccion','campo1(nombre)','campo2(cargo)','campo3(email)','campo4(telefono)','campo5(ciudad)','campo6(linkedin)','campo7(website)','campo8(dni)','campo9(nacimiento)','campo10(nacionalidad)','campo11(direccion)','campo12(genero)'],
        ['personal','Tu Nombre','Cargo Profesional','email@ejemplo.com','+51 999 000 000','Lima Peru','linkedin.com/in/perfil','github.com/usuario','12345678','15/03/1990','Peruana','Calle Los Alamos 123 Lima','Masculino'],
        ['summary','Profesional con X años de experiencia en...'],
        ['experience','Cargo','Empresa','Ene 2022','Presente','Descripción de responsabilidades'],
        ['education','Ingeniería de Sistemas','Universidad Nacional','2015','2020'],
        ['skill','Python','4','5'],
        ['language','Inglés','C1','C2'],
        ['course','AWS Cloud Practitioner','Coursera','2023'],
        ['recommendation','Juan Pérez','Gerente de TI','Tech Corp','Excelente profesional muy dedicado...'],
        ['hobbies','Fotografía, senderismo, open source'],
        ['template','moderna'],
    ]
    out = io.StringIO()
    csv.writer(out).writerows(rows)
    buf = io.BytesIO(out.getvalue().encode('utf-8-sig'))
    buf.seek(0)
    return send_file(buf, mimetype='text/csv', as_attachment=True, download_name='plantilla_cv.csv')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    buf  = generate_cv_pdf(data)
    buf.seek(0)
    name = data.get('personal', {}).get('name', 'CV').replace(' ', '_')
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=f'CV_{name}.pdf')


@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    """Remove uniform background from a photo and return white-bg PNG as base64."""
    try:
        import numpy as np
        from PIL import Image
        from scipy import ndimage
        import io, base64

        b64 = request.get_json().get('photo', '')
        if not b64:
            return jsonify({'error': 'No photo'}), 400

        hdr, data_b64 = b64.split(',', 1) if ',' in b64 else ('', b64)
        raw = base64.b64decode(data_b64)
        img = Image.open(io.BytesIO(raw)).convert('RGBA')
        data = np.array(img)
        h, w = data.shape[:2]

        # Sample background color from corners
        samples = [data[2,2], data[2,w-3], data[h-3,2], data[h-3,w-3],
                   data[2,w//2], data[h-3,w//2]]
        bg_r = int(np.median([s[0] for s in samples]))
        bg_g = int(np.median([s[1] for s in samples]))
        bg_b = int(np.median([s[2] for s in samples]))

        r = data[:,:,0].astype(int)
        g = data[:,:,1].astype(int)
        b = data[:,:,2].astype(int)
        dist = np.sqrt((r-bg_r)**2 + (g-bg_g)**2 + (b-bg_b)**2)

        # Adaptive tolerance: higher for very uniform backgrounds
        tol = 45
        bg_mask = dist < tol

        # Flood fill from edges to only remove connected background
        seed = np.zeros_like(bg_mask)
        seed[0,:] = seed[-1,:] = seed[:,0] = seed[:,-1] = True
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
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5050)