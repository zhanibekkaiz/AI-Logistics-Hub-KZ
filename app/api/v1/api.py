"""
Основной роутер API v1 для AI Logistics Hub
"""

from fastapi import APIRouter

from app.api.v1.endpoints import calculation, tnved, supplier, tariffs, rls_tnved_info, telegram

# Создание основного роутера
api_router = APIRouter()

# Подключение роутеров эндпоинтов
api_router.include_router(
    calculation.router,
    prefix="/calculate",
    tags=["calculation"]
)

api_router.include_router(
    tnved.router,
    prefix="/tnved",
    tags=["tnved"]
)

api_router.include_router(
    supplier.router,
    prefix="/supplier",
    tags=["supplier"]
)

api_router.include_router(
    tariffs.router,
    prefix="/tariffs",
    tags=["tariffs"]
)

api_router.include_router(
    rls_tnved_info.router,
    prefix="/tnved-info",
    tags=["tnved-info"]
)

api_router.include_router(
    telegram.router,
    prefix="/telegram",
    tags=["telegram"]
)
