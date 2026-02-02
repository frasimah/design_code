from fastapi import APIRouter, Depends
from typing import List, Dict, Any, Optional
import json
import os
from config.settings import DATA_DIR
from pydantic import BaseModel
from src.storage.project_storage import ProjectStorage
from src.api.auth.jwt import get_current_user, require_auth

router = APIRouter()

# Use separate database for tests to avoid destroying production data
if os.environ.get("TEST_MODE"):
    DB_FILE = DATA_DIR / "test_user_data.db"
else:
    DB_FILE = DATA_DIR / "user_data.db"
storage = ProjectStorage(DB_FILE)

# Migration from JSON to SQLite
JSON_FILE = DATA_DIR / "user_projects.json"
if JSON_FILE.exists():
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
            if old_data:
                storage.save_projects(old_data)
        # Rename to mark as migrated
        JSON_FILE.rename(JSON_FILE.with_suffix('.json.bak'))
    except Exception as e:
        print(f"Migration error: {e}")

class Project(BaseModel):
    id: str
    name: str
    items: List[Dict[str, Any]]

@router.get("/", response_model=List[Project])
async def get_projects(user: Optional[dict] = Depends(get_current_user)):
    """Get projects for the authenticated user"""
    user_id = user.get("id") if user else None
    return storage.get_projects(user_id)

@router.post("/", response_model=List[Project])
async def save_all_projects(
    projects: List[Project],
    user: dict = Depends(require_auth)
):
    """Save projects for the authenticated user"""
    projects_data = [p.model_dump() for p in projects]
    storage.save_projects(projects_data, user["id"])
    return projects

