const socket = io();

// chat
const messages = document.getElementById('messages');
const chat_input = document.getElementById('chat-input');
const chatrooms = document.getElementById('chatrooms');
const chatroom_title = document.getElementById('chatroom-title');

// alerts
const alerts = document.getElementById('alerts');

// session
let userid = '';
let username = '';

// spaces and rooms
let roomid = 1
let spaceid = 1

// auth
let pending_request = '';
const auth_popup = document.getElementById('auth-popup');
const username_inp = document.getElementById('auth-username');
const password_inp = document.getElementById('auth-password');

// markdown
const md = markdownit({
    html:false,
    xhtmlOut:false,
    breaks:false,
    langPrefix:'language-',
    typographer:false,
    quotes:'“”‘’',
}).use(window.markdownitEmoji)

md.renderer.rules.emoji = function(token, idx) {
    return twemoji.parse(token[idx].content);
};

function render_md(string) {
    return md.render(string);
}

function generate_alert(type, alert_title, alert_content, timeout = 2000) {
    const alert = document.createElement("div");
    alert.classList.add("alert", "list-container", type);

    const title = document.createElement("b");
    title.textContent = alert_title;
    const content = document.createElement("p");
    content.textContent = alert_content;

    alert.appendChild(title);
    alert.appendChild(content);

    alerts.appendChild(alert);

    setTimeout(() => {
        alert.classList.add("fade-out")
        setTimeout(() => alert.remove(), 500)
    }, timeout)
}

function generate_token(n) {
    var chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    var token = '';
    for(var i = 0; i < n; i++) {
        token += chars[Math.floor(Math.random() * chars.length)];
    }
    return token;
};

function fetch_messages(roomid) {
    socket.emit("fetch_messages", {
        token: Cookies.get('session'),
        roomid: roomid,
    });
}

function fetch_chatrooms() {
    socket.emit("fetch_chatrooms", {
        token: Cookies.get('session'),
    });
}

if (Cookies.get('session')) {
    socket.emit("start_session", {
        token: Cookies.get('session'),
    });
};

socket.on('alert', (data) => {
    generate_alert(data.type, data.title, data.content)
});

socket.on('chatrooms', (data) => {
        for (let chatroom in data.chatrooms) {
            const chatroom_button = document.createElement('button');
            cur_roomid = data.chatrooms[chatroom].roomid
            cur_roomname = data.chatrooms[chatroom].name
            chatroom_button.classList.add("chatroom-btn")
            chatroom_button.textContent = cur_roomname;
            chatroom_button.setAttribute( "onClick", "change_chatroom("+cur_roomid+", '"+cur_roomname+"');" )
            chatrooms.appendChild(chatroom_button)
        };
        
        messages.scrollTop = messages.scrollHeight - messages.clientHeight;
});

socket.on('messages', (data) => {
        messages.innerHTML = '';
        for (let message in data.messages) {
            const group = document.createElement('div');
            group.classList.add('message-group');

            const author = document.createElement('b');
            author.classList.add('message-author');
            author.textContent = data.messages[message].username;

            const content = document.createElement('p');
            content.classList.add('message-content');
            content.innerHTML = render_md(data.messages[message].content);

            group.appendChild(author);
            group.appendChild(content);
            messages.appendChild(group);
            
        };
        
        chatroom_title.textContent = data.room_name
        messages.scrollTop = messages.scrollHeight - messages.clientHeight;
});

socket.on('message', (data) => {
    if (data.roomid == roomid) {
    const group = document.createElement('div');
    group.classList.add('message-group');

    const author = document.createElement('b');
    author.classList.add('message-author');
    author.textContent = data.username;

    const content = document.createElement('p');
    content.classList.add('message-content');
    content.innerHTML = render_md(data.content);

    group.appendChild(author);
    group.appendChild(content);
    messages.appendChild(group);
    messages.scrollTop = messages.scrollHeight - messages.clientHeight;
    }
});

socket.on('validated_session', (data) => {
        username = data.username;
        auth_userid = data.userid;
        auth_popup.style.display = 'none';
        chat_input.disabled = false;
        fetch_messages(roomid)
        fetch_chatrooms()
});

socket.on('auth', (data) => {
        const r_id = generate_token(16);
        Cookies.set('session', data.session_token, { expires: 7 })
        socket.emit("start_session", {
            token: data.session_token,
            request_id: r_id
        });
        pending_request = r_id;
});

function change_chatroom(id) {
    roomid = id
    fetch_messages(id)
}

function register() {
    const r_id = generate_token(16);
    if (username_inp.value && password_inp.value) {
        socket.emit("register", {
            username: username_inp.value,
            password: password_inp.value,
            request_id: r_id
        });
        pending_request = r_id;
    }
    password_inp.value = '';
};

function login() {
    const r_id = generate_token(16);
    if (username_inp.value && password_inp.value) {
        socket.emit('login', {
            username: username_inp.value,
            password: password_inp.value,
            request_id: r_id
        });
        pending_request = r_id;
    }
    password_inp.value = '';
};

function send_message(event) {
    console.log(auth_userid)
    if (event.key === 'Enter' && chat_input.value.trim() !== '') {
        socket.emit('message', {
        session: Cookies.get('session'),
        roomid: roomid,
        content: chat_input.value.trim()
    });
        chat_input.value = '';
        event.preventDefault();
    }
};
