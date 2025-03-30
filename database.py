import sqlite3
import json



DB_PATH = "bot_database.db"



def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Existing Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            language_level TEXT,
            progress_json TEXT
        )
    """)

    # New table for Activity 1 word completions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CompletedWords1 (
            user_id INTEGER,
            word TEXT,
            PRIMARY KEY (user_id, word)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized!")

def register_user(user_id, name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Default progress is an empty JSON object
    cursor.execute("""
        INSERT OR IGNORE INTO Users (user_id, name, progress_json)
        VALUES (?, ?, ?)
    """, (user_id, name, json.dumps({})))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, name, language_level, progress_json
        FROM Users
        WHERE user_id=?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row  # (user_id, name, language_level, progress_json) or None

def update_progress(user_id, new_progress):
    """Update the progress_json field for the user (not heavily used yet)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Users
        SET progress_json = ?
        WHERE user_id = ?
    """, (new_progress, user_id))
    conn.commit()
    conn.close()

############################################
# NEW FUNCTIONS for CompletedWords1 TABLE
############################################

def get_completed_words1(user_id, as_list=False):
    """
    Returns completed words for Activity 1. 
    - By default, returns a set.
    - If as_list=True, returns a list instead.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT word FROM CompletedWords1 WHERE user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    words = [row[0] for row in rows]
    return words if as_list else set(words)


def mark_completed_words1(user_id, words):
    """
    Inserts each word into the CompletedWords1 table for the user.
    Using 'INSERT OR IGNORE' so duplicates won’t cause an error.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for w in words:
        cursor.execute("""
            INSERT OR IGNORE INTO CompletedWords1 (user_id, word)
            VALUES (?, ?)
        """, (user_id, w))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
