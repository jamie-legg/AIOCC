"""Main FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
import time
from .config import settings
from .database import engine, Base
from .api import auth, enrichment, oauth_proxy, analytics, studio


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    print("Starting AIOCC Upload Studio API...")
    
    # Create database tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created")
    
    yield
    
    # Shutdown
    print("Shutting down AIOCC Upload Studio API...")


# Create FastAPI app
app = FastAPI(
    title="AIOCC Upload Studio API",
    description="Backend API for flat-file clip uploads and AI metadata",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing."""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    print(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    return response


# Include routers
app.include_router(auth.router)
app.include_router(enrichment.router)
app.include_router(oauth_proxy.router)
app.include_router(analytics.router)
app.include_router(studio.router)
app.include_router(studio.callback_router)

Path(settings.studio_upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.studio_upload_dir), name="uploads")


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "AIOCC Upload Studio API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    print(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

