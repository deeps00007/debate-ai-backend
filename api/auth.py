from fastapi import APIRouter, Depends, HTTPException
from core.security import verify_firebase_token
from services.firestore_service import FirestoreService

router = APIRouter()
firestore_service = FirestoreService()


@router.post("/me")
async def get_current_user(user: dict = Depends(verify_firebase_token)):
    user_id = user["uid"]
    user_data = await firestore_service.get_or_create_user(user_id)
    return {"user_id": user_id, **user_data}
