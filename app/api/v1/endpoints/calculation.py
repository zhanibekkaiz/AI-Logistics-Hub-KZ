"""
Эндпоинты для расчёта доставки
Основной функционал MVP
"""

import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import structlog

from app.models.schemas import (
    CalculationRequest,
    CalculationResult,
    ErrorResponse,
    SuccessResponse
)
from app.services.calculation import CalculationService
from app.services.airtable import AirtableService
from app.services.tnved import TNVEDService
from app.core.logging import log_business_event

logger = structlog.get_logger(__name__)

router = APIRouter()


def get_calculation_service() -> CalculationService:
    """Dependency для получения сервиса расчётов"""
    # TODO: Получать из глобального состояния приложения
    from app.main import calculation_service
    if not calculation_service:
        raise HTTPException(status_code=503, detail="Calculation service not available")
    return calculation_service


@router.post("/", response_model=CalculationResult)
async def calculate_delivery(
    request: CalculationRequest,
    calculation_service: CalculationService = Depends(get_calculation_service)
) -> CalculationResult:
    """
    Расчёт стоимости доставки (карго vs белая)
    
    Основной эндпоинт MVP для сравнения типов доставки
    """
    
    request_id = f"calc_{uuid.uuid4().hex[:8]}"
    
    try:
        logger.info(
            "Calculation request received",
            request_id=request_id,
            weight=float(request.weight),
            volume=float(request.volume),
            category=request.category,
            origin=request.origin,
            destination=request.destination
        )
        
        # Логируем бизнес-событие
        log_business_event(
            logger,
            "calculation_requested",
            request_id=request_id,
            weight=float(request.weight),
            category=request.category,
            origin=request.origin,
            destination=request.destination
        )
        
        # Выполняем расчёт
        result = await calculation_service.calculate_delivery(
            request=request,
            request_id=request_id
        )
        
        logger.info(
            "Calculation completed successfully",
            request_id=request_id,
            cargo_cost=result.cargo_delivery.get("total_cost"),
            white_cost=result.white_delivery.get("total_cost")
        )
        
        return result
        
    except ValueError as e:
        logger.warning(
            "Validation error in calculation",
            request_id=request_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(
            "Calculation failed",
            request_id=request_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при расчёте доставки")


@router.get("/{request_id}", response_model=CalculationResult)
async def get_calculation_result(
    request_id: str,
    calculation_service: CalculationService = Depends(get_calculation_service)
) -> CalculationResult:
    """
    Получение результата расчёта по ID
    """
    
    try:
        result = await calculation_service.get_calculation_by_id(request_id)
        if not result:
            raise HTTPException(status_code=404, detail="Расчёт не найден")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get calculation result",
            request_id=request_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при получении результата")


@router.post("/batch", response_model=Dict[str, Any])
async def calculate_batch(
    requests: list[CalculationRequest],
    calculation_service: CalculationService = Depends(get_calculation_service)
) -> Dict[str, Any]:
    """
    Пакетный расчёт нескольких доставок
    """
    
    if len(requests) > 10:
        raise HTTPException(status_code=400, detail="Максимум 10 запросов за раз")
    
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    results = []
    
    logger.info(
        "Batch calculation started",
        batch_id=batch_id,
        request_count=len(requests)
    )
    
    try:
        for i, request in enumerate(requests):
            request_id = f"{batch_id}_{i+1}"
            
            try:
                result = await calculation_service.calculate_delivery(
                    request=request,
                    request_id=request_id
                )
                results.append({
                    "request_id": request_id,
                    "status": "success",
                    "result": result
                })
                
            except Exception as e:
                logger.error(
                    "Failed to calculate request in batch",
                    batch_id=batch_id,
                    request_id=request_id,
                    error=str(e)
                )
                results.append({
                    "request_id": request_id,
                    "status": "error",
                    "error": str(e)
                })
        
        logger.info(
            "Batch calculation completed",
            batch_id=batch_id,
            success_count=len([r for r in results if r["status"] == "success"]),
            error_count=len([r for r in results if r["status"] == "error"])
        )
        
        return {
            "batch_id": batch_id,
            "total_requests": len(requests),
            "successful": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"]),
            "results": results
        }
        
    except Exception as e:
        logger.error(
            "Batch calculation failed",
            batch_id=batch_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при пакетном расчёте")


@router.get("/history/{user_id}", response_model=Dict[str, Any])
async def get_calculation_history(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    calculation_service: CalculationService = Depends(get_calculation_service)
) -> Dict[str, Any]:
    """
    История расчётов пользователя
    """
    
    try:
        history = await calculation_service.get_user_calculation_history(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "user_id": user_id,
            "total_count": len(history),
            "limit": limit,
            "offset": offset,
            "calculations": history
        }
        
    except Exception as e:
        logger.error(
            "Failed to get calculation history",
            user_id=user_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при получении истории")


@router.delete("/{request_id}")
async def delete_calculation(
    request_id: str,
    calculation_service: CalculationService = Depends(get_calculation_service)
) -> SuccessResponse:
    """
    Удаление расчёта
    """
    
    try:
        success = await calculation_service.delete_calculation(request_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Расчёт не найден")
        
        logger.info("Calculation deleted", request_id=request_id)
        
        return SuccessResponse(
            message="Расчёт успешно удалён",
            data={"request_id": request_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete calculation",
            request_id=request_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при удалении расчёта")
