from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from utils.config import Config

def generateInlineKeyboard(chat_id) -> InlineKeyboardMarkup:
    keyboard = [
            [
                InlineKeyboardButton("OPENAI-GPT: Increase Temperature", callback_data=f"/setting_inc_temp"),
                InlineKeyboardButton("OPENAI-GPT: Decrease Temperature", callback_data=f"/setting_dec_temp")
                ],
            [
                InlineKeyboardButton("OPENAI-Dalle: Increase Resolution", callback_data=f"/setting_inc_resolution"),
                InlineKeyboardButton("OPENAI-Dalle: Decrease Resolution", callback_data=f"/setting_dec_resolution")
                ],
            [
                InlineKeyboardButton("OPENAI-Whisper: Enable", callback_data=f"/setting_en_whisper"),
                InlineKeyboardButton("OPENAI-Whisper: Disable", callback_data=f"/setting_dis_whisper")
                ],
            [
                InlineKeyboardButton("Google TTS: Enable voice", callback_data=f"/setting_en_voice"),
                InlineKeyboardButton("Google TTS: Disable voice", callback_data=f"/setting_dis_voice")
                ],
            [
                InlineKeyboardButton("Chat: Increase Context", callback_data=f"/setting_inc_context"),
                InlineKeyboardButton("Chat: Decrease Context", callback_data=f"/setting_dec_context")
                ]
            ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def getSettingsReport(options):
    header = "Updated settings:\n\n"
    gptModel = f"GPT-Model: {options['gpt_model']}\n"
    imageResolution = f"Image Resolution: {options['image_resolution']}\n"
    gptTemperature = f"Temperature: {options['temperature']}\n"
    whisperStatus = f"Whisper to Chat: {options['whisper_to_chat']}\n"
    assistantVoice = f"Assistant voice: {options['assistant_voice_chat']}\n" 
    contextLength = f"Context Length: {options['max-context']}"
    fullReport = header + gptModel + imageResolution + gptTemperature + whisperStatus + assistantVoice + contextLength
    return fullReport

def getUsageReport(user_data):
    user_usage = user_data["usage"]
    chatUsage = f"""- Used ~{user_usage["chatgpt"]} tokens with ChatGPT.\n"""
    imageUsage = f"""- Generated {user_usage["dalle"]} images with DALL-E.\n"""
    whisperUsage = f"""- Transcribed {round(float(user_usage["whisper"]) / 60.0, 2)}min with Whisper."""
    info_message = chatUsage + imageUsage + whisperUsage
    return info_message

def getHelpReport():
    header          = "Commands: \n\n"
    clearContext    = "/clear            - Clear the context.\n"
    dalle           = "/imagine <prompt> - Generate image with Dall-E.\n"
    settings        = "/settings         - Open config menu.\n"
    config          = "/config           - View current configuration.\n"
    switch          = "/switch           - Switch between language models.\n"
    usage           = "/usage            - See usage statistics.\n"
    help_message = header + clearContext + dallE + settings + config + switch + usage
    return help_message
