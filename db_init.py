import sqlite3
import os
from developer import hash_password

DB_PATH = os.path.join("instance", "developer.db")

# Main dev account details
MAIN_DEV = {
    "full_name": "Vedant Chitre",
    "email": "arunakchitre@gmail.com",
    "mobile": "9869345997",
    "password": "Vedant2009$",
    "role": "main"
}

def initialize_developer_db():
    if not os.path.exists("instance"):
        os.makedirs("instance")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ✅ Create table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS developers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        mobile TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'sub-dev',
        face_encoding BLOB
    )
    """)

    # ✅ Check for main dev
    cursor.execute("SELECT id FROM developers WHERE email = ?", (MAIN_DEV["email"],))
    if not cursor.fetchone():
        pw_hash = hash_password(MAIN_DEV["password"])
        cursor.execute("""
            INSERT INTO developers (full_name, email, mobile, password_hash, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            MAIN_DEV["full_name"],
            MAIN_DEV["email"],
            MAIN_DEV["mobile"],
            pw_hash,
            MAIN_DEV["role"]
        ))
        print("✅ Main developer created.")
    else:
        print("ℹ️ Main developer already exists.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_developer_db()
