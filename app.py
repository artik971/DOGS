from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['DATABASE'] = 'dogs.db'


# Функция для подключения к базе данных
def get_db():
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db


# Функция для инициализации базы данных
def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        db.commit()


# Инициализация базы данных при старте
init_db()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('main'))
        else:
            flash('Неверный логин или пароль', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['new_username']
        password = request.form['new_password']

        if not username or not password:
            flash('Введите логин и пароль', 'error')
            return redirect(url_for('register'))

        db = get_db()
        try:
            hashed_password = generate_password_hash(password)
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            db.execute(
                'INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)',
                (username, hashed_password, created_at)
            )
            db.commit()
            db.close()

            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            db.close()
            flash('Пользователь уже существует', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/main')
def main():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Получаем информацию о пользователе из базы данных
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (session['username'],)).fetchone()
    db.close()

    if user:
        created_at = datetime.strptime(user['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
        welcome_message = f"Добро пожаловать, {user['username']}! "


    return render_template('main.html', image_url=None, welcome_message=welcome_message)


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('login'))


@app.route('/camera')
def camera():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('camera.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))

    if 'photo' not in request.files:
        flash('Не найден файл', 'error')
        return redirect(url_for('main'))

    file = request.files['photo']
    if file.filename == '':
        flash('Не выбран файл', 'error')
        return redirect(url_for('main'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Создаем папку uploads, если ее нет
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Получаем информацию о пользователе для отображения
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (session['username'],)).fetchone()
        db.close()

        if user:
            created_at = datetime.strptime(user['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
            welcome_message = f"Добро пожаловать, {user['username']}! "
        else:
            welcome_message = f"Добро пожаловать, {session['username']}!"


        return render_template(
            'main.html',
            image_url=url_for('static', filename=os.path.join('uploads', filename)),
            welcome_message=welcome_message,
            uploaded_image=filename
        )

    flash('Недопустимый формат файла', 'error')
    return redirect(url_for('main'))

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)