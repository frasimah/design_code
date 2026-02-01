
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from src.ai.image_search import ImageSearch
import shutil
import tempfile
from pathlib import Path

router = APIRouter()
searcher = ImageSearch()

@router.post("/", response_model=List[dict])
async def search_by_image(file: UploadFile = File(...)):
    """
    Search for products by uploading an image.
    """
    try:
        # Save uploaded file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)
        
        try:
            # Perform search
            results = searcher.search_by_image(tmp_path, n_results=30)
            
            # Clean up results to be JSON serializable and flattened for frontend
            cleaned_results = []
            for r in results:
                product_data = r.get("product", {})
                
                # Merge product data into top level
                cleaned_r = {
                    **product_data,
                    "slug": r.get("slug"),
                    "distance": r.get("distance"),
                    # Keep analysis for frontend to display match info
                    "analysis": r.get("analysis"),
                    "vision_confidence": r.get("vision_confidence")
                }
                
                # Remove internal objects that might not be serializable or duplicate
                if "details" in cleaned_r:
                    del cleaned_r["details"]
                if "product" in cleaned_r:
                    del cleaned_r["product"]
                
                cleaned_results.append(cleaned_r)
                
            return cleaned_results
            
        finally:
            # Clean up temp file
            if tmp_path.exists():
                tmp_path.unlink()
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
