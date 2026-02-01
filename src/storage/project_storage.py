
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from slugify import slugify

class ProjectStorage:
    """SQLite storage for user projects"""
    
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
                    items_json TEXT NOT NULL
                )
            """)
            conn.commit()
            
            # Migration: add slug column if missing (without UNIQUE - SQLite limitation)
            cursor = conn.execute("PRAGMA table_info(projects)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'slug' not in columns:
                conn.execute("ALTER TABLE projects ADD COLUMN slug TEXT")
                conn.commit()
            
    def save_projects(self, projects: List[Dict[str, Any]]):
        """Overwrite all projects in the database"""
        with sqlite3.connect(self.db_path) as conn:
            # Simple approach for a single user: clear and re-insert
            conn.execute("DELETE FROM projects")
            for p in projects:
                # Generate slug from name if not provided
                slug = p.get('slug') or slugify(p['name'], lowercase=True)
                conn.execute(
                    "INSERT INTO projects (id, name, slug, items_json) VALUES (?, ?, ?, ?)",
                    (p['id'], p['name'], slug, json.dumps(p['items'], ensure_ascii=False))
                )
            conn.commit()
            
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, name, slug, items_json FROM projects")
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
    
    def get_project_by_slug(self, slug_or_id: str) -> Optional[Dict[str, Any]]:
        """Get a single project by slug or ID"""
        with sqlite3.connect(self.db_path) as conn:
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
