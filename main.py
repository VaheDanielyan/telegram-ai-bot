import asyncio
import logging
import os
import tempfile
from functools import wraps
from io import BytesIO

import openai
import pyttsx3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from aiogram.utils import executor
from aiogram.utils import exceptions
from dotenv import load_dotenv
from gtts import gTTS
from pydub import AudioSegment

from integrations.openai_integration import *
from utils.text_to_voice import TextToVoice
from app.app import AIBot

from utils import database

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Envrionment Variables Load
load_dotenv()
if os.environ.get("OPENAI_API_KEY") is None:
    print("OpenAI_API_KEY is not set in.env file or OPENAI_API_KEY environment variable is not set")
    exit(1)

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

ALLOWED_USERS = os.environ.get("BOT_ALLOWED_USERS").split(",")
SYSTEM_PROMPT = os.environ.get("CHAT_DEFAULT_SYSTEM_PROMPT")
TEMPERATURE = os.environ.get("CHATGPT_TEMPERATURE")
MODEL = "gpt-3.5-turbo"
MODEL_2 = "gpt-4"
CURRENTMODEL = MODEL
WHISPER_TO_CHAT = bool(int(os.environ.get("ASR_TO_CHAT")))
ENABLE_TTS = bool(int(os.environ.get("ENABLE_TTS")))
VOICE_LANGUAGE = os.environ.get("VOICE_LANGUAGE")
MAX_USER_CONTEXT = int(os.environ.get("CHAT_MAX_CONTEXT"))
openai.api_key = os.environ.get("OPENAI_API_KEY")

openai_integration = IntegrationOpenAI(os.environ.get("OPENAI_API_KEY"))
textToVoice = TextToVoice("en")

def generate_settings_markup(chat_id: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("Increase Temperature", callback_data=f"setting_inc_temp_{chat_id}"),
            InlineKeyboardButton("Decrease Temperature", callback_data=f"setting_dec_temp_{chat_id}")
        ],
        [
            InlineKeyboardButton("Enable Whisper", callback_data=f"setting_en_whisper_{chat_id}"),
            InlineKeyboardButton("Disable Whisper", callback_data=f"setting_dis_whisper_{chat_id}")
        ],
        [
            InlineKeyboardButton("Enable assistant voice", callback_data=f"setting_en_voice_{chat_id}"),
            InlineKeyboardButton("Disable assistant voice", callback_data=f"setting_dis_voice_{chat_id}")
        ],
        [
            InlineKeyboardButton("Increase Context", callback_data=f"setting_inc_context_{chat_id}"),
            InlineKeyboardButton("Decrease Context", callback_data=f"setting_dec_context_{chat_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@dp.message_handler(commands=['settings'])
async def settings(message: types.Message):
    chat_id = str(message.chat.id)
    settings_markup = generate_settings_markup(chat_id)
    await message.reply(text='Settings:', reply_markup=settings_markup)

async def settings_callback(callback_query: types.CallbackQuery):
    user_data = await getUserData(callback_query.message.chat.id)
    action, chat_id = callback_query.data.rsplit("_", 1)
    options = user_data["options"]

    if action.startswith("setting_inc_temp"):
       options["temperature"] = min(options["temperature"] + 0.1, 1)
    elif action.startswith("setting_dec_temp"):
        options["temperature"] = max(options["temperature"] - 0.1, 0)

    elif action.startswith("setting_en_whisper"):
        options["whisper_to_chat"] = True
    elif action.startswith("setting_dis_whisper"):
        options["whisper_to_chat"] = False

    elif action.startswith("setting_en_voice"):
        options["assistant_voice_chat"] = True
    elif action.startswith("setting_dis_voice"):
        options["assistant_voice_chat"] = False

    elif action.startswith("setting_inc_context"):
        options["max-context"] = min(options["max-context"] + 1, MAX_USER_CONTEXT)
    elif action.startswith("setting_dec_context"):
        options["max-context"] = max(options["max-context"] - 1, 1)

    settings_markup = generate_settings_markup(chat_id)
    try:
        await callback_query.message.edit_text(text='Choose a setting option:', reply_markup=settings_markup)
    except exceptions.MessageNotModified as e:
        print(e)

    database.update_user(chat_id, user_data)
    settings_txt = f"Updated settings:\n\nTemperature: {options['temperature']}\nWhisper to Chat: {options['whisper_to_chat']}\nAssistant voice: {options['assistant_voice_chat']}\nContext Length: {options['max-context']}"
    await callback_query.answer()
    await callback_query.message.reply(text=settings_txt)


if __name__ == '__main__':
    bot = AIBot()
    bot.run()
