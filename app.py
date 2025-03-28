import os
import secrets
from functools import wraps  # Bu satır eklendi
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from database import Database

# Uygulama oluşturma
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Rastgele secret key

# Konfigürasyon
app.config.update(
    UPLOAD_FOLDER='static/uploads',
    ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif'},
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,  # 2MB
    DATABASE='ev_arkadasi.db'
)

# Veritabanı bağlantısı
def get_db():
    if 'db' not in g:
        g.db = Database(app.config['DATABASE'])
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Yardımcı fonksiyonlar
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# CSRF Koruması (Basit versiyon)
def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(16)
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token

# Login gerektiren sayfalar için decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bu sayfayı görüntülemek için giriş yapmalısınız', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Rotlar
@app.route('/')
def index():
    db = get_db()
    # Filtreleri TAMAMEN KALDIR (test için)
    ilanlar = db.get_ilanlar({})  # Boş dict gönder
    print("DEBUG - İlan Sayısı:", len(ilanlar))  # Log ekle
    return render_template('index.html', ilanlar=ilanlar)

@app.route('/ilan/<int:ilan_id>')
def ilan_detay(ilan_id):
    db = get_db()
    ilan = db.get_ilan(ilan_id)
    if not ilan:
        flash('İlan bulunamadı!', 'error')
        return redirect(url_for('index'))
    return render_template('ilan_detay.html', ilan=ilan)

@app.route('/ilan_ver', methods=['GET', 'POST'])
@login_required
def ilan_ver():
    if request.method == 'POST':
        # CSRF kontrolü
        if request.form.get('csrf_token') != session.get('_csrf_token'):
            abort(403)
        
        # Form verilerini al
        baslik = request.form['baslik']
        aciklama = request.form['aciklama']
        fiyat = float(request.form['fiyat'])
        konum = request.form['konum']
        cinsiyet = request.form['cinsiyet']
        oda_sayisi = request.form['oda_sayisi']
        sigara = 'sigara' in request.form
        alkol = 'alkol' in request.form
        evcil_hayvan = 'evcil_hayvan' in request.form

        # Resim yükleme kısmını şu şekilde değiştirin:
        resimler = []
        for file in request.files.getlist('resimler'):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Dosya yolunu tam olarak belirtin
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(upload_path)
                    resimler.append(filename)
                    print(f"DEBUG: {filename} başarıyla kaydedildi")  # Log ekleyin
                except Exception as e:
                    print(f"ERROR: {filename} kaydedilemedi - {str(e)}")
                    flash(f"{filename} yüklenirken hata oluştu", "warning")
        
        # Veritabanına ekle
        db = get_db()
        ilan_id = db.ilan_ekle(
            session['user_id'], baslik, aciklama, fiyat, konum, cinsiyet,
            oda_sayisi, sigara, alkol, evcil_hayvan, ','.join(resimler))
        
        if ilan_id:
            flash('İlan başarıyla eklendi!', 'success')
            return redirect(url_for('ilan_detay', ilan_id=ilan_id))
        else:
            flash('İlan eklenirken hata oluştu', 'error')
    
    return render_template('ilan_ver.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Debug için
        print(f"CSRF Token Kontrolü: {request.form.get('csrf_token') == session.get('_csrf_token')}")
        
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        user = db.get_user(username)
        
        # Debug çıktıları
        print(f"Aranan kullanıcı: {username}")
        print(f"Bulunan kullanıcı: {user}")
        if user:
            print(f"Şifre eşleşiyor mu: {check_password_hash(user['password'], password)}")

        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session.permanent = True  # Kalıcı oturum
            flash('Başarıyla giriş yaptınız', 'success')
            print("Giriş başarılı, session:", session)
            return redirect(url_for('index'))
        else:
            flash('Kullanıcı adı veya şifre hatalı', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form.get('phone', '')
        
        if len(password) < 8:
            flash('Şifre en az 8 karakter olmalıdır', 'danger')
            return redirect(url_for('register'))
        
        db = get_db()
        hashed_pw = generate_password_hash(password)
        user_id = db.user_ekle(username, hashed_pw, email, phone)
        
        if user_id:
            flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Bu kullanıcı adı/email zaten kullanımda', 'danger')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Çıkış yapıldı', 'info')
    return redirect(url_for('index'))
    
@app.context_processor
def utility_processor():
    def file_exists(path):
        return os.path.exists(path)
    return dict(file_exists=file_exists)
    
@app.route('/debug_listings')
def debug_listings():
    db = get_db()
    listings = db.get_ilanlar({})
    return {
        'count': len(listings),
        'listings': listings,
        'upload_folder': os.listdir(app.config['UPLOAD_FOLDER'])
    }    
# Başlangıç ayarları
if __name__ == '__main__':
    # Gerekli klasörleri oluştur
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Development sunucusu
    app.run(host='0.0.0.0', port=5000, debug=True)