import logging
import uvicorn
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.config.settings import get_settings
from app.services.mem0_client import close_mem0_client, get_mem0_client


def setup_logging():
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=settings.LOG_FORMAT,
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)


logger = setup_logging()
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting memory service...")

    try:
        settings = get_settings()
        logger.info(f"Service configuration loaded: {settings.SERVICE_NAME}")

        try:
            mem0_client = get_mem0_client(settings)
            app.state.mem0_client = mem0_client
            logger.info("mem0 client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize mem0 client: {e}")

        logger.info("Memory service started successfully")
        yield

    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise
    finally:
        logger.info("Shutting down memory service...")
        close_mem0_client()
        logger.info("Memory service shutdown complete")

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Memory Service API",
        description="API for storing and retrieving user memories using mem0",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.include_router(api_router)


    from fastapi.exceptions import RequestValidationError
    from starlette.requests import Request as StarletteRequest

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: StarletteRequest, exc: RequestValidationError):
        logger.warning(f"Validation error on {request.method} {request.url}: {exc.errors()}")
        errors = []
        for err in exc.errors():
            loc = ' -> '.join(str(l) for l in err.get('loc', []))
            msg = err.get('msg', 'Invalid input')
            errors.append({"location": loc, "message": msg})
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Validation error",
                "errors": errors
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Global exception on {request.method} {request.url}: {exc}", exc_info=True
        )

        error_detail = str(exc) if settings.DEBUG else "An internal error occurred"

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal server error",
                "detail": error_detail,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(
            f"HTTP exception on {request.method} {request.url}: "
            f"{exc.status_code} - {exc.detail}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "status_code": exc.status_code,
            },
        )

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "service": settings.SERVICE_NAME,
            "status": "running",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/v1/health",
            "endpoints": {
                "store_memory": "POST /api/v1/memories",
                "search_memories": "POST /api/v1/memories/search",
                "get_user_memories": "GET /api/v1/memories/{username}",
                "delete_user_memories": "DELETE /api/v1/memories/{username}",
            },
        }

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        logger.info(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
        return response

    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()

    logger.info(f"Starting {settings.SERVICE_NAME} server...")
    logger.info(f"Server will run on {settings.HOST}:{settings.PORT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")

    uvicorn.run(
        "app.main:app", 
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
