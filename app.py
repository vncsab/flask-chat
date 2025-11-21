from flask import *
from flask_socketio import SocketIO
import bcrypt
import sqlite3
import secrets
from datetime import *
import hashlib
import string as stng

socketio = SocketIO()

def get_db_connection():
    conn = sqlite3.connect("database.db", timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret!'
    socketio.init_app(app)
    return app

def hshtoken(token):
    return hashlib.sha256(token.encode()).hexdigest()

def hshpswd(plain_text_password):
    return bcrypt.hashpw(plain_text_password, bcrypt.gensalt())

def chkpswd(plain_text_password, hashed_password):
    return bcrypt.checkpw(plain_text_password, hashed_password)

def create_session(userid, cur, request_id):
    session_token = secrets.token_hex(32)
    expires_at = datetime.now() + timedelta(days=7)
    cur.execute(
        "insert into sessions (userid, token, expires_at) values (?, ?, ?)",
        (userid, hshtoken(session_token), expires_at)
    )
    socketio.emit("auth", 
    {
        'session_token': session_token,
        'request_id': request_id
    }, to=request.sid)

def extract_session_info(session, cur):
    res = cur.execute("select * from sessions where token=? and expires_at > datetime('now')", (hshtoken(session),))
    row = res.fetchone()
    if row is not None:
        userid = row["userid"]
        res = cur.execute("select username from users where userid=?", (userid,))
        username = res.fetchone()["username"]
        return userid, username
    else:
        return None, None

def validate_username(string):
    str_string = string.strip()
    allowed_chars = set(stng.ascii_letters + stng.digits + "_-")
    if all(c in allowed_chars for c in str_string):
        if len(str_string) < 16:
            return True
        else:
            return False
    else:
        return False

def send_alert(alert_type, title, content, clientsid):
    socketio.emit("alert", 
    {
        'type': alert_type,
        'title': title,
        'content': content,
    }, to=clientsid)
    print("sent alert to", clientsid)

app = create_app()

@app.route("/")
def index():
    return render_template('index.html')

@socketio.on('connect')
def test_connect(auth):
    pass

@socketio.on('disconnect')
def test_disconnect(reason):
    pass

@socketio.on('message')
def handle_message(msg):
    print("message received: ", msg)
    conn = get_db_connection()
    cur = conn.cursor()
    session = msg.get('session')
    roomid = msg.get('roomid')
    content = msg.get('content')
    userid, username = extract_session_info(session, cur)
    if userid is not None:
        if len(msg.get('content')) < 400:
            cur.execute(
                "insert into messages (userid, roomid, content) values (?, ?, ?)",
                (userid, roomid, content)
            )
            socketio.emit("message", 
            {
            'userid': userid,
            'username': username,
            'content': content,
            'roomid': roomid
            })
        else:
            send_alert("error", "message error", "message too long", request.sid)
    else:
        print("message invalid: invalid session!!", msg)

    conn.commit()
    conn.close()

@socketio.on('fetch_messages')
def handle_fetch_messages(data):
    print("fetch messages received: ", data)
    conn = get_db_connection()
    cur = conn.cursor()
    session = data.get('token')
    roomid = data.get('roomid')
    lastid = 0
    userid, username = extract_session_info(session, cur)
    if userid is not None:
        cur.execute("""
                select m.messageid, m.userid, u.username, m.content
                from messages m
                join users u ON m.userid = u.userid
                where m.roomid = ?
                and m.messageid > ? 
                ORDER BY m.messageid DESC
                LIMIT 50
            """, (roomid, lastid))
        rows = cur.fetchall()
        roomname = cur.execute("select name from chatrooms where roomid=?", (roomid,)).fetchone()["name"]
        socketio.emit("messages", 
        {
            'room_name': roomname,
            'messages': [dict(row) for row in rows[::-1]]
        }, to=request.sid
        )

@socketio.on('fetch_chatrooms')
def handle_fetch_chatrooms(data):
    print("fetch messages received: ", data)
    conn = get_db_connection()
    cur = conn.cursor()
    session = data.get('token')
    userid, username = extract_session_info(session, cur)
    if userid is not None:
        cur.execute("select roomid, name from chatrooms")
        rows = cur.fetchall()
        socketio.emit("chatrooms", 
        {
            'chatrooms': [dict(row) for row in rows[::]]
        }, to=request.sid
        )

@socketio.on('register')
def handle_register(user):
    print("registration received: ", user)
    conn = get_db_connection()
    cur = conn.cursor()
    username = user.get('username').strip()
    hashed_pw = hshpswd(user.get('password')).strip()
    request_id = user.get('request_id')
    res = cur.execute("select * from users where username=?",
    (username,))
    row = res.fetchone()
    if validate_username(username):
        if row is None:
            cur.execute(
                "insert into users (username, passhash) values (?, ?)",
                (username, hashed_pw)
            )
            res = cur.execute("select userid, username from users where username=?", (username,))
            userid, usern = res.fetchone()
            create_session(userid, cur, request_id)
            send_alert("success", "auth success", f"registration successful for '{username}'", request.sid)
        else:
            send_alert("error", "auth error", "'{username}' already exists", request.sid)
            print("registration cancelled: username found in the db!!")
    else:
        print("registration cancelled: username contains invalid characters")
        send_alert("error", "auth error", "username is too long or has invalid", request.sid)
    conn.commit()
    conn.close()

@socketio.on('login')
def handle_login(user):
    print("login received: ", user)
    conn = get_db_connection()
    cur = conn.cursor()
    username = user.get('username').strip()
    request_id = user.get('request_id').strip()
    pw = user.get('password')
    res = cur.execute("select * from users where username=?",
    (username,))
    row = res.fetchone()
    if row is not None:
        res = cur.execute("select userid, passhash from users where username=?", (username,))
        userid, passhash = res.fetchone()
        expires_at = datetime.now() + timedelta(days=7)
        if chkpswd(pw, passhash):
            create_session(userid, cur, request_id)
            send_alert("success", "auth success", f"login successful for '{username}'", request.sid)
            print(f"login successful for {userid}:{username}")
        else:
            send_alert("error", "auth error", f"password invalid for '{username}'", request.sid)
            print("login failed: password invalid!!")
    else:
        send_alert("error", "auth error", f"'{username}' is not an account that exists.", request.sid)
        print("login failed: account doesnt exist!!")
    conn.commit()
    conn.close()

@socketio.on('start_session')
def validate_session(session_data):
    print("session received: ", session_data)
    conn = get_db_connection()
    cur = conn.cursor()
    request_id = session_data.get('request_id')
    session_token = session_data.get('token')
    print(session_token)
    res = cur.execute("select * from sessions where token=? and expires_at > datetime('now')", (hshtoken(session_token),))
    row = res.fetchone()
    if row is not None:
        print("session is valid: ", session_data)
        userid = row["userid"]
        res = cur.execute("select username from users where userid=?", (userid,))
        username = res.fetchone()["username"]
        socketio.emit("validated_session", 
        {
            'username': username,
            'userid': userid,
            'request_id': request_id
        }, to=request.sid)
        send_alert("info", "session started", f"started session '{username}', welcome", request.sid)
    else:
        send_alert("error", "session error", f"started session '{username}', welcome", request.sid)
        print("session is invalid!!: ", session_data)

socketio.run(app, host="0.0.0.0", port=80)