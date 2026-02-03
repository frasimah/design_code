
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from src.ai.consultant import Consultant
from config.settings import DATA_DIR, PROJECT_ROOT
from src.api.auth.jwt import get_current_user, require_auth

router = APIRouter()
consultant = Consultant()

class ChatRequest(BaseModel):
    query: str
    image: Optional[str] = None
    history: Optional[List[dict]] = []
    sources: Optional[List[str]] = None

class ChatResponse(BaseModel):
    answer: str
    products: Optional[List[dict]] = []

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, user: Optional[dict] = Depends(get_current_user)):
    """
    Chat with the AI consultant.
    """
    try:
        # Use authenticated user ID or fallback to anonymous
        user_id = user.get("id") if user else "anonymous"
        
        # Handle image if provided
        image_path = None
        if request.image:
            import base64
            import uuid
            import os
            
            # Create tmp dir if doesn't exist
            tmp_dir = DATA_DIR / "tmp"
            tmp_dir.mkdir(exist_ok=True)
            
            # Decode image
            image_data = request.image
            if "base64," in image_data:
                image_data = image_data.split("base64,")[1]
            
            # Save to temporary file
            image_path = tmp_dir / f"{uuid.uuid4()}.jpg"
            with open(image_path, "wb") as f:
                f.write(base64.b64decode(image_data))
            
            image_path = str(image_path)

        consultant_result = consultant.answer(
            request.query, 
            image_path=image_path, 
            user_id=user_id,
            sources=request.sources
        )
        response_text = consultant_result.get("answer", "")
        
        # Clean up temp image
        if image_path and os.path.exists(image_path):
            try:
                # os.remove(image_path)
                pass 
            except Exception:
                pass
        
        # Get relevant products for context to display them
        # Get relevant products for context to display them
        relevant_products = consultant_result.get("products")
        # Fallback removed: only show products explicitly recommended by AI logic
        
        # Flatten product structure for frontend
        flattened_products = []
        for r in relevant_products:
            # If it's already a flat dict, use it directly
            if 'details' not in r:
                 flattened_products.append(r)
                 continue
                 
            details = r.get('details', {})
            flat_product = {
                **details,
                "slug": r.get('slug'),
                "distance": r.get('distance'),
                # "vision_confidence": r.get('vision_confidence'),
            }
            if 'details' in flat_product:
                del flat_product['details']
            flattened_products.append(flat_product)
        
        return {
            "answer": response_text,
            "products": flattened_products
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/", response_model=List[dict])
async def get_history(user: Optional[dict] = Depends(get_current_user)):
    """
    Get chat history for the authenticated user.
    """
    user_id = user.get("id") if user else "anonymous"
    raw_history = consultant.storage.get_history(user_id, limit=50)
    # Format for frontend: role, content (instead of parts)
    formatted = []
    for item in raw_history:
        formatted.append({
            "role": "user" if item["role"] == "user" else "assistant",
            "content": item["parts"][0] if item["parts"] else ""
        })
    return formatted

