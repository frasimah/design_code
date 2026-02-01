
import sqlite3
from pathlib import Path
from typing import List, Dict
import time

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
                    timestamp REAL NOT NULL
                )
            """)
            conn.commit()
            
    def add_message(self, user_id: str, role: str, content: str):
        """Add a message to history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (str(user_id), role, content, time.time())
            )
            conn.commit()
            
    def get_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent chat history for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT role, content FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (str(user_id), limit)
            )
            rows = cursor.fetchall()
            
        # Return in chronological order (oldest first)
        history = [{"role": row[0], "parts": [row[1]]} for row in rows][::-1]
        return history

    def clear_history(self, user_id: str):
        """Clear history for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE user_id = ?", (str(user_id),))
            conn.commit()
