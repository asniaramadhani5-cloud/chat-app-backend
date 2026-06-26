from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict, List
import json
import os
import uuid
import aiofiles

from database import init_db
from models import RegisterModel, LoginModel, MessageModel, GroupModel, AdminActionModel
from auth import register_user, login_user, verify_token, admin_action, get_all_users
from encryption import encrypt_message, decrypt_message

app = FastAPI(title="Chat App")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

@app.get("/chat.html")
async def serve_chat():
    return FileResponse("static/chat.html")

@app.get("/index.html")
async def serve_index_html():
    return FileResponse("static/index.html")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder uploads
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
# Serve frontend files
import shutil
frontend_path = "../frontend"
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

# Simpan koneksi WebSocket aktif
active_connections: Dict[str, WebSocket] = {}

# ─────────────────────────────────────
# STARTUP
# ─────────────────────────────────────
@app.on_event("startup")
async def startup():
    init_db()
    print("🚀 Server berjalan!")

# ─────────────────────────────────────
# AUTH
# ─────────────────────────────────────
@app.post("/register")
async def register(data: RegisterModel):
    result = register_user(data.username, data.password)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/login")
async def login(data: LoginModel):
    result = login_user(data.username, data.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    return result

# ─────────────────────────────────────
# ADMIN
# ─────────────────────────────────────
@app.get("/admin/users")
async def get_users(token: str):
    username = verify_token(token)
    if username != "admin":
        raise HTTPException(status_code=403, detail="Akses ditolak!")
    return get_all_users()

@app.post("/admin/action")
async def manage_user(data: AdminActionModel, token: str):
    username = verify_token(token)
    if username != "admin":
        raise HTTPException(status_code=403, detail="Akses ditolak!")
    result = admin_action(data.username, data.action, data.reason)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

# ─────────────────────────────────────
# UPLOAD FILE
# ─────────────────────────────────────
@app.post("/upload")
async def upload_file(token: str, file: UploadFile = File(...)):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Token tidak valid!")

    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    filepath = f"uploads/{filename}"

    async with aiofiles.open(filepath, "wb") as f:
        content = await file.read()
        await f.write(content)

    return {"url": f"/uploads/{filename}"}

# ─────────────────────────────────────
# WEBSOCKET CHAT
# ─────────────────────────────────────
@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    username = verify_token(token)
    if not username:
        await websocket.close()
        return

    await websocket.accept()
    active_connections[username] = websocket
    print(f"✅ {username} terhubung!")

    # Broadcast status online
    await broadcast_status(username, "online")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")

            # Pesan teks
            if msg_type == "message":
                receiver = message.get("receiver")
                content = message.get("content")
                is_group = message.get("is_group", False)

                # Enkripsi pesan
                encrypted = encrypt_message(content)

                # Simpan ke database
                from database import get_connection
                conn = get_connection()
                conn.execute(
                    "INSERT INTO messages (sender, receiver, content, is_group) VALUES (?, ?, ?, ?)",
                    (username, receiver, encrypted, 1 if is_group else 0)
                )
                conn.commit()
                conn.close()

                # Kirim ke penerima
                payload = {
                    "type": "message",
                    "sender": username,
                    "content": content,
                    "is_group": is_group
                }

                if is_group:
                    await broadcast_group(receiver, payload, exclude=username)
                else:
                    if receiver in active_connections:
                        await active_connections[receiver].send_text(json.dumps(payload))

    except WebSocketDisconnect:
        active_connections.pop(username, None)
        await broadcast_status(username, "offline")
        print(f"❌ {username} terputus!")

# Broadcast status online/offline
async def broadcast_status(username: str, status: str):
    payload = json.dumps({"type": "status", "username": username, "status": status})
    for user, ws in active_connections.items():
        if user != username:
            try:
                await ws.send_text(payload)
            except:
                pass

# Broadcast ke grup
async def broadcast_group(group_id: str, payload: dict, exclude: str = None):
    from database import get_connection
    conn = get_connection()
    members = conn.execute(
        "SELECT username FROM group_members WHERE group_id = ?", (group_id,)
    ).fetchall()
    conn.close()

    for member in members:
        uname = member["username"]
        if uname != exclude and uname in active_connections:
            try:
                await active_connections[uname].send_text(json.dumps(payload))
            except:
                pass

# ─────────────────────────────────────
# RIWAYAT PESAN
# ─────────────────────────────────────
@app.get("/messages/{receiver}")
async def get_messages(receiver: str, token: str):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Token tidak valid!")

    from database import get_connection
    conn = get_connection()
    messages = conn.execute(
        """SELECT sender, receiver, content, created_at 
           FROM messages 
           WHERE (sender = ? AND receiver = ?) 
           OR (sender = ? AND receiver = ?)
           ORDER BY created_at ASC""",
        (username, receiver, receiver, username)
    ).fetchall()
    conn.close()

    result = []
    for msg in messages:
        result.append({
            "sender": msg["sender"],
            "receiver": msg["receiver"],
            "content": decrypt_message(msg["content"]),
            "created_at": msg["created_at"]
        })
    return result