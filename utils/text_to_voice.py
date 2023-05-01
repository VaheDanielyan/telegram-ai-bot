import tempfile
from io import BytesIO
from gtts import gTTS
import pyttsx3
import os

class TextToVoice:
    def __init__(self, default_language: str):
        self.voiceLanguage = default_language

    def setLanguage(self, language_code):
        self.voiceLanguage = language_code

    async def textToVoice(self, text: str) -> BytesIO:
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.ogg', delete=False) as ogg_file:
            temp_filename = ogg_file.name
        gttsSuccess = False
        try:
            tts = gTTS(text, lang=self.voiceLanguage)
            tts.save(temp_filename)
            gttsSuccess = True
        except Exception as e:
            print("Google TTS failed, falling back to pyttsx3: --> ", e)

        # If Google TTS is disabled or failed, use pyttsx3
        if not gttsSuccess:
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)
            engine.save_to_file(text, temp_filename)
            for voice in engine.getProperty('voices'):
                if VOICE_LANGUAGE in voice.languages[0].decode('utf-8') and gender == voice.gender:
                    engine.setProperty('voice', voice.id)
            engine.runAndWait()
            engine.stop()
            await asyncio.sleep(1)

        with open(temp_filename, "rb") as audio_file:
            voice_data = BytesIO(audio_file.read())

        os.remove(temp_filename)
        voice_data.seek(0)
        return voice_data
