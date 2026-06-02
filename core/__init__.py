import os
import json
from config import settings

DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"


def init_firebase():
    if DEV_MODE:
        return

    try:
        import firebase_admin
        from firebase_admin import credentials

        if len(firebase_admin._apps) > 0:
            return

        cred_json = settings.firebase_credentials_json
        if cred_json:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id})
        else:
            cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
            if cred_path:
                firebase_admin.initialize_app(credentials.Certificate(cred_path))
            else:
                firebase_admin.initialize_app(project=settings.firebase_project_id)
    except Exception:
        pass
