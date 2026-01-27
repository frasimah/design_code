
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.ai.consultant import BrickConsultant
from config.settings import DATA_DIR, PROJECT_ROOT

router = APIRouter()
consultant = BrickConsultant()

class ChatRequest(BaseModel):
    query: str
    image: Optional[str] = None
    history: Optional[List[dict]] = []

class ChatResponse(BaseModel):
    answer: str
    products: Optional[List[dict]] = []
    simulation_image: Optional[str] = None

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the AI consultant.
    """
    try:
        # Get relevant products for context
        # Note: BrickConsultant.answer handles history internally via storage if user_id is provided,
        # but here we might want to be stateless or handle session ID.
        # For now, we'll use a simple wrapper around answer().
        
        # We can pass a session_id in headers or body if we want persistent history per user
        # For now, let's just use a default session or generate one.
        
        # Actually, BrickConsultant.answer takes user_id. Let's assume a single user for now or
        # let the frontend generate a session ID.
        
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

        consultant_result = consultant.answer(request.query, image_path=image_path, user_id="api_user")
        response_text = consultant_result.get("answer", "")
        simulation_bytes = consultant_result.get("simulation_image")
        
        simulation_url = None
        if simulation_bytes:
            # Save simulation image
            import uuid
            gen_dir = PROJECT_ROOT / "brick-catalog" / "public" / "generated"
            gen_dir.mkdir(parents=True, exist_ok=True)
            
            gen_filename = f"simulation_{uuid.uuid4()}.jpg"
            gen_path = gen_dir / gen_filename
            with open(gen_path, "wb") as f:
                f.write(simulation_bytes)
            
            simulation_url = f"/generated/{gen_filename}"

        # Clean up temp image
        if image_path and os.path.exists(image_path):
            try:
                # os.remove(image_path)
                pass 
            except:
                pass
        
        # Get relevant products for context to display them
        # Use products returned by answer() if available (e.g. joints), otherwise search
        relevant_products = consultant_result.get("products")
        if not relevant_products:
            relevant_products = consultant.search_products(request.query, n_results=30)
        
        # Flatten product structure for frontend
        flattened_products = []
        for r in relevant_products:
            # If it's already a flat dict (from joints logic), use it directly
            if 'details' not in r and 'slug' in r:
                 flattened_products.append(r)
                 continue
                 
            details = r.get('details', {})
            flat_product = {
                **details,
                "slug": r.get('slug'),
                "distance": r.get('distance'),
                "vision_confidence": r.get('vision_confidence'),
            }
            if 'details' in flat_product:
                del flat_product['details']
            flattened_products.append(flat_product)
        
        return {
            "answer": response_text,
            "products": flattened_products,
            "simulation_image": simulation_url
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
