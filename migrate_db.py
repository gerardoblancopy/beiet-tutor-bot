import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "data", "beiet.db")

def migrate():
    if not os.path.exists(db_path):
        print("No DB found to migrate.")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if we need to add tokens
    cursor.execute("PRAGMA table_info(conversation_messages)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "input_tokens" not in columns:
        print("Adding token tracking columns to db...")
        cursor.execute("ALTER TABLE conversation_messages ADD COLUMN input_tokens INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE conversation_messages ADD COLUMN output_tokens INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE conversation_messages ADD COLUMN cost REAL DEFAULT 0.0")
        conn.commit()
        print("Token tracking columns added successfully.")
    else:
        print("Token tracking metrics already exist.")
        
    conn.close()

if __name__ == "__main__":
    migrate()
