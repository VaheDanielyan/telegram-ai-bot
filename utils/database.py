import sqlite3
import json
import asyncio

from integrations.openai_integration import ImageResolution

DB_PATH = "db_data/users.db"

def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id TEXT PRIMARY KEY,
            context TEXT,
            usage_chatgpt INTEGER,
            usage_whisper INTEGER,
            usage_dalle INTEGER,
            whisper_to_chat INTEGER,
            assistant_voice_chat INTEGER,
            image_resolution TEXT,
            temperature REAL,
            max_context INTEGER
        )
    """)
    print("Database initialized")
    conn.commit()
    conn.close()
    
async def getUserData(chat_id, config):
    user_data = get_user(chat_id)
    if not user_data:
        user_data = {
            "context": [],
            "usage": {"chatgpt": 0, "whisper": 0, "dalle": 0},
            "options": {
                "whisper_to_chat": config.bot_asr_to_chat,
                "assistant_voice_chat": False,
                "image_resolution": ImageResolution.MEDIUM.value,
                "temperature": float(config.openai_gpt_default_temperature),
                "max-context": config.chat_max_context
            }
        }
        add_user(chat_id, user_data)
        user_data = get_user(chat_id)
    return user_data

def clearUserContext(chat_id):
    user_data = getUserData(chat_id)
    user_data["context"] = []
    update_user(chat_id, user_data)

def get_user(chat_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return {
            "context": json.loads(user[1]),
            "usage": {
                "chatgpt": user[2],
                "whisper": user[3],
                "dalle": user[4]
            },
            "options": {
                "whisper_to_chat": bool(user[5]),
                "assistant_voice_chat": bool(user[6]),
                "image_resolution": str(user[7]),
                "temperature": user[8],
                "max-context": user[9]
            }
        }
    return None

def add_user(chat_id: str, user_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO users (
            chat_id, context, usage_chatgpt, usage_whisper, usage_dalle,
            whisper_to_chat, assistant_voice_chat, image_resolution, temperature, max_context
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        chat_id,
        json.dumps(user_data["context"]),
        user_data["usage"]["chatgpt"],
        user_data["usage"]["whisper"],
        user_data["usage"]["dalle"],
        int(user_data["options"]["whisper_to_chat"]),
        int(user_data["options"]["assistant_voice_chat"]),
        user_data["options"]["image_resolution"],
        user_data["options"]["temperature"],
        user_data["options"]["max-context"]
    ))
    conn.commit()
    conn.close()

def update_user(chat_id: str, user_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE users
        SET
            context = ?,
            usage_chatgpt = ?,
            usage_whisper = ?,
            usage_dalle = ?,
            whisper_to_chat = ?,
            assistant_voice_chat = ?,
            image_resolution = ?,
            temperature = ?,
            max_context = ?
        WHERE chat_id = ?
    """, (
        json.dumps(user_data["context"]),
        user_data["usage"]["chatgpt"],
        user_data["usage"]["whisper"],
        user_data["usage"]["dalle"],
        int(user_data["options"]["whisper_to_chat"]),
        int(user_data["options"]["assistant_voice_chat"]),
        user_data["options"]["image_resolution"],
        user_data["options"]["temperature"],
        user_data["options"]["max-context"],
        chat_id
    ))
    conn.commit()
    conn.close()
    
def get_total_usage():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT
            SUM(usage_chatgpt) AS total_chatgpt,
            SUM(usage_whisper) AS total_whisper,
            SUM(usage_dalle) AS total_dalle
        FROM users
    """)
    total_usage = c.fetchone()
    conn.close()
    return {
        "chatgpt": total_usage[0],
        "whisper": total_usage[1],
        "dalle": total_usage[2]
    }
