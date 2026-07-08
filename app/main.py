import logging
import time
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from app.core.logging_config import setup_logging
from app.core.config import settings
from app.routers import roadmap, project, chat

# Setup logging before anything else
setup_logging()
logger = logging.getLogger("app.main")

app = FastAPI(
    title="AI Learning Assistant",
    description="FastAPI Backend for personalized learning roadmap and RAG-based chat",
    version="1.0.0"
)

# Request/Response Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    method = request.method
    path = request.url.path
    logger.info(f"---> Incoming Request: {method} {path}")
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(f"<--- Outgoing Response: {method} {path} | Status: {response.status_code} | Duration: {duration:.4f}s")
        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"<--- Request Failed: {method} {path} | Error: {str(e)} | Duration: {duration:.4f}s")
        return await global_exception_handler(request, e)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Pass through standard HTTPExceptions with their status codes
    if isinstance(exc, HTTPException):
        logger.warning(f"HTTPException occurred: status={exc.status_code}, detail={exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
        
    # Pass through validation errors with 422
    if isinstance(exc, RequestValidationError):
        logger.warning(f"RequestValidationError occurred: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()}
        )
        
    # Catch-all for unexpected internal exceptions (avoids leaking stack traces)
    logger.error(f"Unhandled Exception occurred: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected internal server error occurred. Please check the logs for details."}
    )

# Register routers
app.include_router(roadmap.router)
app.include_router(project.router)
app.include_router(chat.router)

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "llm_model": settings.LLM_MODEL,
        "chroma_db_path": settings.CHROMA_DB_PATH
    }

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")
