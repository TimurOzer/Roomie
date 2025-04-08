from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit
from datetime import datetime
from werkzeug.utils import secure_filename
import json
import os
import random

app = Flask(__name__)
app.secret_key = "gizli-anahtar"
socketio = SocketIO(app)

USERS_FILE = "users.json"
POSTS_FILE = "posts.json"

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

PRIVATE_MESSAGES_FILE = "messages.json"

BILDIRIMLER_FILE = "bildirimler.json"
MATCHES_FILE = "matches.json"

def load_messages():
    if not os.path.exists(PRIVATE_MESSAGES_FILE):
        return {}
    with open(PRIVATE_MESSAGES_FILE, "r") as f:
        return json.load(f)

def save_messages(data):
    with open(PRIVATE_MESSAGES_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_room_name(user1, user2):
    return "_".join(sorted([user1, user2]))

def load_bildirimler():
    if not os.path.exists(BILDIRIMLER_FILE):
        return []
    with open(BILDIRIMLER_FILE, "r") as f:
        return json.load(f)

def save_bildirimler(data):
    with open(BILDIRIMLER_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_bildirim(gonderen, hedef, tip):
    bildirimler = load_bildirimler()
    bildirimler.append({"gonderen": gonderen, "hedef": hedef, "tip": tip})
    save_bildirimler(bildirimler)
    
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as file:
        return json.load(file)

def save_users(users):
    with open(USERS_FILE, "w") as file:
        json.dump(users, file, indent=4)
        
def load_posts():
    if not os.path.exists(POSTS_FILE):
        return []
    with open(POSTS_FILE, "r") as file:
        return json.load(file)

def save_posts(posts):
    with open(POSTS_FILE, "w") as file:
        json.dump(posts, file, indent=4)
        
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    session['gunluk_limitler'] = {"cay": 5, "kahve": 1}
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            flash("Giriş başarılı!", "success")
            session['username'] = username  # oturumu başlat
            return redirect(url_for('dashboard'))
        else:
            flash("Hatalı kullanıcı adı veya şifre!", "danger")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash("Bu kullanıcı adı zaten alınmış.", "warning")
        else:
            users[username] = password
            save_users(users)
            flash("Kayıt başarılı, şimdi giriş yapabilirsiniz.", "success")
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/post', methods=['GET', 'POST'])
def post():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = session['username']
        content = request.form['content']
        address = request.form['address']
        date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        budget = request.form.get('budget', '')

        # Checkbox değerlerini al
        no_smoking = 'no_smoking' in request.form
        no_pets = 'no_pets' in request.form
        only_female = 'only_female' in request.form
        only_male = 'only_male' in request.form

        # Görsel yükleme
        image_file = request.files.get('image')
        image_url = None
        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_url = f"/static/uploads/{filename}"

        posts = load_posts()
        new_post = {
            "user": username,
            "content": content,
            "address": address,
            "image": image_url,
            "timestamp": date_str,
            "no_smoking": no_smoking,
            "no_pets": no_pets,
            "only_female": only_female,
            "only_male": only_male,
            "budget": budget
        }
        posts.append(new_post)
        save_posts(posts)

        socketio.emit('new_post', new_post, broadcast=True)

        return redirect(url_for('ilanlar'))

    return render_template('post.html')

@app.route('/ilanlar')
def ilanlar():
    posts = load_posts()
    return render_template('ilanlar.html', posts=posts)
    
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash("Lütfen giriş yapın.", "warning")
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Çıkış yaptınız.", "success")
    return redirect(url_for('login'))
    
@app.route('/kartlar')
def kartlar():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    posts = load_posts()
    if not posts:
        return render_template('kartlar.html', post=None)

    post = random.choice(posts)
    return render_template('kartlar.html', post=post)


@app.route('/secim', methods=['POST'])
def secim():
    if 'username' not in session:
        return "Oturum yok", 403

    data = request.get_json()
    secen = session['username']
    secim_tipi = data.get('secim')  # "cay", "kahve", "carpi"
    ev_sahibi = data.get('ev_sahibi')

    # Günlük limit kontrolü (sonraki adımda detaylandıracağız)
    limitler = session.get("gunluk_limitler", {"cay": 5, "kahve": 1})
    if secim_tipi == "cay" and limitler["cay"] <= 0:
        return {"hata": "Günlük çay limitin doldu."}, 400
    if secim_tipi == "kahve" and limitler["kahve"] <= 0:
        return {"hata": "Günlük kahve limitin doldu."}, 400

    if secim_tipi in ["cay", "kahve"]:
        add_bildirim(secen, ev_sahibi, secim_tipi)
        socketio.emit('bildirim', {
            "hedef": ev_sahibi,
            "gonderen": secen,
            "tip": secim_tipi
        }, broadcast=True)

        # Limiti azalt
        limitler[secim_tipi] -= 1
        session["gunluk_limitler"] = limitler

    return {"durum": "başarılı"}
    
@app.route('/bildirimler')
def bildirimler():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    tum_bildirimler = load_bildirimler()
    benim = [b for b in tum_bildirimler if b['hedef'] == session['username']]
    return render_template("bildirimler.html", bildirimler=benim)

def load_matches():
    if not os.path.exists(MATCHES_FILE):
        return []
    with open(MATCHES_FILE, "r") as f:
        return json.load(f)

def save_matches(matches):
    with open(MATCHES_FILE, "w") as f:
        json.dump(matches, f, indent=4)

@app.route('/kabul_et/<gonderen>', methods=["POST"])
def kabul_et(gonderen):
    ev_sahibi = session['username']
    matches = load_matches()

    # Zaten eşleşmişlerse ekleme
    if not any(m for m in matches if set(m) == set([gonderen, ev_sahibi])):
        matches.append([gonderen, ev_sahibi])
        save_matches(matches)

    # Bildirimi sil
    bildirimler = load_bildirimler()
    bildirimler = [b for b in bildirimler if not (b["gonderen"] == gonderen and b["hedef"] == ev_sahibi)]
    save_bildirimler(bildirimler)

    return redirect(url_for('mesajlasma', kullanici=gonderen))
    
@app.route("/mesajlasma/<kullanici>")
def mesajlasma(kullanici):
    if 'username' not in session:
        return redirect(url_for('login'))

    ben = session['username']
    room = get_room_name(ben, kullanici)
    all_messages = load_messages()
    messages = all_messages.get(room, [])

    return render_template("mesajlasma.html", username=ben, diger_kullanici=kullanici, messages=messages)

@socketio.on("join_private")
def handle_join_private(data):
    room = get_room_name(data["from"], data["to"])
    join_room(room)

@socketio.on("private_message")
def handle_private_message(data):
    room = get_room_name(data["from"], data["to"])

    # Mesajı kaydet
    all_messages = load_messages()
    if room not in all_messages:
        all_messages[room] = []
    all_messages[room].append({
        "from": data["from"],
        "text": data["text"]
    })
    save_messages(all_messages)

    emit("private_message", data, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)

