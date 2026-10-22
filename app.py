import os, sqlite3, secrets, hashlib, hmac, json, re, sys, getpass, base64, urllib.request, urllib.error, time
from pathlib import Path
from functools import wraps
from datetime import timedelta
from flask import Flask, request, jsonify, session, redirect, send_from_directory, abort
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('NEKARRA_DATA_DIR', ROOT / 'data'))
UPLOADS = DATA / 'uploads'
DB = DATA / 'catalog.sqlite3'
DATA.mkdir(parents=True, exist_ok=True)
UPLOADS.mkdir(parents=True, exist_ok=True)
app = Flask(__name__, static_folder='static', static_url_path='/static')
secret_path = DATA / '.secret_key'
if not secret_path.exists():
    secret_path.write_text(secrets.token_hex(32))
    try: secret_path.chmod(0o600)
    except OSError: pass
app.secret_key = os.environ.get('NEKARRA_SECRET_KEY') or secret_path.read_text().strip()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=timedelta(hours=8), MAX_CONTENT_LENGTH=12*1024*1024)
if os.environ.get('NEKARRA_HTTPS') == '1': app.config['SESSION_COOKIE_SECURE'] = True

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS admin (id INTEGER PRIMARY KEY, salt TEXT NOT NULL, passhash TEXT NOT NULL)')
        c.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
            category TEXT NOT NULL, price INTEGER NOT NULL, sizes TEXT NOT NULL,
            fabric TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
            image TEXT NOT NULL DEFAULT '/static/assets/product-photo-pending.svg',
            published INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        c.execute("INSERT OR IGNORE INTO settings VALUES ('whatsapp','')")
        if not c.execute('SELECT 1 FROM products').fetchone():
            c.execute('''INSERT INTO products(code,name,category,price,sizes,fabric,description,published)
                         VALUES (?,?,?,?,?,?,?,?)''', ('NK007','CASUAL WEAR FROCKS AND TOPS','Ethnic Tops',400,
                                  json.dumps(['S','M','L','XL','XXL']), 'Organza, Cotton, Rayon, Linen', '', 0))
init_db()

def hash_password(pw, salt):
    return hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), bytes.fromhex(salt), 310000).hex()

def has_admin():
    with connect() as c: return bool(c.execute('SELECT 1 FROM admin WHERE id=1').fetchone())

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('admin'): return jsonify(error='Please log in'), 401
        return f(*args, **kwargs)
    return wrapper

def csrf_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('admin'): return jsonify(error='Please log in'), 401
        if not hmac.compare_digest(request.headers.get('X-CSRF-Token',''), session.get('csrf','')):
            return jsonify(error='Invalid session token. Reload and retry.'), 403
        return f(*args, **kwargs)
    return wrapper

def serialize(row):
    d=dict(row)
    d['sizes']=json.loads(d['sizes'])
    d['published']=bool(d['published'])
    return d

@app.get('/')
def home(): return send_from_directory(ROOT / 'static', 'index.html')

@app.get('/admin')
def dashboard(): return send_from_directory(ROOT / 'static', 'admin.html')

@app.get('/uploads/<path:filename>')
def upload_file(filename): return send_from_directory(UPLOADS, filename)

@app.get('/api/products')
def public_products():
    with connect() as c:
        products=[serialize(x) for x in c.execute('SELECT * FROM products WHERE published=1 ORDER BY id DESC')]
        phone=c.execute("SELECT value FROM settings WHERE key='whatsapp'").fetchone()['value']
    return jsonify(products=products, whatsapp=phone)

@app.post('/api/login')
def login():
    pw=(request.get_json(silent=True) or {}).get('password','')
    with connect() as c: row=c.execute('SELECT * FROM admin WHERE id=1').fetchone()
    if not row: return jsonify(error='Admin account not configured. Run setup-admin on the server.'), 503
    valid=hmac.compare_digest(hash_password(pw,row['salt']),row['passhash']) if isinstance(pw,str) else False
    if not valid: return jsonify(error='Incorrect password'), 401
    session.clear(); session['admin']=True; session['csrf']=secrets.token_urlsafe(32); session.permanent=True
    return jsonify(ok=True, csrf=session['csrf'])

@app.get('/api/admin/session')
def admin_session():
    return jsonify(logged_in=bool(session.get('admin')), csrf=session.get('csrf',''))

@app.post('/api/logout')
@csrf_required
def logout(): session.clear(); return jsonify(ok=True)

@app.get('/api/admin/products')
@admin_required
def admin_products():
    with connect() as c:
        products=[serialize(x) for x in c.execute('SELECT * FROM products ORDER BY id DESC')]
        phone=c.execute("SELECT value FROM settings WHERE key='whatsapp'").fetchone()['value']
    return jsonify(products=products, whatsapp=phone)

def product_fields(raw):
    name=str(raw.get('name','')).strip()[:120]
    code=str(raw.get('code','')).strip().upper()[:30]
    category=str(raw.get('category','')).strip()
    price=raw.get('price','')
    sizes=raw.get('sizes',[])
    if not name or not re.fullmatch(r'[A-Z0-9_-]{2,30}',code): raise ValueError('Enter a product name and valid code (letters/numbers).')
    if category not in ('Kurtis','Ethnic Tops','Signature Edit'): raise ValueError('Select a valid category.')
    try: price=int(price)
    except (TypeError,ValueError): raise ValueError('Enter a valid price in whole rupees.')
    if not 1 <= price <= 10000000: raise ValueError('Price must be between ₹1 and ₹1,00,00,000.')
    allowed=['XS','S','M','L','XL','XXL','3XL','Free Size']
    if not isinstance(sizes,list) or not sizes or any(s not in allowed for s in sizes): raise ValueError('Select at least one valid size.')
    return (code,name,category,price,json.dumps(list(dict.fromkeys(sizes))),str(raw.get('fabric','')).strip()[:240],str(raw.get('description','')).strip()[:1200],1 if raw.get('published') else 0)

@app.post('/api/admin/products')
@csrf_required
def add_product():
    try: fields=product_fields(request.get_json(force=True))
    except (ValueError,TypeError) as e: return jsonify(error=str(e)),400
    try:
        with connect() as c:
            cur=c.execute('INSERT INTO products(code,name,category,price,sizes,fabric,description,published) VALUES (?,?,?,?,?,?,?,?)',fields)
            return jsonify(id=cur.lastrowid,ok=True),201
    except sqlite3.IntegrityError: return jsonify(error='Product code already exists'),409

@app.put('/api/admin/products/<int:pid>')
@csrf_required
def edit_product(pid):
    try: fields=product_fields(request.get_json(force=True))
    except (ValueError,TypeError) as e: return jsonify(error=str(e)),400
    try:
        with connect() as c:
            result=c.execute('UPDATE products SET code=?,name=?,category=?,price=?,sizes=?,fabric=?,description=?,published=? WHERE id=?',(*fields,pid))
            if not result.rowcount: return jsonify(error='Product not found'),404
    except sqlite3.IntegrityError: return jsonify(error='Product code already exists'),409
    return jsonify(ok=True)

@app.delete('/api/admin/products/<int:pid>')
@csrf_required
def delete_product(pid):
    with connect() as c:
        c.execute('DELETE FROM products WHERE id=?',(pid,))
    return jsonify(ok=True)

@app.post('/api/admin/products/<int:pid>/image')
@csrf_required
def image_product(pid):
    f=request.files.get('image')
    if not f: return jsonify(error='Select a photograph'),400
    contents=f.read()
    ext=None
    if contents.startswith(b'\xff\xd8\xff'): ext='.jpg'
    elif contents.startswith(b'\x89PNG\r\n\x1a\n'): ext='.png'
    elif contents.startswith(b'RIFF') and contents[8:12]==b'WEBP': ext='.webp'
    if not ext: return jsonify(error='Upload a JPG, PNG, or WebP image'),400
    filename=secrets.token_hex(16)+ext
    with connect() as c:
        if not c.execute('SELECT 1 FROM products WHERE id=?',(pid,)).fetchone(): return jsonify(error='Product not found'),404
        (UPLOADS/filename).write_bytes(contents)
        c.execute('UPDATE products SET image=? WHERE id=?',('/uploads/'+filename,pid))
    return jsonify(ok=True,image='/uploads/'+filename)

@app.put('/api/admin/settings')
@csrf_required
def update_settings():
    phone=str((request.get_json(silent=True) or {}).get('whatsapp','')).strip().lstrip('+').replace(' ','').replace('-','')
    if phone and not re.fullmatch(r'\d{10,15}',phone): return jsonify(error='Use country code and phone digits, e.g. 919876543210'),400
    with connect() as c: c.execute("UPDATE settings SET value=? WHERE key='whatsapp'",(phone,))
    return jsonify(ok=True)


# Free, LOCAL open-source FASHN VTON v1.5 integration. No API keys or photo storage.
# Intended for local Windows testing; NOT a production-ready public image-processing service.
import io, threading, uuid
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps, UnidentifiedImageError

VTON_DIR = Path(os.environ.get('NEKARRA_VTON_DIR', ROOT / 'fashn-vton-1.5')).resolve()
VTON_WEIGHTS = VTON_DIR / 'weights'
executor = ThreadPoolExecutor(max_workers=1)
tryon_jobs = {}
tryon_lock = threading.Lock()
JOB_TTL = 25 * 60

def purge_jobs():
    cutoff = time.monotonic() - JOB_TTL
    with tryon_lock:
        for job_id in list(tryon_jobs):
            if tryon_jobs[job_id]['created'] < cutoff:
                del tryon_jobs[job_id]

def read_image(binary):
    if not binary or len(binary) > 6 * 1024 * 1024:
        raise ValueError('Photo must be between 1 byte and 6 MB.')
    try:
        image = Image.open(io.BytesIO(binary))
        if image.format not in ('JPEG', 'PNG', 'WEBP'):
            raise ValueError('Only JPG, PNG or WebP photos are supported.')
        image = ImageOps.exif_transpose(image)
        image.thumbnail((1800, 1800))
        return image.convert('RGB')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError('The selected photo could not be read.')

def get_vton_state():
    if not (VTON_DIR / 'src' / 'fashn_vton').is_dir():
        return False, 'Model code is missing. Run INSTALL_FREE_AI.ps1 first.'
    if not (VTON_WEIGHTS / 'model.safetensors').is_file():
        return False, 'Model weights are missing. Run INSTALL_FREE_AI.ps1 first.'
    return True, 'The free local model files are available. A compatible installation and adequate RAM/GPU are also required.'

@app.get('/api/tryon/config')
def tryon_config():
    enabled, message = get_vton_state()
    return jsonify(enabled=enabled, engine='free-local-vton-1.5', message=message)

def render_local_tryon(job_id, person, garment, category):
    try:
        import sys
        # pip install -e . makes this import available in the project's virtual environment.
        from fashn_vton import TryOnPipeline
        pipeline = TryOnPipeline(weights_dir=str(VTON_WEIGHTS))
        result = pipeline(person_image=person, garment_image=garment, category=category)
        if not result.images:
            raise RuntimeError('The model did not return an image.')
        memory = io.BytesIO()
        result.images[0].save(memory, format='PNG')
        output = 'data:image/png;base64,' + base64.b64encode(memory.getvalue()).decode('ascii')
        with tryon_lock:
            if job_id in tryon_jobs:
                tryon_jobs[job_id].update(status='completed', image=output)
    except Exception as exc:
        # Keep paths/stack traces out of customer responses.
        with tryon_lock:
            if job_id in tryon_jobs:
                tryon_jobs[job_id].update(status='failed', error='Local AI could not generate this preview. Check the VS Code terminal for setup, GPU or memory errors.')
        app.logger.exception('Local try-on failed: %s', exc)
    finally:
        person.close(); garment.close()

@app.post('/api/tryon/start')
def tryon_start():
    ready, msg = get_vton_state()
    if not ready: return jsonify(error=msg),503
    if request.form.get('consent') != 'yes':
        return jsonify(error='You must consent to local processing of your photo.'),400
    try: pid=int(request.form.get('product_id',0))
    except (ValueError,TypeError): return jsonify(error='Choose a valid product.'),400
    with connect() as c:
        p = c.execute('SELECT * FROM products WHERE id=? AND published=1',(pid,)).fetchone()
    if not p: return jsonify(error='This product is not available.'),404
    if not p['image'].startswith('/uploads/'):
        return jsonify(error='The boutique must upload a real outfit photo before AI try-on.'),400
    name=p['image'][len('/uploads/'):]
    if not name or '/' in name or chr(92) in name:
        return jsonify(error='Invalid garment image.'),400
    path=UPLOADS / name
    if not path.is_file(): return jsonify(error='The garment photo is missing.'),400
    uploaded=request.files.get('photo')
    if not uploaded: return jsonify(error='Please upload your photo.'),400
    try:
        person=read_image(uploaded.read())
        garment=read_image(path.read_bytes())
    except ValueError as e: return jsonify(error=str(e)),400
    purge_jobs()
    with tryon_lock:
        if sum(j['status']=='processing' for j in tryon_jobs.values()) >= 1:
            person.close();garment.close()
            return jsonify(error='A local try-on is already running. Please try again when it finishes.'),429
        job_id=uuid.uuid4().hex
        tryon_jobs[job_id]={'created':time.monotonic(),'status':'processing','owner':session.get('tryon_owner')}
    if 'tryon_owner' not in session:
        session['tryon_owner']=secrets.token_urlsafe(24)
        with tryon_lock: tryon_jobs[job_id]['owner']=session['tryon_owner']
    category='one-pieces' if any(word in p['name'].lower() for word in ('frock', 'dress', 'gown')) else 'tops'
    executor.submit(render_local_tryon,job_id,person,garment,category)
    return jsonify(job_id=job_id,status='processing'),202

@app.get('/api/tryon/status/<job_id>')
def tryon_status(job_id):
    purge_jobs()
    with tryon_lock:
        job=tryon_jobs.get(job_id)
        if not job or not session.get('tryon_owner') or job['owner']!=session['tryon_owner']:
            return jsonify(error='Try-on session not found or expired.'),404
        state=job['status']
        if state=='completed': return jsonify(status='completed',image=job['image'])
        if state=='failed': return jsonify(status='failed',error=job['error'])
    return jsonify(status='processing')

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='setup-admin':
        a=getpass.getpass('Create admin password (minimum 12 characters): ')
        b=getpass.getpass('Confirm admin password: ')
        if len(a)<12 or a!=b: sys.exit('Passwords must match and have at least 12 characters.')
        salt=secrets.token_hex(16)
        with connect() as c:
            c.execute('INSERT OR REPLACE INTO admin(id,salt,passhash) VALUES (1,?,?)',(salt,hash_password(a,salt)))
        print('Admin password configured. Run: python app.py')
    else:
        if not has_admin(): print('IMPORTANT: Run python app.py setup-admin before using /admin')
        app.run(host='127.0.0.1',port=int(os.environ.get('PORT','5000')),debug=False)
