import os

class Config:
    def __init__(self):
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.openai_chat_models = os.environ.get("CHATGPT_CHAT_MODELS").split(";")
        self.openai_gpt_default_temperature = os.environ.get("CHATGPT_DEFAULT_TEMPERATURE")

        self.chat_provider = os.environ.get("CHAT_PROVIDER")
        self.chat_default_system_prompt = os.environ.get("CHAT_DEFAULT_SYSTEM_PROMPT")
        self.chat_max_context = os.environ.get("CHAT_MAX_CONTEXT")

        self.tti_provider = os.environ.get("TTI_PROVIDER")
        self.asr_provider = os.environ.get("ASR_PROVIDER")
        self.asr_model = os.environ.get("ASR_MODEL")

        self.bot_asr_to_chat = os.environ.get("ASR_TO_CHAT")
        self.bot_use_tts = os.environ.get("ENABLE_TTS")
        self.bot_default_tts_language = os.environ.get("VOICE_LANGUAGE")
        self.bot_access_token = os.environ.get("BOT_TOKEN")
        self.bot_allowed_users = os.environ.get("BOT_ALLOWED_USERS").split(";")
