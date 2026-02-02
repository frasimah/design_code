"""
User Profile API routes.
Handles user settings like contact info for commercial proposals.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from config.settings import DATA_DIR
from src.storage.project_storage import ProjectStorage
from src.api.auth.jwt import get_current_user, require_auth

router = APIRouter()

# Use same database as projects
if os.environ.get("TEST_MODE"):
    DB_FILE = DATA_DIR / "test_user_data.db"
else:
    DB_FILE = DATA_DIR / "user_data.db"
storage = ProjectStorage(DB_FILE)


class UserProfile(BaseModel):
    manager_name: str = ""
    phone: str = ""
    email: str = ""
    company_name: str = ""


class ProfileResponse(BaseModel):
    manager_name: str
    phone: str
    email: str
    company_name: str


@router.get("/", response_model=ProfileResponse)
async def get_profile(user: dict = Depends(require_auth)):
    """Get the authenticated user's profile"""
    profile = storage.get_user_profile(user["id"])
    if not profile:
        # Return empty profile if not set
        return ProfileResponse(manager_name="", phone="", email="", company_name="")
    return ProfileResponse(**profile)


@router.put("/", response_model=ProfileResponse)
async def save_profile(
    profile: UserProfile,
    user: dict = Depends(require_auth)
):
    """Save or update the authenticated user's profile"""
    print(f"[PROFILE DEBUG] Saving profile for user {user.get('id')}: {profile}")
    try:
        # Log to file for debugging
        with open("profile_debug.log", "a") as f:
            f.write(f"Saving profile for user {user.get('id')}: {profile}\n")
            
        saved = storage.save_user_profile(user["id"], profile.model_dump())
        
        with open("profile_debug.log", "a") as f:
            f.write(f"Save successful: {saved}\n")
            
        print(f"[PROFILE DEBUG] Save successful: {saved}")
        return ProfileResponse(**saved)
    except Exception as e:
        with open("profile_debug.log", "a") as f:
            f.write(f"Save failed: {e}\n")
        print(f"[PROFILE DEBUG] Save failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
