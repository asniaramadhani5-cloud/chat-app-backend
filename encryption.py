from cryptography.fernet import Fernet
import os
import base64

# Generate kunci enkripsi
def generate_key():
    return Fernet.generate_key()

# Simpan kunci ke file
def save_key(key: bytes, filename: str = "secret.key"):
    with open(filename, "wb") as f:
        f.write(key)

# Load kunci dari file
def load_key(filename: str = "secret.key") -> bytes:
    if not os.path.exists(filename):
        key = generate_key()
        save_key(key, filename)
    with open(filename, "rb") as f:
        return f.read()

# Enkripsi pesan
def encrypt_message(message: str) -> str:
    key = load_key()
    f = Fernet(key)
    encrypted = f.encrypt(message.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

# Dekripsi pesan
def decrypt_message(encrypted_message: str) -> str:
    try:
        key = load_key()
        f = Fernet(key)
        decoded = base64.urlsafe_b64decode(encrypted_message.encode())
        decrypted = f.decrypt(decoded)
        return decrypted.decode()
    except Exception:
        return "⚠️ Pesan tidak dapat didekripsi"