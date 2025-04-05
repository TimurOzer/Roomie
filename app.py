from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit
from datetime import datetime
from werkzeug.utils import secure_filename
import json
import os

app = Flask(__name__)
app.secret_key = "gizli-anahtar"
socketio = SocketIO(app)

USERS_FILE = "users.json"
POSTS_FILE = "posts.json"

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
    random.shuffle(posts)  # Rastgele sırala
    return render_template("kartlar.html", posts=posts, current_user=session['username'])

@app.route('/secim', methods=['POST'])
def secim():
    if 'username' not in session:
        return {"success": False, "message": "Giriş yapmanız gerekiyor."}, 401
    
    data = request.get_json()
    action = data.get("action")
    owner = data.get("owner")

    # Buraya günlük limit ve eşleşme kontrolü eklenecek
    print(f"{session['username']} -> {action.upper()} -> {owner}")

    return {"success": True}
        
if __name__ == '__main__':
    socketio.run(app, debug=True)

