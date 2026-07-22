import sqlite3
import os

# Adjusting path to look in the current directory, not 'backend/backend'
db_path = "vektra_dev.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(snapshots);")
    columns = cursor.fetchall()
    
    if not columns:
        print("No columns found. Does the table 'snapshots' exist?")
    else:
        for col in columns:
            print(col)
            
    conn.close()
except Exception as e:
    print(f"Error connecting to database: {e}")
