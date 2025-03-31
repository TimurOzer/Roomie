import os
import secrets
from functools import wraps  # Bu satır eklendi
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify, abort
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from database import Database
from datetime import datetime

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
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d.%m.%Y %H:%M'):
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    return value.strftime(format)
    
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
    filters = {}
    
    # Geçerli filtreleri kontrol et
        # Mevcut filtre parametrelerini al
    current_cinsiyet = request.args.get('cinsiyet', 'farketmez')
    current_min_fiyat = request.args.get('min_fiyat', '')
    current_max_fiyat = request.args.get('max_fiyat', '')
    cinsiyet = request.args.get('cinsiyet')
    if cinsiyet and cinsiyet.lower() != 'farketmez':
        filters['cinsiyet'] = cinsiyet
    
    try:
        if request.args.get('min_fiyat'):
            filters['min_fiyat'] = float(request.args.get('min_fiyat'))
        if request.args.get('max_fiyat'):
            filters['max_fiyat'] = float(request.args.get('max_fiyat'))
    except ValueError:
        flash('Geçersiz fiyat aralığı', 'warning')
    
    # Boolean filtreler
    for param in ['sigara', 'alkol', 'evcil_hayvan']:
        if request.args.get(param) in ['1', 'true', 'on']:
            filters[param] = True
    
    ilanlar = db.get_ilanlar(filters)
    print("Filtreler:", filters, "Toplam ilan:", len(ilanlar))  # Debug
    # Template'e mevcut filtre durumunu da gönder
    return render_template('index.html', 
                         ilanlar=ilanlar,
                         current_filters=request.args)

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
        print("Gelen CSRF Token:", request.form.get('csrf_token'))  # Debug
        print("Session CSRF Token:", session.get('_csrf_token'))    # Debug
        if request.form.get('csrf_token') != session.get('_csrf_token'):
            print("CSRF Token Eşleşmiyor!")  # Debug
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
@app.route('/mesaj_istekleri')
@login_required
def mesaj_istekleri():
    db = get_db()
    beklemedeki_istekler = db.get_mesaj_istekleri(session['user_id'], durum='beklemede')
    kabul_edilenler = db.get_mesaj_istekleri(session['user_id'], durum='kabul')
    
    return render_template('mesaj_istekleri.html',
                         beklemedeki_istekler=beklemedeki_istekler,
                         kabul_edilenler=kabul_edilenler)

@app.route('/mesaj_istek_islem', methods=['POST'])
@login_required
def mesaj_istek_islem():
    # Debug için tüm form verilerini yazdır
    print("Form verileri:", request.form)
    
    # CSRF kontrolü
    if request.form.get('csrf_token') != session.get('_csrf_token'):
        print("CSRF token eşleşmiyor!")
        abort(403)
    
    istek_id = request.form.get('istek_id')
    islem = request.form.get('islem')
    
    db = get_db()
    istek = db.get_mesaj_istegi(istek_id)
    
    # Debug çıktıları
    print(f"İstek ID: {istek_id}, İşlem: {islem}")
    print(f"İstek Detay: {istek}")
    print(f"Session User ID: {session['user_id']}")
    
    if not istek or istek['alici_id'] != session['user_id']:
        print("Yetkisiz işlem denemesi!")
        abort(403)
    
    # Veritabanı güncellemesini kontrol et
    rowcount = db.mesaj_istegi_guncelle(istek_id, islem)
    print(f"Etkilenen satır sayısı: {rowcount}")
    
    if rowcount > 0:
        if islem == 'kabul':
            oda_id = db.mesaj_odasi_olustur(
                istek['ilan_id'],
                istek['gonderen_id'],
                istek['alici_id']
            )
            print(f"Mesaj odası ID: {oda_id}")
            
            if oda_id:
                cursor = db.conn.cursor()
                cursor.execute(
                    "UPDATE mesaj_istekleri SET durum = ?, oda_id = ? WHERE id = ?",
                    (islem, oda_id, istek_id)
                )
                db.conn.commit()
                
                # JSON yerine direkt yönlendirme yap
                return redirect(url_for('mesaj_odasi', oda_id=oda_id))
        
        # Reddetme durumunda mesaj_istekleri sayfasına dön
        return redirect(url_for('mesaj_istekleri'))
    
    flash('İşlem başarısız oldu', 'error')
    return redirect(url_for('mesaj_istekleri'))
@app.route('/mesaj_odasi/<int:oda_id>')
@login_required
def mesaj_odasi(oda_id):
    db = get_db()
    oda = db.get_mesaj_odasi(oda_id)
    
    if not oda:
        flash('Mesaj odası bulunamadı', 'error')
        return redirect(url_for('mesajlar'))
    
    if session['user_id'] not in (oda['kullanici1_id'], oda['kullanici2_id']):
        flash('Bu mesaj odasına erişim izniniz yok', 'error')
        return redirect(url_for('mesajlar'))
    
    mesajlar = db.get_mesajlar(oda_id)
    diger_kullanici_id = oda['kullanici1_id'] if oda['kullanici2_id'] == session['user_id'] else oda['kullanici2_id']
    diger_kullanici = db.get_user_by_id(diger_kullanici_id)
    
    return render_template('mesaj_odasi.html',
                         oda=oda,
                         mesajlar=mesajlar,
                         diger_kullanici=diger_kullanici)
        
@app.route('/begeni', methods=['POST'])
@login_required
def begeni_ekle():
    print("\n--- YENİ BEGENI ISTEGI ---")
    print("Form Data:", request.form)
    print("Session:", session)
    
    ilan_id = request.form.get('ilan_id')
    tip = request.form.get('tip')
    
    print(f"İlan ID: {ilan_id}, Tip: {tip}")
    
    if not ilan_id or tip not in ['cay', 'kahve']:
        print("Hata: Geçersiz parametreler")
        return jsonify({'success': False, 'error': 'Geçersiz istek'}), 400
    
    db = get_db()
    ilan = db.get_ilan(ilan_id)
    
    if not ilan:
        print("Hata: İlan bulunamadı")
        return jsonify({'success': False, 'error': 'İlan bulunamadı'}), 404
    
    print(f"İlan Sahibi ID: {ilan['user_id']}")
    
    try:
        begeni_id = db.begeni_ekle(ilan_id, session['user_id'], tip)
        print(f"Beğeni Eklendi, ID: {begeni_id}")
        
        mesaj_istegi_id = db.mesaj_istegi_ekle(
            session['user_id'],
            ilan['user_id'],
            ilan_id,
            tip
        )
        print(f"Mesaj İsteği ID: {mesaj_istegi_id}")
        
        return jsonify({'success': True})
    except Exception as e:
        print("Hata:", str(e))
        return jsonify({'success': False, 'error': str(e)}), 500
        
@app.route('/mesajlar')
@login_required
def mesajlar():
    db = get_db()
    
    # Ev sahibi mi kontrolü (düzeltilmiş versiyon)
    cursor = db.conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM ilanlar WHERE user_id = ?",
        (session['user_id'],)
    )
    is_ev_sahibi = cursor.fetchone()[0] > 0
    
    # Beğenileri al
    begeniler = []
    cursor.execute('''
        SELECT b.*, u.username, i.baslik as ilan_baslik,
               mi.durum as istek_durumu, mo.id as oda_id
        FROM begeniler b
        JOIN users u ON b.gonderen_id = u.id
        JOIN ilanlar i ON b.ilan_id = i.id
        LEFT JOIN mesaj_istekleri mi ON 
            mi.ilan_id = b.ilan_id AND 
            mi.gonderen_id = b.gonderen_id
        LEFT JOIN mesaj_odalari mo ON 
            (mo.kullanici1_id = b.gonderen_id AND mo.kullanici2_id = ?) OR
            (mo.kullanici2_id = b.gonderen_id AND mo.kullanici1_id = ?)
        WHERE i.user_id = ? OR b.gonderen_id = ?
        ORDER BY b.tarih DESC
    ''', (session['user_id'], session['user_id'], session['user_id'], session['user_id']))
    
    begeniler = [dict(row) for row in cursor.fetchall()]
    
    # Ayırma işlemi
    kahve_gonderenler = [b for b in begeniler if b['tip'] == 'kahve']
    cay_gonderenler = [b for b in begeniler if b['tip'] == 'cay']
    
    return render_template('mesajlar.html',
                        kahve_gonderenler=kahve_gonderenler,
                        cay_gonderenler=cay_gonderenler,
                        is_ev_sahibi=is_ev_sahibi)
                         
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