import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from database import Database

# Uygulama oluşturma
app = Flask(__name__)
app.secret_key = 'gizli_anahtar_123'  # Production'da değiştirin!
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB

# Veritabanı bağlantısı
def get_db():
    if 'db' not in g:
        g.db = Database('ev_arkadasi.db')
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

# Rotlar
@app.route('/')
def index():
    db = get_db()
    filters = {
        'cinsiyet': request.args.get('cinsiyet'),
        'min_fiyat': request.args.get('min_fiyat'),
        'max_fiyat': request.args.get('max_fiyat')
    }
    ilanlar = db.get_ilanlar(filters)
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

def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form.get('phone', '')
        
        db = get_db()
        # Şifreyi hash'le
        hashed_password = generate_password_hash(password)
        
        # Kullanıcıyı veritabanına ekle
        user_id = db.user_ekle(username, hashed_password, email, phone)
        
        if user_id:
            flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Bu kullanıcı adı/email zaten kullanımda', 'error')
    
    return render_template('register.html')
    
def ilan_ver():
    if 'user_id' not in session:
        flash('İlan vermek için giriş yapmalısınız', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
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
        
        # Resim yükleme
        resimler = []
        for file in request.files.getlist('resimler'):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                resimler.append(filename)
        
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
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.get_user(username)
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Başarıyla giriş yaptınız', 'success')
            return redirect(url_for('index'))
        else:
            flash('Kullanıcı adı veya şifre hatalı', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Çıkış yapıldı', 'info')
    return redirect(url_for('index'))

# Başlangıç ayarları
if __name__ == '__main__':
    # Gerekli klasörleri oluştur
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Development sunucusu
    app.run(host='0.0.0.0', port=5000, debug=True)