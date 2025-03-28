from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
from database import Database

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = Database('ev_arkadasi.db')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    ilanlar = db.get_ilanlar()
    return render_template('index.html', ilanlar=ilanlar)

@app.route('/ilan_ver', methods=['GET', 'POST'])
def ilan_ver():
    if request.method == 'POST':
        baslik = request.form['baslik']
        aciklama = request.form['aciklama']
        fiyat = request.form['fiyat']
        konum = request.form['konum']
        cinsiyet = request.form['cinsiyet']
        oda_sayisi = request.form['oda_sayisi']
        sigara = 1 if 'sigara' in request.form else 0
        alkol = 1 if 'alkol' in request.form else 0
        evcil_hayvan = 1 if 'evcil_hayvan' in request.form else 0
        
        # Resim yükleme
        resimler = []
        files = request.files.getlist('resimler')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                resimler.append(filename)
        
        resimler_str = ','.join(resimler)
        
        db.ilan_ekle(baslik, aciklama, fiyat, konum, cinsiyet, oda_sayisi, 
                    sigara, alkol, evcil_hayvan, resimler_str)
        
        flash('İlanınız başarıyla eklendi!', 'success')
        return redirect(url_for('index'))
    
    return render_template('ilan_ver.html')

@app.route('/ilan/<int:ilan_id>')
def ilan_detay(ilan_id):
    ilan = db.get_ilan(ilan_id)
    if ilan:
        ilan['resimler'] = ilan['resimler'].split(',') if ilan['resimler'] else []
        return render_template('ilan_detay.html', ilan=ilan)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='164.92.247.14', port=5000, debug=True)