"""
Эндпоинты для работы с тарифами
"""

from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
import structlog

from app.models.schemas import (
    TariffInfo,
    DeliveryType,
    ErrorResponse,
    SuccessResponse
)
from app.services.airtable import AirtableService

logger = structlog.get_logger(__name__)

router = APIRouter()


def get_airtable_service() -> AirtableService:
    """Dependency для получения Airtable сервиса"""
    from app.main import airtable_service
    if not airtable_service:
        raise HTTPException(status_code=503, detail="Airtable service not available")
    return airtable_service


@router.get("/", response_model=List[TariffInfo])
async def get_tariffs(
    route: Optional[str] = Query(None, description="Маршрут (например: shenzhen-almaty)"),
    service_type: Optional[DeliveryType] = Query(None, description="Тип услуги"),
    airtable_service: AirtableService = Depends(get_airtable_service)
) -> List[TariffInfo]:
    """
    Получение списка тарифов с возможностью фильтрации
    """
    
    try:
        tariffs = await airtable_service.get_tariffs(
            route=route,
            service_type=service_type
        )
        
        logger.info(
            "Tariffs retrieved successfully",
            route=route,
            service_type=service_type,
            count=len(tariffs)
        )
        
        return tariffs
        
    except Exception as e:
        logger.error(
            "Failed to get tariffs",
            route=route,
            service_type=service_type,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при получении тарифов")


@router.get("/routes", response_model=List[str])
async def get_available_routes(
    airtable_service: AirtableService = Depends(get_airtable_service)
) -> List[str]:
    """
    Получение списка доступных маршрутов
    """
    
    try:
        routes = await airtable_service.get_available_routes()
        
        logger.info(
            "Available routes retrieved",
            count=len(routes)
        )
        
        return routes
        
    except Exception as e:
        logger.error(
            "Failed to get available routes",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при получении маршрутов")


@router.get("/{route}", response_model=Dict[str, Any])
async def get_route_tariffs(
    route: str,
    airtable_service: AirtableService = Depends(get_airtable_service)
) -> Dict[str, Any]:
    """
    Получение тарифов для конкретного маршрута
    """
    
    try:
        tariffs = await airtable_service.get_route_tariffs(route)
        
        if not tariffs:
            raise HTTPException(status_code=404, detail="Тарифы для маршрута не найдены")
        
        logger.info(
            "Route tariffs retrieved",
            route=route,
            count=len(tariffs)
        )
        
        return {
            "route": route,
            "tariffs": tariffs,
            "total_count": len(tariffs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get route tariffs",
            route=route,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при получении тарифов маршрута")


@router.post("/", response_model=TariffInfo)
async def create_tariff(
    tariff: TariffInfo,
    airtable_service: AirtableService = Depends(get_airtable_service)
) -> TariffInfo:
    """
    Создание нового тарифа
    
    TODO: Добавить авторизацию для администраторов
    """
    
    try:
        created_tariff = await airtable_service.create_tariff(tariff)
        
        logger.info(
            "Tariff created successfully",
            route=tariff.route,
            service_type=tariff.service_type,
            price_per_kg=float(tariff.price_per_kg)
        )
        
        return created_tariff
        
    except Exception as e:
        logger.error(
            "Failed to create tariff",
            route=tariff.route,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при создании тарифа")


@router.put("/{tariff_id}", response_model=TariffInfo)
async def update_tariff(
    tariff_id: str,
    tariff: TariffInfo,
    airtable_service: AirtableService = Depends(get_airtable_service)
) -> TariffInfo:
    """
    Обновление тарифа
    
    TODO: Добавить авторизацию для администраторов
    """
    
    try:
        updated_tariff = await airtable_service.update_tariff(tariff_id, tariff)
        
        if not updated_tariff:
            raise HTTPException(status_code=404, detail="Тариф не найден")
        
        logger.info(
            "Tariff updated successfully",
            tariff_id=tariff_id,
            route=tariff.route
        )
        
        return updated_tariff
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update tariff",
            tariff_id=tariff_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при обновлении тарифа")


@router.delete("/{tariff_id}")
async def delete_tariff(
    tariff_id: str,
    airtable_service: AirtableService = Depends(get_airtable_service)
) -> SuccessResponse:
    """
    Удаление тарифа
    
    TODO: Добавить авторизацию для администраторов
    """
    
    try:
        success = await airtable_service.delete_tariff(tariff_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Тариф не найден")
        
        logger.info("Tariff deleted successfully", tariff_id=tariff_id)
        
        return SuccessResponse(
            message="Тариф успешно удалён",
            data={"tariff_id": tariff_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete tariff",
            tariff_id=tariff_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при удалении тарифа")
