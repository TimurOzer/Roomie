from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
from auth_router import oauth2_scheme, fake_users_db
from jose import jwt, JWTError
from datetime import datetime

SECRET_KEY = "super-secret-key"
ALGORITHM = "HS256"

router = APIRouter()

# Günlük limit yapısı
user_limits = {}

class UserProfile(BaseModel):
    username: str
    full_name: Optional[str] = None
    email: str
    cay_hakki: int
    kahve_hakki: int
    last_reset: date

# Token'dan kullanıcı adını çöz
async def get_current_username(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Geçersiz token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token doğrulaması başarısız")

# Günlük limitleri kontrol ve sıfırla
def reset_limits_if_needed(username: str):
    today = date.today()
    user_limit = user_limits.get(username)
    if not user_limit or user_limit['last_reset'] != today:
        user_limits[username] = {
            "cay": 5,
            "kahve": 1,
            "last_reset": today
        }

@router.get("/me", response_model=UserProfile)
async def get_my_profile(username: str = Depends(get_current_username)):
    user = fake_users_db.get(username)
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    reset_limits_if_needed(username)
    limits = user_limits[username]

    return UserProfile(
        username=username,
        full_name=user.full_name,
        email=user.email,
        cay_hakki=limits['cay'],
        kahve_hakki=limits['kahve'],
        last_reset=limits['last_reset']
    )
