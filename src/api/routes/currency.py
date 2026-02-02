from fastapi import APIRouter, HTTPException
import aiohttp
import time

router = APIRouter(tags=["currency"])

# Simple cache: { "rate": float, "timestamp": float }
rate_cache = {
    "rate": None,
    "timestamp": 0
}
CACHE_TTL = 3600  # 1 hour

@router.get("/rate")
async def get_currency_rate():
    """Get EUR to RUB exchange rate from CBR"""
    global rate_cache
    
    current_time = time.time()
    
    # Return cached if valid
    if rate_cache["rate"] and (current_time - rate_cache["timestamp"] < CACHE_TTL):
        return {"currency": "RUB", "rate": rate_cache["rate"], "source": "cache"}
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.cbr-xml-daily.ru/daily_json.js") as response:
                if response.status != 200:
                    raise HTTPException(status_code=502, detail="Failed to fetch rates from CBR")
                
                # Use content_type=None because CBR serves JSON with application/javascript mimetype
                data = await response.json(content_type=None)
                # Extract EUR rate
                eur_rate = data.get("Valute", {}).get("EUR", {}).get("Value")
                
                if not eur_rate:
                    raise HTTPException(status_code=502, detail="EUR rate not found in CBR response")
                
                rate_cache = {
                    "rate": eur_rate,
                    "timestamp": current_time
                }
                
                return {"currency": "RUB", "rate": eur_rate, "source": "cbr"}
    except Exception as e:
        # Fallback if cache exists even if expired
        if rate_cache["rate"]:
            return {"currency": "RUB", "rate": rate_cache["rate"], "source": "cache_fallback"}
            
        print(f"Error fetching currency: {e}")
        # Last resort fallback constant (approximate)
        return {"currency": "RUB", "rate": 105.0, "source": "fallback_constant"}
