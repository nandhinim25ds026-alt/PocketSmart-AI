import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, HTTPException, status
from jose import jwt, JWTError
from passlib.context import CryptContext

from models import UserInDB

SECRET_KEY = os.getenv("SECRET_KEY", "change_this_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Simple in-memory "database" (resets every time the server restarts)
users_db: dict[str, UserInDB] = {}
blacklisted_tokens: set[str] = set()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = users_db.get(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_token(request: Request) -> Optional[str]:
    return request.cookies.get("access_token")


async def get_current_active_user(request: Request) -> UserInDB:
    token = await get_token(request)
    if not token or token in blacklisted_tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in users_db:
            raise HTTPException(status_code=401, detail="Invalid token")
        return users_db[username]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
