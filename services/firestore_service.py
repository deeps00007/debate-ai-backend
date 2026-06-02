import json
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict
from config import settings

DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"


class _MemoryStore:
    def __init__(self):
        self.users = {}
        self.debates = {}
        self.messages = {}
        self.feedback = {}
        self._counter = 0

    def _next_id(self):
        self._counter += 1
        return f"dev-id-{self._counter}"


_store = _MemoryStore()


def _get_firestore():
    from firebase_admin import firestore
    return firestore.client()


class FirestoreService:
    def db(self):
        if DEV_MODE:
            return None
        return _get_firestore()

    def get_or_create_user(self, user_id: str) -> dict:
        if DEV_MODE:
            if user_id not in _store.users:
                _store.users[user_id] = {
                    "user_id": user_id,
                    "subscription": "free",
                    "daily_debate_count": 0,
                    "last_debate_date": "",
                }
            return _store.users[user_id]

        doc_ref = self.db().collection("users").document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        user_data = {
            "user_id": user_id,
            "subscription": "free",
            "daily_debate_count": 0,
            "last_debate_date": "",
            "created_at": datetime.now(timezone.utc),
        }
        doc_ref.set(user_data)
        return user_data

    def check_daily_limit(self, user_id: str) -> bool:
        if DEV_MODE:
            return True
        doc_ref = self.db().collection("users").document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            return True
        user_data = doc.to_dict()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        last_date = user_data.get("last_debate_date", "")
        if last_date != today:
            doc_ref.update({"daily_debate_count": 0, "last_debate_date": today})
            return True
        count = user_data.get("daily_debate_count", 0)
        return count < settings.free_debates_per_day

    def increment_debate_count(self, user_id: str):
        if DEV_MODE:
            if user_id in _store.users:
                _store.users[user_id]["daily_debate_count"] = _store.users[user_id].get("daily_debate_count", 0) + 1
            return
        doc_ref = self.db().collection("users").document(user_id)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        doc_ref.update({
            "daily_debate_count": self.db().collection("users").document(user_id).get().to_dict().get("daily_debate_count", 0) + 1,
            "last_debate_date": today,
        })

    def create_debate(self, user_id: str, topic: str, difficulty: str) -> str:
        debate_id = _store._next_id() if DEV_MODE else self.db().collection("debates").document().id

        if DEV_MODE:
            _store.debates[debate_id] = {
                "user_id": user_id,
                "topic": topic,
                "difficulty": difficulty,
                "status": "active",
                "turn_count": 0,
                "created_at": datetime.now(timezone.utc),
                "ended_at": None,
            }
            _store.messages[debate_id] = []
            return debate_id

        debate_data = {
            "user_id": user_id,
            "topic": topic,
            "difficulty": difficulty,
            "status": "active",
            "turn_count": 0,
            "created_at": datetime.now(timezone.utc),
            "ended_at": None,
        }
        doc_ref = self.db().collection("debates").document(debate_id)
        doc_ref.set(debate_data)
        return debate_id

    def get_debate(self, debate_id: str) -> Optional[dict]:
        if DEV_MODE:
            return _store.debates.get(debate_id)
        doc = self.db().collection("debates").document(debate_id).get()
        return doc.to_dict() if doc.exists else None

    def save_message(self, debate_id: str, speaker: str, text: str, turn_index: int) -> str:
        message_id = _store._next_id() if DEV_MODE else self.db().collection("debates").document(debate_id).collection("messages").document().id

        message_data = {
            "debate_id": debate_id,
            "speaker": speaker,
            "text": text,
            "turn_index": turn_index,
            "timestamp": datetime.now(timezone.utc),
        }

        if DEV_MODE:
            if debate_id not in _store.messages:
                _store.messages[debate_id] = []
            _store.messages[debate_id].append(message_data)
            return message_id

        self.db().collection("debates").document(debate_id).collection("messages").document(message_id).set(message_data)
        return message_id

    def get_messages(self, debate_id: str, limit: int = 10) -> list[dict]:
        if DEV_MODE:
            msgs = _store.messages.get(debate_id, [])
            return msgs[-limit:] if len(msgs) > limit else msgs

        messages = (
            self.db().collection("debates")
            .document(debate_id)
            .collection("messages")
            .order_by("turn_index", direction=self.db().collection("debates").document(debate_id).collection("messages").__class__.DESCENDING if hasattr(self.db().collection("debates").document(debate_id).collection("messages"), '__class__') else 0)
            .limit(limit)
            .stream()
        )

        from firebase_admin import firestore
        messages = (
            self.db().collection("debates")
            .document(debate_id)
            .collection("messages")
            .order_by("turn_index", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )

        result = []
        for msg in messages:
            result.append(msg.to_dict())
        result.reverse()
        return result

    def update_turn_count(self, debate_id: str, turn_count: int):
        if DEV_MODE:
            if debate_id in _store.debates:
                _store.debates[debate_id]["turn_count"] = turn_count
            return
        self.db().collection("debates").document(debate_id).update({"turn_count": turn_count})

    def end_debate(self, debate_id: str) -> dict:
        if DEV_MODE:
            if debate_id in _store.debates:
                _store.debates[debate_id]["status"] = "completed"
                _store.debates[debate_id]["ended_at"] = datetime.now(timezone.utc)
            msgs = _store.messages.get(debate_id, [])
            transcript_parts = []
            for msg in msgs:
                speaker = "User" if msg["speaker"] == "user" else "AI"
                transcript_parts.append(f"{speaker}: {msg['text']}")
            transcript = "\n\n".join(transcript_parts)
            topic = _store.debates.get(debate_id, {}).get("topic", "")
            return {"transcript": transcript, "topic": topic}

        debate_ref = self.db().collection("debates").document(debate_id)
        debate_ref.update({"status": "completed", "ended_at": datetime.now(timezone.utc)})
        messages = self.get_messages(debate_id, limit=100)
        transcript_parts = []
        for msg in messages:
            speaker = "User" if msg["speaker"] == "user" else "AI"
            transcript_parts.append(f"{speaker}: {msg['text']}")
        transcript = "\n\n".join(transcript_parts)
        debate = self.get_debate(debate_id)
        return {"transcript": transcript, "topic": debate.get("topic", "")}

    def save_feedback(self, debate_id: str, feedback_data: dict):
        if DEV_MODE:
            _store.feedback[debate_id] = feedback_data
            return
        self.db().collection("debates").document(debate_id).collection("feedback").document("report").set(feedback_data)

    def get_feedback(self, debate_id: str) -> Optional[dict]:
        if DEV_MODE:
            return _store.feedback.get(debate_id)
        doc = (
            self.db().collection("debates")
            .document(debate_id)
            .collection("feedback")
            .document("report")
            .get()
        )
        return doc.to_dict() if doc.exists else None

    def get_user_debates(self, user_id: str) -> list[dict]:
        if DEV_MODE:
            result = []
            for did, debate in _store.debates.items():
                if debate["user_id"] == user_id:
                    data = dict(debate)
                    data["id"] = did
                    data["date"] = debate.get("created_at", datetime.now(timezone.utc)).strftime("%d %b %Y")
                    result.append(data)
            return result

        from firebase_admin import firestore
        debates = (
            self.db().collection("debates")
            .where("user_id", "==", user_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(20)
            .stream()
        )
        result = []
        for debate in debates:
            data = debate.to_dict()
            data["id"] = debate.id
            data["date"] = data.get("created_at", datetime.now(timezone.utc)).strftime("%d %b %Y")
            result.append(data)
        return result
