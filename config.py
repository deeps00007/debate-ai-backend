import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.sarvam_api_key = os.getenv('SARVAM_API_KEY', '')
        self.sarvam_base_url = os.getenv('SARVAM_BASE_URL', 'https://api.sarvam.ai')
        self.sarvam_stt_model = os.getenv('SARVAM_STT_MODEL', 'saarika:v2.5')
        self.sarvam_tts_speaker = os.getenv('SARVAM_TTS_SPEAKER', 'shubh')
        self.sarvam_tts_model = os.getenv('SARVAM_TTS_MODEL', 'bulbul:v3')
        self.sarvam_chat_model = os.getenv('SARVAM_CHAT_MODEL', 'sarvam-30b')
        self.firebase_credentials_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
        self.firebase_project_id = os.getenv('FIREBASE_PROJECT_ID', 'debate-ai-coach')
        self.max_audio_size_mb = int(os.getenv('MAX_AUDIO_SIZE_MB', '5'))
        self.max_debate_turns = int(os.getenv('MAX_DEBATE_TURNS', '20'))
        self.free_debates_per_day = int(os.getenv('FREE_DEBATES_PER_DAY', '5'))


settings = Settings()
