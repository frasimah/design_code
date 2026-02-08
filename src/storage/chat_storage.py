
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
import time
import json

class ChatStorage:
    """Simple SQLite storage for chat history"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    product_slugs TEXT
                )
            """)
            # Migration: add product_slugs column if it doesn't exist
            cursor = conn.execute("PRAGMA table_info(messages)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'product_slugs' not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN product_slugs TEXT")
            conn.commit()
            
    def add_message(self, user_id: str, role: str, content: str, product_slugs: Optional[List[str]] = None):
        """Add a message to history"""
        slugs_json = json.dumps(product_slugs) if product_slugs else None
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (user_id, role, content, timestamp, product_slugs) VALUES (?, ?, ?, ?, ?)",
                (str(user_id), role, content, time.time(), slugs_json)
            )
            conn.commit()
            
    def get_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent chat history for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT role, content, product_slugs FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (str(user_id), limit)
            )
            rows = cursor.fetchall()
            
        # Return in chronological order (oldest first)
        history = []
        for row in rows[::-1]:
            item = {"role": row[0], "parts": [row[1]]}
            if row[2]:
                try:
                    item["product_slugs"] = json.loads(row[2])
                except:
                    pass
            history.append(item)
        return history

    def clear_history(self, user_id: str):
        """Clear history for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE user_id = ?", (str(user_id),))
            conn.commit()
