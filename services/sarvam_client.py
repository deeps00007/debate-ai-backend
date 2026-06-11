import httpx
import base64
from typing import Optional
from config import settings
from core.exceptions import SarvamAPIError


class SarvamClient:
    def __init__(self):
        self.base_url = settings.sarvam_base_url.rstrip("/")
        self.api_key = settings.sarvam_api_key
        self.headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def speech_to_text(self, audio_bytes: bytes, language_code: str = "en-IN") -> str:
        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data = {
            "model": settings.sarvam_stt_model,
            "language_code": language_code,
        }
        stt_headers = {"api-subscription-key": self.api_key}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/speech-to-text",
                files=files,
                data=data,
                headers=stt_headers,
            )
            if response.status_code != 200:
                raise SarvamAPIError(f"STT failed ({response.status_code}): {response.text}")
            result = response.json()
            return result.get("transcript", "")

    async def chat_completion(self, messages: list[dict], max_tokens: int = 1024) -> str:
        self.headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": settings.sarvam_chat_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.8,
                    "reasoning_effort": None,
                },
                headers=self.headers,
            )
            del self.headers["Authorization"]
            if response.status_code != 200:
                raise SarvamAPIError(f"Chat failed ({response.status_code}): {response.text}")
            data = response.json()
            content = data["choices"][0]["message"].get("content")
            if not content:
                content = data["choices"][0]["message"].get("reasoning_content", "I see your point.")
            return content or "Let me think about that."

    async def text_to_speech(
        self,
        text: str,
        speaker: Optional[str] = None,
        language_code: str = "en-IN",
        pace: float = 1.0,
    ) -> bytes:
        model = settings.sarvam_tts_model
        payload = {
            "text": text,
            "target_language_code": language_code,
            "speaker": speaker or settings.sarvam_tts_speaker,
            "model": model,
            "pace": pace,
            "temperature": 0.6,
            "speech_sample_rate": 24000,
            "output_audio_codec": "mp3",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}/text-to-speech",
                json=payload,
                headers=self.headers,
            )
            if response.status_code != 200:
                raise SarvamAPIError(f"TTS failed ({response.status_code}): {response.text}")
            data = response.json()
            audio_b64 = data.get("audios", [""])[0]
            return base64.b64decode(audio_b64)
