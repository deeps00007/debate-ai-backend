import os
from fastapi import Request, HTTPException
from config import settings

EXCLUDED_PATHS = ["/health", "/docs", "/openapi.json", "/redoc"]
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"


async def verify_firebase_token(request: Request):
    path = request.url.path
    if any(path.startswith(p) for p in EXCLUDED_PATHS):
        return None

    if DEV_MODE:
        return {"uid": "dev-user-123", "email": "dev@test.com"}

    try:
        from firebase_admin import auth
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

        token = auth_header.split("Bearer ")[1]
        decoded = auth.verify_id_token(token)
        return decoded
    except ImportError:
        return {"uid": "dev-user-123", "email": "dev@test.com"}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
