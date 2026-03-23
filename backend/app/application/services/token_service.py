from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import settings


class TokenService:
    def create_access_token(self, user_id: int) -> str:
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
        payload = {"sub": str(user_id), "iat": int(now.timestamp()), "exp": int(expire.timestamp())}
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def decode_access_token(self, token: str) -> dict:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
