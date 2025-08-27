"""
AI Logistics Hub - Main Application
Интеллектуальный сервис для расчёта логистики и проверки поставщиков из Китая
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.api import api_router
from app.services.airtable import AirtableService
from app.services.tnved import TNVEDService
from app.services.calculation import CalculationService

# Настройка логирования
setup_logging()
logger = structlog.get_logger(__name__)

# Глобальные сервисы
airtable_service: AirtableService = None
tnved_service: TNVEDService = None
calculation_service: CalculationService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global airtable_service, tnved_service, calculation_service
    
    # Инициализация сервисов при запуске
    logger.info("Starting AI Logistics Hub application")
    
    try:
        # Инициализация Airtable сервиса
        airtable_service = AirtableService(
            api_key=settings.AIRTABLE_API_KEY,
            base_id=settings.AIRTABLE_BASE_ID
        )
        await airtable_service.initialize()
        logger.info("Airtable service initialized successfully")
        
        # Инициализация TNVED сервиса
        tnved_service = TNVEDService(
            tnved_api_key=settings.TNVED_API_KEY,
            keden_api_key=settings.KEDEN_API_KEY
        )
        logger.info("TNVED service initialized successfully")
        
        # Инициализация сервиса расчётов
        calculation_service = CalculationService(
            airtable_service=airtable_service,
            tnved_service=tnved_service
        )
        logger.info("Calculation service initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Очистка при завершении
    logger.info("Shutting down AI Logistics Hub application")


# Создание FastAPI приложения
app = FastAPI(
    title="AI Logistics Hub",
    description="Интеллектуальный сервис для расчёта логистики и проверки поставщиков из Китая",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик исключений"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "Произошла внутренняя ошибка сервера",
            "request_id": request.headers.get("X-Request-ID", "unknown")
        }
    )


@app.get("/")
async def root() -> Dict[str, Any]:
    """Корневой эндпоинт"""
    return {
        "message": "AI Logistics Hub API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Проверка здоровья сервиса"""
    try:
        # Проверка подключения к Airtable
        airtable_status = "healthy" if airtable_service else "unavailable"
        
        # Проверка TNVED сервиса
        tnved_status = "healthy" if tnved_service else "unavailable"
        
        return {
            "status": "healthy",
            "services": {
                "airtable": airtable_status,
                "tnved": tnved_status,
                "calculation": "healthy" if calculation_service else "unavailable"
            },
            "timestamp": "2024-01-01T00:00:00Z"  # TODO: добавить реальное время
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
