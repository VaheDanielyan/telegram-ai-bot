import asyncio
import logging
from utils import database
import os
import tempfile
from functools import wraps
from io import BytesIO
from dotenv import load_dotenv
from pydub import AudioSegment

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from aiogram.utils import executor
from aiogram.utils import exceptions

from integrations.openai_integration import *
from utils.config import Config
from utils.text_to_voice import TextToVoice

from utils import utils

class AIBot:
    def __init__(self):
        load_dotenv()
        self.config = Config()
        self.openai_integration = IntegrationOpenAI(self.config.openai_key)
        self.textToVoice = TextToVoice(self.config.bot_default_tts_language)

        self.bot = Bot(token=self.config.bot_access_token)
        self.dp = Dispatcher(self.bot)
        self.dp.middleware.setup(LoggingMiddleware())
        self.allowedUsers = self.config.bot_allowed_users

        database.init_database()

        logging.basicConfig(
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
        if (self.config.chat_provider == "openai"):
            self.currentLLM = self.config.openai_chat_models[0]

    async def messageHandler(self, message: types.Message):
        if (not self.checkAccess(message)):
            await message.reply("Access Denied")
            return
        if (message.is_command()):
            await self.handleCommand(message)
        elif (message.chat.type == types.ChatType.PRIVATE and not message.text.startswith("/")):
            chat_id = str(message.chat.id)
            user_data = await database.getUserData(chat_id, self.config)
            
            user_prompt = message.text
            await self.bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)
            assistant_message, user_data = await self.messageLLM(user_prompt, chat_id, message.from_user.full_name, user_data)
            
            await message.reply(assistant_message, parse_mode=ParseMode.MARKDOWN)
            
            if user_data["options"]["assistant_voice_chat"]:
                await self.bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)
                voice_data = await self.textToVoice.textToVoice(assistant_message)
                await message.reply_voice(voice_data)

    async def handleAttachment(self, message: types.Message):
        chat_id = message.chat.id
        user_data = await database.getUserData(chat_id, self.config)
        await self.bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)
        transcript = {'text': ''}
        audioMessage = False
        if message.voice:
            file_id = message.voice.file_id
            file_format = "ogg"
            audioMessage = True
            duration = message.voice.duration
        elif message.video:
            file_id = message.video.file_id
            file_format = "mp4"
            duration = message.video.duration
        elif message.audio:
            file_id = message.audio.file_id
            duration = message.audio.duration
            file_format = "mp3"
        else:
            await message.reply("Can't handle such file. Reason: unknown.")
            return

        file = await self.bot.get_file(file_id)
        user_id = message.chat.id
        await file.download(f"{user_id}.{file_format}")
        
        if file_format == "ogg":
            ogg_audio = AudioSegment.from_file(f"{user_id}.ogg", format="ogg")
            ogg_audio.export(f"{user_id}.mp3", format="mp3")
            os.remove(f"{user_id}.ogg")
            file_format = "mp3"

        with open(f"{user_id}.{file_format}", "rb") as audio_file:
            await self.bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)
            transcript = self.openai_integration.transcribeAudio(user_data, audio_file, duration)

        os.remove(f"{user_id}.{file_format}")

        if transcript['text'] == "":
            transcript['text'] = "[Silence]"

        chatGPT_response = False
        if audioMessage and user_data["options"]["whisper_to_chat"]:
            chatGPT_response, user_data = await self.messageLLM(transcript['text'], str(chat_id), message.from_user.full_name, user_data)
            transcript['text'] = "> " + transcript['text'] + "\n\n" + chatGPT_response
        
        await message.reply(transcript['text'])
        if user_data["options"]["assistant_voice_chat"] and chatGPT_response:
                await self.bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)
                voice_data = await self.textToVoice.textToVoice(chatGPT_response)
                await message.reply_voice(voice_data)
        
        database.update_user(str(chat_id), user_data)


    async def messageLLM(self, text: str, chat_id: str, user_name="User", user_data={}):
        await self.bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)
        if (self.config.chat_provider == "openai"):
            assistant_message = self.openai_integration.gptCompletion(text, self.config.chat_default_system_prompt,
                                                                      user_name, self.currentLLM, user_data)
        database.update_user(chat_id, user_data)
        return assistant_message, user_data


    async def handleCommand(self, message: types.Message):
        chat_id = str(message.chat.id)
        user_data = await database.getUserData(chat_id, self.config)
        if (message.get_command() == "/start"):
            await message.reply("Hello, how can I assist you today?")
        elif (message.get_command() == "/clear"):
            if user_data:
                utils.clearUserContext(chat_id)
                print(f"Cleared context for {message.from_user.full_name}")
            await message.reply("Your message context history was cleared.")
        elif (message.get_command() == "/switch"):
            if (self.config.chat_provider == "openai"):
                if (self.currentLLM == self.config.openai_chat_models[0]):
                    self.currentLLM = self.config.openai_chat_models[1]
                elif (self.currentLLM == self.config.openai_chat_models[1]):
                    self.currentLLM = self.config.openai_chat_models[0]
            await message.reply(f"Switched model to {self.currentLLM}")
            print(f"Using {self.currentLLM}")
        elif (message.get_command() == "/settings"):
            self.settingsMarkup = utils.generateInlineKeyboard(chat_id)
            await message.reply(text='Settings:', reply_markup=self.settingsMarkup)
        elif (message.get_command() == "/imagine"):
            await self.bot.send_chat_action(message.chat.id, action=types.ChatActions.TYPING)
            resolution = user_data["options"]["image_resolution"]
            url = self.openai_integration.generateImage(user_data, message.text, ImageResolution(resolution))
            database.update_user(str(message.chat.id), user_data)
            await message.reply(url)
        elif (message.get_command() == "/usage"):
            usage = utils.getUsageReport(user_data)
            await message.reply(usage)

    async def settingsCallback(self, callback_query: types.CallbackQuery):
        user_data = await database.getUserData(callback_query.message.chat.id, self.config)
        chat_id = callback_query.message.chat.id
        action = callback_query.data
        options = user_data["options"]

        if action.startswith("/setting_inc_temp"):
           options["temperature"] = min(options["temperature"] + 0.1, 1)
        elif action.startswith("/setting_dec_temp"):
            options["temperature"] = max(options["temperature"] - 0.1, 0)
        elif action.startswith("/setting_inc_resolution"):
            options["image_resolution"] = ImageResolution.LARGE.value
        elif action.startswith("/setting_dec_resolution"):
            options["image_resolution"] = ImageResolution.MEDIUM.value
        elif action.startswith("/setting_en_whisper"):
            options["whisper_to_chat"] = True
        elif action.startswith("/setting_dis_whisper"):
            options["whisper_to_chat"] = False
        elif action.startswith("/setting_en_voice"):
            options["assistant_voice_chat"] = True
        elif action.startswith("/setting_dis_voice"):
            options["assistant_voice_chat"] = False
        elif action.startswith("/setting_inc_context"):
            options["max-context"] = min(options["max-context"] + 1, MAX_USER_CONTEXT)
        elif action.startswith("/setting_dec_context"):
            options["max-context"] = max(options["max-context"] - 1, 1)

        database.update_user(chat_id, user_data)
        await callback_query.answer()
        settings_text = utils.getSettingsReport(user_data["options"])
        await callback_query.message.reply(text=settings_text)

    def checkAccess(self, message: types.Message):
        user_id = str(message.chat.id)
        if user_id not in self.allowedUsers:
            if "*" != self.allowedUsers[0]:
                print(f"Unauthorized access denied for {user_id}.")
                return False
        print("Access Granted")
        return True

    def run(self):
        print(f"Allowed users: {self.allowedUsers}")
        print(f"System prompt: {self.config.chat_default_system_prompt}")
        print(f"TTS: {self.config.bot_use_tts}")
        print(f"Using " + self.currentLLM)
        self.dp.register_message_handler(self.messageHandler)
        self.dp.register_message_handler(self.handleAttachment, content_types=['photo', 'video', 'audio', 'voice'])
        self.dp.register_callback_query_handler(self.settingsCallback, lambda c: c.data.startswith('/setting_'))

        executor.start_polling(self.dp, skip_updates=True)
