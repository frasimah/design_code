
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from slugify import slugify

class ProjectStorage:
    """SQLite storage for user projects and profiles"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize database schema"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT UNIQUE,
                    items_json TEXT NOT NULL,
                    user_id TEXT
                )
            """)
            
            # User profiles table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    manager_name TEXT,
                    phone TEXT,
                    email TEXT,
                    company_name TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            
            # Migration: add columns if missing
            cursor = conn.execute("PRAGMA table_info(projects)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'slug' not in columns:
                conn.execute("ALTER TABLE projects ADD COLUMN slug TEXT")
                conn.commit()
            if 'user_id' not in columns:
                conn.execute("ALTER TABLE projects ADD COLUMN user_id TEXT")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id)")
                conn.commit()
            
    def save_projects(self, projects: List[Dict[str, Any]], user_id: Optional[str] = None):
        """Save projects for a specific user (or all if user_id is None for backward compat)"""
        with sqlite3.connect(self.db_path) as conn:
            if user_id:
                # Delete only this user's projects
                conn.execute("DELETE FROM projects WHERE user_id = ?", (user_id,))
            else:
                # Backward compatibility: delete all
                conn.execute("DELETE FROM projects")
            
            for p in projects:
                slug = p.get('slug') or slugify(p['name'], lowercase=True)
                conn.execute(
                    "INSERT OR REPLACE INTO projects (id, name, slug, items_json, user_id) VALUES (?, ?, ?, ?, ?)",
                    (p['id'], p['name'], slug, json.dumps(p['items'], ensure_ascii=False), user_id)
                )
            conn.commit()
            
    def get_projects(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get projects for a specific user. Returns empty list for unauthenticated users."""
        if not user_id:
            # Unauthenticated users don't see any personal projects
            return []
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, name, slug, items_json FROM projects WHERE user_id = ?",
                (user_id,)
            )
            rows = cursor.fetchall()
            
        projects = []
        for row in rows:
            projects.append({
                "id": row[0],
                "name": row[1],
                "slug": row[2] or slugify(row[1], lowercase=True),
                "items": json.loads(row[3])
            })
        return projects
    
    def get_project_by_slug(self, slug_or_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a single project by slug or ID, optionally filtered by user"""
        with sqlite3.connect(self.db_path) as conn:
            if user_id:
                cursor = conn.execute(
                    "SELECT id, name, slug, items_json FROM projects WHERE (slug = ? OR id = ?) AND user_id = ?",
                    (slug_or_id, slug_or_id, user_id)
                )
            else:
                cursor = conn.execute(
                    "SELECT id, name, slug, items_json FROM projects WHERE slug = ? OR id = ?",
                    (slug_or_id, slug_or_id)
                )
            row = cursor.fetchone()
            
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "slug": row[2],
                "items": json.loads(row[3])
            }
        return None

    # User Profile Methods
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by user_id"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT manager_name, phone, email, company_name FROM user_profiles WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            
        if row:
            return {
                "manager_name": row[0] or "",
                "phone": row[1] or "",
                "email": row[2] or "",
                "company_name": row[3] or ""
            }
        return None
    
    def save_user_profile(self, user_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Save or update user profile"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_profiles (user_id, manager_name, phone, email, company_name, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                user_id,
                profile.get("manager_name", ""),
                profile.get("phone", ""),
                profile.get("email", ""),
                profile.get("company_name", "")
            ))
            conn.commit()
        return self.get_user_profile(user_id)
