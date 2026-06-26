const API = ""
let token = localStorage.getItem("token");
let currentUser = localStorage.getItem("username");
let currentRole = localStorage.getItem("role");
let selectedChat = null;
let ws = null;
let users = [];

// ─────────────────────────────────────
// AUTH
// ─────────────────────────────────────
function showTab(tab) {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".form").forEach(f => f.classList.remove("active"));
    event.target.classList.add("active");
    document.getElementById(tab + "Form").classList.add("active");
    hideMessage();
}

function showMessage(text, type) {
    const el = document.getElementById("message");
    el.textContent = text;
    el.className = "message " + type;
}

function hideMessage() {
    const el = document.getElementById("message");
    el.className = "message";
}

async function register() {
    const username = document.getElementById("regUsername").value.trim();
    const password = document.getElementById("regPassword").value;
    const confirm = document.getElementById("regConfirm").value;

    if (!username || !password) return showMessage("Username dan password wajib diisi!", "error");
    if (username.length < 5) return showMessage("Username minimal 5 karakter!", "error");
    if (password.length < 8) return showMessage("Password minimal 8 karakter!", "error");
    if (password !== confirm) return showMessage("Password tidak cocok!", "error");

    const res = await fetch(`${API}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (res.ok) {
        showMessage("✅ Pendaftaran berhasil! Tunggu persetujuan admin.", "success");
    } else {
        showMessage("❌ " + data.detail, "error");
    }
}

async function login() {
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value;

    if (!username || !password) return showMessage("Isi username dan password!", "error");

    const res = await fetch(`${API}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (res.ok) {
        localStorage.setItem("token", data.token);
        localStorage.setItem("username", username);
        localStorage.setItem("role", data.role);
        window.location.href = "chat.html";
    } else {
        showMessage("❌ " + data.detail, "error");
    }
}

// ─────────────────────────────────────
// CHAT PAGE INIT
// ─────────────────────────────────────
window.onload = function () {
    if (!document.getElementById("currentUser")) return;

    if (!token) {
        window.location.href = "index.html";
        return;
    }

    document.getElementById("currentUser").textContent = currentUser;

    if (currentRole === "admin") {
        document.getElementById("adminTab").style.display = "block";
    }

    connectWebSocket();
    loadUsers();
}

function logout() {
    if (ws) ws.close();
    localStorage.clear();
    window.location.href = "index.html";
}

// ─────────────────────────────────────
// WEBSOCKET
// ─────────────────────────────────────
function connectWebSocket() {
    ws = new WebSocket(`wss://${window.location.host}/ws/${token}`);

    ws.onmessage = function (event) {
        const data = JSON.parse(event.data);

        if (data.type === "message") {
            if (data.sender === selectedChat) {
                appendMessage(data.content, "received");
            }
        }

        if (data.type === "status") {
            updateUserStatus(data.username, data.status);
        }
    };

    ws.onclose = function () {
        setTimeout(connectWebSocket, 3000);
    };
}

// ─────────────────────────────────────
// USERS
// ─────────────────────────────────────
async function loadUsers() {
    const res = await fetch(`${API}/admin/users?token=${token}`);
    if (!res.ok) return;
    const data = await res.json();
    users = data.filter(u => u.status === "approved" && u.username !== currentUser);
    renderUserList(users);
}

function renderUserList(list) {
    const el = document.getElementById("userList");
    el.innerHTML = "";
    list.forEach(u => {
        el.innerHTML += `
        <div class="user-item" onclick="openChat('${u.username}')">
            <div class="avatar">
                ${u.username[0].toUpperCase()}
                <div class="offline-dot" id="dot-${u.username}"></div>
            </div>
            <div class="user-info">
                <div class="user-name">${u.username}</div>
                <div class="user-status" id="status-${u.username}">Offline</div>
            </div>
        </div>`;
    });
}

function searchUser() {
    const q = document.getElementById("searchInput").value.toLowerCase();
    const filtered = users.filter(u => u.username.toLowerCase().includes(q));
    renderUserList(filtered);
}

function updateUserStatus(username, status) {
    const statusEl = document.getElementById(`status-${username}`);
    const dotEl = document.getElementById(`dot-${username}`);
    if (statusEl) statusEl.textContent = status === "online" ? "🟢 Online" : "⚫ Offline";
    if (dotEl) dotEl.className = status === "online" ? "online-dot" : "offline-dot";
}

// ─────────────────────────────────────
// CHAT
// ─────────────────────────────────────
async function openChat(username) {
    selectedChat = username;

    document.getElementById("chatArea").innerHTML = `
        <div class="chat-header">
            <div class="avatar">${username[0].toUpperCase()}</div>
            <div class="chat-header-info">
                <h3>${username}</h3>
                <span id="chatStatus">...</span>
            </div>
        </div>
        <div class="messages" id="messages"></div>
        <div class="input-area">
            <button class="file-btn" onclick="document.getElementById('fileInput').click()">📎</button>
            <input type="text" id="msgInput" placeholder="Tulis pesan..." onkeypress="if(event.key==='Enter') sendMessage()" />
            <button class="send-btn" onclick="sendMessage()">➤</button>
        </div>
    `;

    loadMessages(username);
}

async function loadMessages(username) {
    const res = await fetch(`${API}/messages/${username}?token=${token}`);
    if (!res.ok) return;
    const messages = await res.json();
    messages.forEach(msg => {
        const type = msg.sender === currentUser ? "sent" : "received";
        appendMessage(msg.content, type, msg.created_at);
    });
}

function appendMessage(content, type, time = null) {
    const el = document.getElementById("messages");
    if (!el) return;
    const timeStr = time ? new Date(time).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }) : new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
    el.innerHTML += `
        <div class="message-bubble ${type}">
            ${content}
            <div class="message-time">${timeStr}</div>
        </div>`;
    el.scrollTop = el.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById("msgInput");
    const content = input.value.trim();
    if (!content || !selectedChat) return;

    ws.send(JSON.stringify({
        type: "message",
        receiver: selectedChat,
        content: content,
        is_group: false
    }));

    appendMessage(content, "sent");
    input.value = "";
}

// ─────────────────────────────────────
// FILE UPLOAD
// ─────────────────────────────────────
async function uploadFile() {
    const file = document.getElementById("fileInput").files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API}/upload?token=${token}`, {
        method: "POST",
        body: formData
    });
    const data = await res.json();
    if (data.url) {
        ws.send(JSON.stringify({
            type: "message",
            receiver: selectedChat,
            content: `📎 <a href="${API}${data.url}" target="_blank">Lihat File</a>`,
            is_group: false
        }));
        appendMessage(`📎 <a href="${API}${data.url}" target="_blank">Lihat File</a>`, "sent");
    }
}

// ─────────────────────────────────────
// SIDEBAR TABS
// ─────────────────────────────────────
function showSideTab(tab) {
    document.querySelectorAll(".sidebar-tab").forEach(t => t.classList.remove("active"));
    event.target.classList.add("active");

    if (tab === "admin") {
        loadAdminPanel();
    } else {
        loadUsers();
    }
}

// ─────────────────────────────────────
// ADMIN PANEL
// ─────────────────────────────────────
async function loadAdminPanel() {
    const res = await fetch(`${API}/admin/users?token=${token}`);
    if (!res.ok) return;
    const users = await res.json();

    const chatArea = document.getElementById("chatArea");
    chatArea.innerHTML = `
        <div class="admin-panel">
            <h2>👑 Panel Admin</h2>
            ${users.map(u => `
            <div class="user-card">
                <div class="user-card-info">
                    <strong>${u.username}</strong><br>
                    <span>Daftar: ${new Date(u.created_at).toLocaleDateString("id-ID")}</span>
                    <span class="status-badge status-${u.status}" style="margin-left:8px">
                        ${u.status === "pending" ? "⏳ Menunggu" :
                          u.status === "approved" ? "✅ Disetujui" :
                          u.status === "rejected" ? "❌ Ditolak" : "🚫 Banned"}
                    </span>
                </div>
                <div class="user-card-actions">
                    ${u.status === "pending" ? `
                        <button class="btn-approve" onclick="doAction('${u.username}','approve')">✅ Setujui</button>
                        <button class="btn-reject" onclick="doAction('${u.username}','reject')">❌ Tolak</button>
                    ` : ""}
                    ${u.status === "approved" ? `
                        <button class="btn-ban" onclick="doAction('${u.username}','banned')">🚫 Ban</button>
                    ` : ""}
                </div>
            </div>`).join("")}
        </div>`;
}

async function doAction(username, action) {
    const res = await fetch(`${API}/admin/action?token=${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, action })
    });
    if (res.ok) {
        loadAdminPanel();
    }
}
