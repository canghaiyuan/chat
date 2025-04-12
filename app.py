from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, send, join_room, leave_room
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

# 初始化数据库
def init_db():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id TEXT PRIMARY KEY, username TEXT, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS channels
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, creator_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS channel_messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, channel_id INTEGER, user_id TEXT, message TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form['id']
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('chat.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (id, username, password) VALUES (?,?,?)", (user_id, username, password))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "ID 已存在，请选择其他 ID。"
        finally:
            conn.close()
    return render_template('register.html')

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['id']
        password = request.form['password']
        conn = sqlite3.connect('chat.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id =? AND password =?", (user_id, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user_id
            session['username'] = user[1]
            return redirect(url_for('channels'))
        else:
            return "ID 或密码错误。"
    return render_template('login.html')

# 注销路由
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

# 频道列表路由
@app.route('/channels')
def channels():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("SELECT * FROM channels")
    channels = c.fetchall()
    conn.close()
    return render_template('channels.html', channels=channels)

# 创建频道路由
@app.route('/create_channel', methods=['POST'])
def create_channel():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    channel_name = request.form['channel_name']
    user_id = session['user_id']
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("INSERT INTO channels (name, creator_id) VALUES (?,?)", (channel_name, user_id))
    conn.commit()
    conn.close()
    return redirect(url_for('channels'))

# 频道聊天页面路由
@app.route('/channel/<int:channel_id>')
def channel(channel_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("SELECT * FROM channels WHERE id =?", (channel_id,))
    channel = c.fetchone()
    c.execute("SELECT users.username, channel_messages.message FROM channel_messages JOIN users ON channel_messages.user_id = users.id WHERE channel_id =?", (channel_id,))
    messages = c.fetchall()
    conn.close()
    return render_template('channel.html', channel=channel, messages=messages)

# SocketIO 事件处理
@socketio.on('join')
def on_join(data):
    channel_id = data['channel_id']
    join_room(channel_id)
    user_id = session['user_id']
    username = session['username']
    message = f'{username} 加入了频道。'
    send({'user': username, 'message': message}, room=channel_id)

@socketio.on('leave')
def on_leave(data):
    channel_id = data['channel_id']
    leave_room(channel_id)
    user_id = session['user_id']
    username = session['username']
    message = f'{username} 离开了频道。'
    send({'user': username, 'message': message}, room=channel_id)

@socketio.on('message')
def handle_message(data):
    channel_id = data['channel_id']
    user_id = session['user_id']
    username = session['username']
    message = data['message']
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("INSERT INTO channel_messages (channel_id, user_id, message) VALUES (?,?,?)", (channel_id, user_id, message))
    conn.commit()
    conn.close()
    send({'user': username, 'message': message}, room=channel_id)

if __name__ == '__main__':
    socketio.run(app, debug=True)    