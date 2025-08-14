"""
FastAPI Application for News Delivery System
ニュース配信システム FastAPIアプリケーション
CLAUDE.md仕様準拠
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Depends, Security, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn

from .utils.logger import setup_logger
from .utils.config import load_config
from .infrastructure.database import AsyncDatabase
from .infrastructure.redis_cache import RedisCache
from .infrastructure.security import SecurityManager
from .middleware.logging_middleware import LoggingMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .routers import news, delivery, admin, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル管理"""
    logger = setup_logger(__name__)
    
    # Startup
    logger.info("Starting News Delivery System FastAPI application...")
    
    try:
        # Initialize database
        await app.state.database.connect()
        logger.info("Database connection established")
        
        # Initialize Redis cache
        await app.state.redis_cache.connect()
        logger.info("Redis cache connection established")
        
        # Initialize security manager
        await app.state.security_manager.initialize()
        logger.info("Security manager initialized")
        
        # Start background tasks
        app.state.background_tasks = []
        
        logger.info("FastAPI application startup completed")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down News Delivery System...")
        
        # Stop background tasks
        for task in getattr(app.state, 'background_tasks', []):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close database connection
        if hasattr(app.state, 'database'):
            await app.state.database.disconnect()
            logger.info("Database connection closed")
        
        # Close Redis connection
        if hasattr(app.state, 'redis_cache'):
            await app.state.redis_cache.disconnect()
            logger.info("Redis connection closed")
        
        logger.info("Application shutdown completed")


def create_app() -> FastAPI:
    """FastAPIアプリケーション作成"""
    config = load_config()
    logger = setup_logger(__name__)
    
    # FastAPI インスタンス作成
    app = FastAPI(
        title="News Delivery System API",
        description="ニュース自動配信システム - CLAUDE.md仕様準拠",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # State initialization
    app.state.config = config
    app.state.logger = logger
    app.state.database = AsyncDatabase(config)
    app.state.redis_cache = RedisCache(config)
    app.state.security_manager = SecurityManager(config)
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get('security', 'allowed_origins', default=['http://localhost:3000']),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Add GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware, redis_client=app.state.redis_cache)
    
    # Include routers
    app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
    app.include_router(news.router, prefix="/api/v1/news", tags=["news"])
    app.include_router(delivery.router, prefix="/api/v1/delivery", tags=["delivery"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    
    # Global exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url)
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "status_code": 500,
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url)
            }
        )
    
    return app


# Dependency injection functions
async def get_database(app: FastAPI = Depends()) -> AsyncDatabase:
    """データベース依存性注入"""
    return app.state.database


async def get_redis_cache(app: FastAPI = Depends()) -> RedisCache:
    """Redis キャッシュ依存性注入"""
    return app.state.redis_cache


async def get_security_manager(app: FastAPI = Depends()) -> SecurityManager:
    """セキュリティマネージャー依存性注入"""
    return app.state.security_manager


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer()),
    security_manager: SecurityManager = Depends(get_security_manager)
) -> Optional[Dict[str, Any]]:
    """現在のユーザー取得"""
    try:
        token = credentials.credentials
        user_data = await security_manager.verify_token(token)
        return user_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Application instance
app = create_app()


if __name__ == "__main__":
    # 開発サーバー起動
    config = load_config()
    
    uvicorn.run(
        "src.fastapi_app:app",
        host=config.get('server', 'host', default='0.0.0.0'),
        port=config.get('server', 'port', default=8000),
        reload=config.get('server', 'reload', default=True),
        log_level=config.get('logging', 'level', default='info').lower(),
        access_log=True,
        use_colors=True
    )