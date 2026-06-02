import asyncio
import base64
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from config import settings
from core.security import verify_firebase_token
from services.firestore_service import FirestoreService
from services.sarvam_client import SarvamClient
from services.debate_engine import build_debate_prompt, build_feedback_prompt

router = APIRouter()
firestore_service = FirestoreService()
sarvam_client = SarvamClient()


class CreateDebateRequest(BaseModel):
    topic: str
    difficulty: str
    language: str = "en-IN"
    voice: str = "shubh"


@router.post("")
async def create_debate(
    body: CreateDebateRequest,
    user: dict = Depends(verify_firebase_token),
):
    user_id = user["uid"]
    can_debate = await asyncio.to_thread(firestore_service.check_daily_limit, user_id)
    if not can_debate:
        raise HTTPException(
            status_code=429,
            detail="Daily debate limit reached. Try again tomorrow or upgrade to premium.",
        )

    debate_id = await asyncio.to_thread(
        firestore_service.create_debate,
        user_id=user_id,
        topic=body.topic,
        difficulty=body.difficulty,
        language=body.language,
        voice=body.voice,
    )
    await asyncio.to_thread(firestore_service.increment_debate_count, user_id)
    return {"debate_id": debate_id}


@router.post("/{debate_id}/turn")
async def submit_turn(
    debate_id: str,
    audio: UploadFile = File(...),
    user: dict = Depends(verify_firebase_token),
):
    debate = await asyncio.to_thread(firestore_service.get_debate, debate_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")

    if debate.get("status") != "active":
        raise HTTPException(status_code=400, detail="Debate is not active")

    turn_count = debate.get("turn_count", 0)
    if turn_count >= settings.max_debate_turns:
        raise HTTPException(
            status_code=400,
            detail="Maximum debate turns reached. Please end the debate.",
        )

    language = debate.get("language", "en-IN")

    try:
        audio_bytes = await audio.read()
        if len(audio_bytes) > settings.max_audio_size_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Audio file too large")

        stt_lang = "hi-IN" if language in ("hi-IN", "hi") else "en-IN"
        user_transcript = await sarvam_client.speech_to_text(audio_bytes, language_code=stt_lang)

        if not user_transcript.strip():
            raise HTTPException(status_code=400, detail="No speech detected. Please try speaking again.")

        await asyncio.to_thread(
            firestore_service.save_message,
            debate_id=debate_id,
            speaker="user",
            text=user_transcript,
            turn_index=turn_count,
        )

        recent_messages = await asyncio.to_thread(
            firestore_service.get_messages,
            debate_id=debate_id,
            limit=8,
        )

        history = []
        for msg in recent_messages:
            role = "user" if msg["speaker"] == "user" else "assistant"
            history.append({"role": role, "content": msg["text"]})

        messages = build_debate_prompt(
            topic=debate["topic"],
            difficulty=debate["difficulty"],
            history=history,
            language=language,
        )

        ai_text = await sarvam_client.chat_completion(messages, max_tokens=1536)

        tts_lang = "hi-IN" if language in ("hi-IN", "hi") else "en-IN"
        tts_speaker = debate.get("voice", "shubh")
        tts_text = ai_text[:2500]
        ai_audio_bytes = await sarvam_client.text_to_speech(tts_text, speaker=tts_speaker, language_code=tts_lang)
        ai_audio_base64 = base64.b64encode(ai_audio_bytes).decode("utf-8")

        await asyncio.to_thread(
            firestore_service.save_message,
            debate_id=debate_id,
            speaker="ai",
            text=ai_text,
            turn_index=turn_count,
        )

        new_turn = turn_count + 1
        await asyncio.to_thread(firestore_service.update_turn_count, debate_id, new_turn)

        return {
            "user_transcript": user_transcript,
            "ai_text": ai_text,
            "ai_audio_base64": ai_audio_base64,
            "turn_index": turn_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


@router.post("/{debate_id}/end")
async def end_debate(
    debate_id: str,
    user: dict = Depends(verify_firebase_token),
):
    debate = await asyncio.to_thread(firestore_service.get_debate, debate_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")

    result = await asyncio.to_thread(firestore_service.end_debate, debate_id)
    transcript = result["transcript"]
    topic = result["topic"]

    feedback_prompt = build_feedback_prompt(transcript, topic)
    feedback_messages = [{"role": "user", "content": feedback_prompt}]

    feedback_text = await sarvam_client.chat_completion(feedback_messages, max_tokens=2048)

    try:
        feedback_json = json.loads(feedback_text)
    except json.JSONDecodeError:
        start = feedback_text.find("{")
        end = feedback_text.rfind("}") + 1
        if start != -1 and end > start:
            feedback_json = json.loads(feedback_text[start:end])
        else:
            feedback_json = {
                "communication_score": 50,
                "persuasion_score": 50,
                "logic_score": 50,
                "words_per_minute": 100,
                "filler_word_count": 5,
                "total_turns": debate.get("turn_count", 0),
                "summary": "Good effort! Keep practicing to improve your debate skills.",
                "tips": [
                    "Practice speaking more slowly and clearly.",
                    "Back up your arguments with examples.",
                    "Listen carefully to counterarguments.",
                ],
            }

    await asyncio.to_thread(firestore_service.save_feedback, debate_id, feedback_json)
    return feedback_json


@router.get("/{debate_id}/feedback")
async def get_feedback(
    debate_id: str,
    user: dict = Depends(verify_firebase_token),
):
    feedback = await asyncio.to_thread(firestore_service.get_feedback, debate_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback


@router.get("")
async def list_debates(
    user: dict = Depends(verify_firebase_token),
):
    user_id = user["uid"]
    return await asyncio.to_thread(firestore_service.get_user_debates, user_id)
