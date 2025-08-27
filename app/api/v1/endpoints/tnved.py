"""
Эндпоинты для работы с ТН ВЭД кодами
"""

import uuid
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
import structlog

from app.models.schemas import (
    TNVEDRequest,
    TNVEDInfo,
    ErrorResponse,
    SuccessResponse
)
from app.services.tnved import TNVEDService
from app.core.logging import log_business_event

logger = structlog.get_logger(__name__)

router = APIRouter()


def get_tnved_service() -> TNVEDService:
    """Dependency для получения TNVED сервиса"""
    from app.main import tnved_service
    if not tnved_service:
        raise HTTPException(status_code=503, detail="TNVED service not available")
    return tnved_service


@router.post("/classify", response_model=TNVEDInfo)
async def classify_product(
    request: TNVEDRequest,
    tnved_service: TNVEDService = Depends(get_tnved_service)
) -> TNVEDInfo:
    """
    Автоматическое определение ТН ВЭД кода по описанию товара
    """
    
    request_id = f"tnved_{uuid.uuid4().hex[:8]}"
    
    try:
        logger.info(
            "TNVED classification request received",
            request_id=request_id,
            description_length=len(request.description),
            category=request.category
        )
        
        # Логируем бизнес-событие
        log_business_event(
            logger,
            "tnved_classification_requested",
            request_id=request_id,
            category=request.category
        )
        
        # Выполняем классификацию
        result = await tnved_service.classify_product(
            description=request.description,
            category=request.category,
            request_id=request_id
        )
        
        logger.info(
            "TNVED classification completed",
            request_id=request_id,
            tnved_code=result.code
        )
        
        return result
        
    except ValueError as e:
        logger.warning(
            "Validation error in TNVED classification",
            request_id=request_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(
            "TNVED classification failed",
            request_id=request_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при определении ТН ВЭД")


@router.get("/code/{tnved_code}", response_model=TNVEDInfo)
async def get_tnved_info(
    tnved_code: str,
    tnved_service: TNVEDService = Depends(get_tnved_service)
) -> TNVEDInfo:
    """
    Получение информации о ТН ВЭД коде
    """
    
    try:
        result = await tnved_service.get_tnved_info(tnved_code)
        if not result:
            raise HTTPException(status_code=404, detail="ТН ВЭД код не найден")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get TNVED info",
            tnved_code=tnved_code,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при получении информации о ТН ВЭД")


@router.get("/search", response_model=Dict[str, Any])
async def search_tnved_codes(
    query: str,
    limit: int = 10,
    tnved_service: TNVEDService = Depends(get_tnved_service)
) -> Dict[str, Any]:
    """
    Поиск ТН ВЭД кодов по ключевым словам
    """
    
    if len(query) < 3:
        raise HTTPException(status_code=400, detail="Поисковый запрос должен содержать минимум 3 символа")
    
    try:
        results = await tnved_service.search_tnved_codes(
            query=query,
            limit=limit
        )
        
        return {
            "query": query,
            "total_found": len(results),
            "limit": limit,
            "results": results
        }
        
    except Exception as e:
        logger.error(
            "TNVED search failed",
            query=query,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при поиске ТН ВЭД кодов")


@router.get("/duty/{tnved_code}", response_model=Dict[str, Any])
async def get_duty_info(
    tnved_code: str,
    tnved_service: TNVEDService = Depends(get_tnved_service)
) -> Dict[str, Any]:
    """
    Получение информации о пошлинах для ТН ВЭД кода
    """
    
    try:
        duty_info = await tnved_service.get_duty_info(tnved_code)
        if not duty_info:
            raise HTTPException(status_code=404, detail="Информация о пошлинах не найдена")
        
        return duty_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get duty info",
            tnved_code=tnved_code,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Ошибка при получении информации о пошлинах")
