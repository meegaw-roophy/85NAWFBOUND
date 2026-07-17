import sqlite3
import os

# Path to the database file
db_path = os.path.join("backend", "vektra_dev.db")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add columns if they don't exist
    # Using a try-except block for each execute to handle cases where column might exist
    try:
        cursor.execute("ALTER TABLE snapshots ADD COLUMN last_trash_talk_sent TEXT;")
        print("Column 'last_trash_talk_sent' added.")
    except sqlite3.OperationalError as e:
        print(f"Note on 'last_trash_talk_sent': {e}")
        
    try:
        cursor.execute("ALTER TABLE snapshots ADD COLUMN trash_talk_count INTEGER DEFAULT 0;")
        print("Column 'trash_talk_count' added.")
    except sqlite3.OperationalError as e:
        print(f"Note on 'trash_talk_count': {e}")
        
    conn.commit()
    print("Database patch completed.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if conn:
        conn.close()
