import sqlite3

db_path = "instance/appointments.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Add columns if not exist
try:
    cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0;")
except sqlite3.OperationalError:
    print("Column 'is_admin' already exists.")

try:
    cur.execute("ALTER TABLE users ADD COLUMN is_developer INTEGER DEFAULT 0;")
except sqlite3.OperationalError:
    print("Column 'is_developer' already exists.")

conn.commit()
conn.close()
print("✅ Columns added or already exist.")
