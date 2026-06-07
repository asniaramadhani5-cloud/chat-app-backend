import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from database import get_connection
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "rahasia_super_aman_ganti_ini")
ALGORITHM = "HS256"
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Hash password
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Cek password
def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# Buat token JWT
def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# Verifikasi token JWT
def verify_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Register pengguna baru
def register_user(username: str, password: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Cek username sudah ada
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return {"success": False, "message": "Username sudah dipakai!"}

        # Simpan user baru dengan status pending
        hashed = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password, status) VALUES (?, ?, 'pending')",
            (username, hashed)
        )
        conn.commit()
        return {"success": True, "message": "Pendaftaran berhasil! Tunggu persetujuan admin."}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()

# Login pengguna
def login_user(username: str, password: str) -> dict:
    # Cek apakah admin
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = create_token("admin")
        return {"success": True, "token": token, "role": "admin"}

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if not user:
            return {"success": False, "message": "Username tidak ditemukan!"}

        if not verify_password(password, user["password"]):
            return {"success": False, "message": "Password salah!"}

        if user["status"] == "pending":
            return {"success": False, "message": "Akun menunggu persetujuan admin!"}

        if user["status"] == "rejected":
            return {"success": False, "message": "Akun kamu ditolak oleh admin!"}

        if user["status"] == "banned":
            return {"success": False, "message": "Akun kamu telah dibanned!"}

        token = create_token(username)
        return {"success": True, "token": token, "role": "user"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()

# Admin: kelola pengguna
def admin_action(username: str, action: str, reason: str = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if action == "approve":
            cursor.execute("UPDATE users SET status = 'approved' WHERE username = ?", (username,))
        elif action == "reject":
            cursor.execute("UPDATE users SET status = 'rejected' WHERE username = ?", (username,))
        elif action == "banned":
            cursor.execute("UPDATE users SET status = 'banned' WHERE username = ?", (username,))
        else:
            return {"success": False, "message": "Aksi tidak valid!"}

        conn.commit()
        return {"success": True, "message": f"User {username} berhasil di-{action}!"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()

# Ambil semua pengguna (untuk admin)
def get_all_users() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, status, created_at FROM users ORDER BY created_at DESC")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users