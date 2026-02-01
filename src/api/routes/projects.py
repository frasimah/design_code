from fastapi import APIRouter
from typing import List, Dict, Any
import json
from config.settings import DATA_DIR
from pydantic import BaseModel
from src.storage.project_storage import ProjectStorage

router = APIRouter()

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
    slug: str
    items: List[Dict[str, Any]]

@router.get("/", response_model=List[Project])
async def get_projects():
    return storage.get_projects()

@router.post("/", response_model=List[Project])
async def save_all_projects(projects: List[Project]):
    # Convert Pydantic models to dicts
    projects_data = [p.model_dump() for p in projects]
    storage.save_projects(projects_data)
    return projects
