
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import products, chat, vision

app = FastAPI(
    title="Lick Brick API",
    description="API for Vandersanden brick catalog and AI consultant",
    version="0.1.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(vision.router, prefix="/api/search", tags=["search"])

@app.get("/")
async def root():
    return {"message": "Lick Brick API is running"}
