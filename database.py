import sqlite3
import json

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
            temperature REAL,
            max_context INTEGER
        )
    """)
    print("Database initialized")
    conn.commit()
    conn.close()
    
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
                "temperature": user[7],
                "max-context": user[8]
            }
        }
    return None

def add_user(chat_id: str, user_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO users (
            chat_id, context, usage_chatgpt, usage_whisper, usage_dalle,
            whisper_to_chat, assistant_voice_chat, temperature, max_context
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        chat_id,
        json.dumps(user_data["context"]),
        user_data["usage"]["chatgpt"],
        user_data["usage"]["whisper"],
        user_data["usage"]["dalle"],
        int(user_data["options"]["whisper_to_chat"]),
        int(user_data["options"]["assistant_voice_chat"]),
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