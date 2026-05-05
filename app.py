from flask import Flask, render_template
from flask_socketio import SocketIO
from agar_env import AgarEnv
import numpy as np

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# Koristimo SocketIO za brzu real-time komunikaciju
socketio = SocketIO(app, cors_allowed_origins="*")

# Inicijalizujemo Gym okruženje
env = AgarEnv()
env.reset()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print("Klijent povezan!")
    # Šaljemo početno stanje čim se klijent poveže
    socketio.emit('state', env._get_obs())

@socketio.on('action')
def handle_action(data):
    # Dobijamo pravac miša sa frontenda
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)
    
    # Izvršavamo korak u Gym okruženju
    obs, reward, done, truncated, info = env.step(np.array([dx, dy]))
    
    # Šaljemo novo stanje igre nazad klijentu
    socketio.emit('state', obs)

if __name__ == '__main__':
    print("Server pokrenut na [http://127.0.0.1:5000](http://127.0.0.1:5000)")
    socketio.run(app, debug=True)
    