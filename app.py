import eventlet
eventlet.monkey_patch() 

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from agar_env import AgarEngine

app = Flask(__name__)
app.secret_key = 'tajni_kljuc_za_sesije_promeni_ga_kasnije'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

engine = AgarEngine()

# OPTIMIZACIJA: check_same_thread=False za asinhroni rad
def get_db_connection():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    return conn

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
        conn.commit()

init_db()

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', username=session['username'])

@app.route('/play')
def play():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action') 
        username = request.form['username'].strip()
        password = request.form['password']
        
        with get_db_connection() as conn:
            c = conn.cursor()
            if action == 'register':
                hashed_pw = generate_password_hash(password)
                try:
                    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
                    conn.commit()
                    session['username'] = username
                    return redirect(url_for('home'))
                except sqlite3.IntegrityError:
                    flash('To korisničko ime već postoji!')
            
            elif action == 'login':
                c.execute("SELECT password FROM users WHERE username=?", (username,))
                user = c.fetchone()
                if user and check_password_hash(user[0], password):
                    session['username'] = username
                    return redirect(url_for('home'))
                else:
                    flash('Pogrešno korisničko ime ili lozinka!')
                    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@socketio.on('connect')
def handle_connect():
    if 'username' not in session:
        return False 
    engine.add_human(request.sid, session['username'])

@socketio.on('disconnect')
def handle_disconnect():
    engine.remove_human(request.sid)

@socketio.on('action')
def handle_action(data):
    engine.set_action(request.sid, data.get('dx', 0), data.get('dy', 0), data.get('split', False))

def game_loop():
    while True:
        engine.step()
        for sid, p in engine.players.items():
            if not p["is_bot"]: 
                local_state = engine.get_partial_state(sid)
                if local_state:
                    socketio.emit('state', local_state, to=sid)
        socketio.sleep(1 / 30.0)

if __name__ == '__main__':
    print("Server pokrenut! Idi na http://0.0.0.0:5000")
    socketio.start_background_task(game_loop)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False) # Debug je false u produkciji radi brzine