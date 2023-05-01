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

import database

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

async def getUserData(chat_id):
    user_data = database.get_user(chat_id)
    if not user_data:
        user_data = {
            "context": [],
            "usage": {"chatgpt": 0, "whisper": 0, "dalle": 0},
            "options": {
                "whisper_to_chat": WHISPER_TO_CHAT,
                "assistant_voice_chat": False,
                "temperature": float(TEMPERATURE),
                "max-context": MAX_USER_CONTEXT
            }
        }
        database.add_user(chat_id, user_data)
        user_data = database.get_user(chat_id)
    return user_data

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

def restricted(func):
    @wraps(func)
    async def wrapped(message, *args, **kwargs):
        user_id = str(message.chat.id)
        print(ALLOWED_USERS)
        if user_id not in ALLOWED_USERS:
            if "*" != ALLOWED_USERS[0]:
                print(f"Unauthorized access denied for {user_id}.")
                return
        else:
            _ = await getUserData(user_id)
        return await func(message, *args, **kwargs)
    return wrapped


async def messageLLM(text: str, chat_id: str, user_name="User", user_data={}):
    await bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)
    assistant_message = openai_integration.gptCompletion(text, SYSTEM_PROMPT, user_name, CURRENTMODEL, user_data)
    database.update_user(chat_id, user_data)
    return assistant_message, user_data

@dp.message_handler(commands=['start'])
@restricted
async def start(message: types.Message):
    _ = await getUserData(message.chat.id)
    await message.reply("Hello, how can I assist you today?")

@dp.message_handler(commands=['gpt3', 'gpt4'])
@restricted
async def swich(message: types.Message):
    _ = await getUserData(message.chat.id)
    model = message.text
    if (message.text == "/gpt3"):
        await switchModel(MODEL)
    elif (message.text == "/gpt4"):
        await switchModel(MODEL_2)
    await message.reply("Switched the active model to " + CURRENTMODEL)
    
@dp.message_handler(commands=['clear'], content_types=['text'])
@restricted
async def clear(message: types.Message) -> None:
    chat_id = str(message.chat.id)
    user_data = await getUserData(chat_id)
    if user_data:
        user_data["context"] = []
        database.update_user(chat_id, user_data)
        print(f"Cleared context for {message.from_user.full_name}")
    await message.reply("Your message context history was cleared.")

async def switchModel(model) -> None:
    global CURRENTMODEL
    CURRENTMODEL = model
    print(f"Switched Model to: " + CURRENTMODEL)
    
@dp.message_handler(commands=['usage'])
@restricted
async def usage(message: types.Message) -> None:
    chat_id = str(message.chat.id)
    user_data = database.get_user(chat_id)
    user_usage = user_data["usage"]
    total_usage = database.get_total_usage()

    user_spent = round((((user_usage['chatgpt'] / 750) * 0.002) + (float(user_usage['dalle']) * 0.02) + ((user_usage['whisper'] / 60.0) * 0.006)), 4)
    total_spent = round((((total_usage['chatgpt'] / 750) * 0.002) + (float(total_usage['dalle']) * 0.02) + ((total_usage['whisper'] / 60.0) * 0.006)), 4)

    user_percentage = (user_spent / total_spent) * 100 if total_spent > 0 else 0

    info_message = f"""User: {message.from_user.full_name}
- Used ~{user_usage["chatgpt"]} tokens with ChatGPT.
- Generated {user_usage["dalle"]} images with DALL-E.
- Transcribed {round(float(user_usage["whisper"]) / 60.0, 2)}min with Whisper.

Total spent: ${user_spent} ({user_percentage:.2f}% of total)

Total usage:
- ChatGPT tokens: {total_usage["chatgpt"]}
- DALL-E images: {total_usage["dalle"]}
- Whisper transcription: {round(float(total_usage["whisper"]) / 60.0, 2)}min

Total spent: ${total_spent}"""

    await message.reply(info_message)

@dp.message_handler(lambda message: message.chat.type == types.ChatType.PRIVATE, content_types=['text'], regexp='^/correctnumber')
@restricted
async def reply42(message: types.Message):
    await message.reply("Yes, 42 is the way")

@dp.message_handler(lambda message: message.chat.type == types.ChatType.PRIVATE, content_types=['text'], regexp='^/imagine')
@restricted
async def imagine(message: types.Message):
    await bot.send_chat_action(message.chat.id, action=types.ChatActions.TYPING)
    user_data = await getUserData(message.chat.id)
    url = openai_integration.generateImage(user_data, message.text, ImageResolution.SMALL)
    database.update_user(str(message.chat.id), user_data)
    await message.reply(url)
    
@dp.message_handler(content_types=['photo', 'video', 'audio', 'voice'])
@restricted
async def attachment(message: types.Message):
    chat_id = message.chat.id
    user_data = await getUserData(chat_id)
    await bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)
    
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

    file = await bot.get_file(file_id)
    user_id = message.chat.id
    await file.download(f"{user_id}.{file_format}")
    
    if file_format == "ogg":
        ogg_audio = AudioSegment.from_file(f"{user_id}.ogg", format="ogg")
        ogg_audio.export(f"{user_id}.mp3", format="mp3")
        os.remove(f"{user_id}.ogg")
        file_format = "mp3"

    with open(f"{user_id}.{file_format}", "rb") as audio_file:
        await bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)
        transcript = openai_integration.transcribeAudio(user_data, audio_file, duration)

    os.remove(f"{user_id}.{file_format}")

    if transcript['text'] == "":
        transcript['text'] = "[Silence]"

    chatGPT_response = False
    if audioMessage and user_data["options"]["whisper_to_chat"]:
        chatGPT_response, user_data = await messageLLM(transcript['text'], str(chat_id), message.from_user.full_name, user_data)
        transcript['text'] = "> " + transcript['text'] + "\n\n" + chatGPT_response
    
    await message.reply(transcript['text'])
    if user_data["options"]["assistant_voice_chat"] and chatGPT_response:
            await bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)
            voice_data = await text_to_voice(chatGPT_response)
            await message.reply_voice(voice_data)
    
    database.update_user(str(chat_id), user_data)
    
@restricted
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

@dp.message_handler(lambda message: message.chat.type == types.ChatType.PRIVATE and not message.text.startswith("/"), content_types=['text'])
@restricted
async def chat(message: types.Message):
    chat_id = str(message.chat.id)
    user_data = await getUserData(chat_id)
    
    user_prompt = message.text
    await bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)
    assistant_message, user_data = await messageLLM(user_prompt, chat_id, message.from_user.full_name, user_data)
    
    await message.reply(assistant_message, parse_mode=ParseMode.MARKDOWN)
    
    if user_data["options"]["assistant_voice_chat"]:
        await bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)
        voice_data = await textToVoice.textToVoice(assistant_message)
        await message.reply_voice(voice_data)

if __name__ == '__main__':
    database.init_database()

    try:
        ALLOWED_USERS = os.environ.get("BOT_ALLOWED_USERS").split(";")
    except Exception as e:
        print(e)
        ALLOWED_USERS = ALLOWED_USERS
        
    print(f"Allowed users: {ALLOWED_USERS}")
    print(f"System prompt: {SYSTEM_PROMPT}")
    print(f"TTS: {ENABLE_TTS}")
    CURRENTMODEL = MODEL
    print(f"Using " + MODEL)
    
    # Register message handler and callback query handler for settings
    dp.register_message_handler(settings, commands=['settings'])
    dp.register_callback_query_handler(settings_callback, lambda c: c.data.startswith('setting_'))

    executor.start_polling(dp, skip_updates=True)
