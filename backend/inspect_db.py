import sqlite3
import os

db_path = os.path.join("backend", "vektra_dev.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(snapshots);")
columns = cursor.fetchall()
for col in columns:
    print(col)

conn.close()
