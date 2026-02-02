from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from config.settings import UPLOAD_DIR
from src.api.auth.jwt import get_current_user
import uuid
import os
import mimetypes

router = APIRouter()

@router.post("/image")
async def upload_image(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not user or not user.get("id"):
        raise HTTPException(status_code=401, detail="Authentication required")
        
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Generate unique filename
    guessed_ext = mimetypes.guess_extension(file.content_type or "")
    ext = (guessed_ext or ".jpg").lstrip(".")
    filename = f"{uuid.uuid4()}.{ext}"
    file_path = UPLOAD_DIR / filename
    
    try:
        with open(file_path, "wb") as buffer:
            max_bytes = 10 * 1024 * 1024
            total = 0
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    buffer.close()
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                    raise HTTPException(status_code=413, detail="File too large")
                buffer.write(chunk)
            
        return {"url": f"/uploads/{filename}"}
    except Exception as e:
        print(f"Error saving uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")
