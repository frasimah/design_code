from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config.settings import DATA_DIR, UPLOAD_DIR, PROJECT_ROOT
from src.api.routes import chat, currency, import_url, products, projects, upload, vision, print_proposal, profile

app = FastAPI(
    title="Design Code API",
    description="API for furniture catalog and AI consultant",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://panel.de-co-de.ru",
        "http://panel.de-co-de.ru",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(vision.router, prefix="/api/search", tags=["search"])
app.include_router(import_url.router, prefix="/api/import-url", tags=["import"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(currency.router, prefix="/api/currency", tags=["currency"])
app.include_router(print_proposal.router, prefix="/api/print", tags=["print"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])

# Mount static files
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Static files from Design code public folder (if exists)
STATIC_DIR = PROJECT_ROOT.parent / "Design code" / "public"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def root():
    return {"message": "Lick Brick API is running"}
