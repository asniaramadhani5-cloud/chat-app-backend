from pydantic import BaseModel
from typing import Optional

# Model untuk registrasi
class RegisterModel(BaseModel):
    username: str
    password: str

# Model untuk login
class LoginModel(BaseModel):
    username: str
    password: str

# Model untuk pesan
class MessageModel(BaseModel):
    receiver: str
    content: str
    is_group: bool = False

# Model untuk grup
class GroupModel(BaseModel):
    name: str
    members: list[str]

# Model untuk update profil
class UpdateProfileModel(BaseModel):
    bio: Optional[str] = None

# Model untuk admin
class AdminActionModel(BaseModel):
    username: str
    action: str  # approve, reject, banned
    reason: Optional[str] = None