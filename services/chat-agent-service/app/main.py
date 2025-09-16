from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.api.router import api_router
from app.config.settings import settings
from app.services.agent_manager import AgentManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_manager = None

rate_limit_storage = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_manager
    
    logger.info("Starting LiveKit Chat Agent Service...")
    agent_manager = AgentManager()
    await agent_manager.initialize()
    
    app.state.agent_manager = agent_manager
    
    yield
    
    logger.info("Shutting down LiveKit Chat Agent Service...")
    if agent_manager:
        await agent_manager.cleanup()

app = FastAPI(
    title="LiveKit Chat Agent Service",
    description="Real-time AI chat agent with memory-enhanced conversations",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def validate_request_size(request: Request):
    """Check request size before processing"""
    content_length = request.headers.get('content-length')
    max_size = 1024 * 10 
    
    if content_length and int(content_length) > max_size:
        logger.warning(f"Request too large from {request.client.host}: {content_length} bytes")
        raise HTTPException(
            status_code=413,
            detail={
                "success": False,
                "message": f"Request body too large. Maximum size allowed: {max_size} bytes",
                "error_code": "REQUEST_TOO_LARGE",
                "max_size": max_size
            }
        )

async def check_rate_limit(request: Request):
    global rate_limit_storage
    
    if request.url.path == "/health":
        return
    
    client_ip = request.client.host
    current_time = time.time()
    max_requests = 100
    window = 60  
    
    rate_limit_storage = {
        ip: requests for ip, requests in rate_limit_storage.items()
        if any(req_time > current_time - window for req_time in requests)
    }
    
    if client_ip not in rate_limit_storage:
        rate_limit_storage[client_ip] = []
    
    rate_limit_storage[client_ip] = [
        req_time for req_time in rate_limit_storage[client_ip]
        if req_time > current_time - window
    ]
    
    if len(rate_limit_storage[client_ip]) >= max_requests:
        logger.warning(f"Rate limit exceeded for {client_ip}: {len(rate_limit_storage[client_ip])} requests")
        raise HTTPException(
            status_code=429,
            detail={
                "success": False,
                "message": f"Rate limit exceeded. Maximum {max_requests} requests per {window} seconds",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "retry_after": window
            }
        )
    
    rate_limit_storage[client_ip].append(current_time)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "chat-agent-service",
        "version": "1.0.0"
    }

@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    logger.warning(f"Validation error from {request.client.host}: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Invalid request data",
            "error_code": "VALIDATION_ERROR",
            "details": exc.errors() if hasattr(exc, 'errors') else str(exc)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail if isinstance(exc.detail, dict) else {
            "success": False,
            "message": str(exc.detail),
            "error_code": "HTTP_ERROR"
        }
    )

@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc):
    logger.error(f"Internal server error from {request.client.host}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )