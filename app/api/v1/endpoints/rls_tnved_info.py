"""
Эндпоинты для работы с API tnved.info
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

import structlog

from app.core.config import get_settings
from app.models.schemas import (
    TNVEDSearchRequest,
    TNVEDSearchResponse,
    TNVEDSearchResult,
    TNVEDLicenseInfo,
    TNVEDRequest,
    TNVEDInfo,
    ErrorResponse,
    SuccessResponse
)
from app.services.rls_tnved_info import TNVEDInfoService

logger = structlog.get_logger(__name__)

router = APIRouter()


def get_tnved_info_service() -> Optional[TNVEDInfoService]:
    """Получение сервиса TNVED Info"""
    settings = get_settings()
    
    if not settings.TNVED_INFO_USERNAME or not settings.TNVED_INFO_PASSWORD:
        logger.warning("TNVED Info credentials not configured")
        return None
    
    return TNVEDInfoService(
        username=settings.TNVED_INFO_USERNAME,
        password=settings.TNVED_INFO_PASSWORD
    )


@router.post("/search", response_model=TNVEDSearchResponse)
async def search_tnved_codes(
    request: TNVEDSearchRequest,
    service: Optional[TNVEDInfoService] = Depends(get_tnved_info_service)
):
    """
    Поиск ТН ВЭД кодов по описанию или коду
    
    Использует API tnved.info для поиска кодов ТН ВЭД.
    Требует настройки TNVED_INFO_USERNAME и TNVED_INFO_PASSWORD в .env файле.
    """
    
    request_id = str(uuid.uuid4())
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="TNVED Info service not configured. Please set TNVED_INFO_USERNAME and TNVED_INFO_PASSWORD in .env file."
        )
    
    try:
        logger.info(
            "Searching TNVED codes via API",
            request_id=request_id,
            query=request.query,
            group=request.group
        )
        
        # Выполняем поиск
        result = await service.search_tnved_codes(
            query=request.query,
            group=request.group,
            request_id=request_id
        )
        
        if not result["success"]:
            return TNVEDSearchResponse(
                success=False,
                results=[],
                response_state=result.get("response_state", 500),
                error_message=result.get("error_message", "Search failed")
            )
        
        # Преобразуем результаты в Pydantic модели
        search_results = []
        for item in result.get("results", []):
            search_results.append(TNVEDSearchResult(
                probability=item.get("Probability", 0.0),
                code=item.get("Code", ""),
                description=item.get("Description", ""),
                start_date=item.get("StartDate"),
                end_date=item.get("EndDate"),
                is_old=item.get("IsOld", False)
            ))
        
        # Преобразуем информацию о лицензии
        license_info = None
        if result.get("license_info"):
            license_data = result["license_info"]
            license_info = TNVEDLicenseInfo(
                work_place=license_data.get("WorkPlace", ""),
                end_date=license_data.get("EndDate"),
                remain=license_data.get("Remain", 0),
                total=license_data.get("Total", 0)
            )
        
        response = TNVEDSearchResponse(
            success=True,
            results=search_results,
            license_info=license_info,
            response_state=result.get("response_state", 200),
            error_message=result.get("error_message")
        )
        
        logger.info(
            "TNVED search completed successfully",
            request_id=request_id,
            results_count=len(search_results)
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "TNVED search failed",
            request_id=request_id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"TNVED search failed: {str(e)}"
        )


@router.get("/search", response_model=TNVEDSearchResponse)
async def search_tnved_codes_get(
    query: str = Query(..., min_length=2, max_length=500, description="Поисковый запрос"),
    group: Optional[str] = Query(None, max_length=10, description="Фильтр по группам"),
    service: Optional[TNVEDInfoService] = Depends(get_tnved_info_service)
):
    """
    Поиск ТН ВЭД кодов по описанию или коду (GET метод)
    
    Использует API tnved.info для поиска кодов ТН ВЭД.
    Требует настройки TNVED_INFO_USERNAME и TNVED_INFO_PASSWORD в .env файле.
    """
    
    request = TNVEDSearchRequest(query=query, group=group)
    return await search_tnved_codes(request, service)


@router.get("/code/{tnved_code}", response_model=TNVEDInfo)
async def get_tnved_code_info(
    tnved_code: str,
    service: Optional[TNVEDInfoService] = Depends(get_tnved_info_service)
):
    """
    Получение информации о конкретном коде ТН ВЭД
    
    Args:
        tnved_code: Код ТН ВЭД (например, 8539310000)
    """
    
    request_id = str(uuid.uuid4())
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="TNVED Info service not configured. Please set TNVED_INFO_USERNAME and TNVED_INFO_PASSWORD in .env file."
        )
    
    try:
        logger.info(
            "Getting TNVED code info",
            request_id=request_id,
            tnved_code=tnved_code
        )
        
        tnved_info = await service.get_tnved_info(tnved_code, request_id=request_id)
        
        if not tnved_info:
            raise HTTPException(
                status_code=404,
                detail=f"TNVED code {tnved_code} not found"
            )
        
        logger.info(
            "TNVED code info retrieved successfully",
            request_id=request_id,
            tnved_code=tnved_code
        )
        
        return tnved_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get TNVED code info",
            request_id=request_id,
            tnved_code=tnved_code,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get TNVED code info: {str(e)}"
        )


@router.post("/classify", response_model=TNVEDInfo)
async def classify_product(
    request: TNVEDRequest,
    service: Optional[TNVEDInfoService] = Depends(get_tnved_info_service)
):
    """
    Автоматическое определение ТН ВЭД кода по описанию товара
    
    Использует API tnved.info для классификации товаров.
    """
    
    request_id = str(uuid.uuid4())
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="TNVED Info service not configured. Please set TNVED_INFO_USERNAME and TNVED_INFO_PASSWORD in .env file."
        )
    
    try:
        logger.info(
            "Classifying product via TNVED API",
            request_id=request_id,
            description_length=len(request.description),
            category=request.category
        )
        
        tnved_info = await service.classify_product(
            description=request.description,
            category=request.category,
            request_id=request_id
        )
        
        if not tnved_info:
            raise HTTPException(
                status_code=404,
                detail="Could not classify product. No suitable TNVED code found."
            )
        
        logger.info(
            "Product classified successfully",
            request_id=request_id,
            tnved_code=tnved_info.code
        )
        
        return tnved_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Product classification failed",
            request_id=request_id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Product classification failed: {str(e)}"
        )


@router.get("/license", response_model=TNVEDLicenseInfo)
async def get_license_info(
    service: Optional[TNVEDInfoService] = Depends(get_tnved_info_service)
):
    """
    Получение информации о лицензии TNVED API
    """
    
    request_id = str(uuid.uuid4())
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="TNVED Info service not configured. Please set TNVED_INFO_USERNAME and TNVED_INFO_PASSWORD in .env file."
        )
    
    try:
        logger.info(
            "Getting TNVED license info",
            request_id=request_id
        )
        
        license_info = await service.get_license_info()
        
        if not license_info:
            raise HTTPException(
                status_code=404,
                detail="License information not available"
            )
        
        # Преобразуем в Pydantic модель
        response = TNVEDLicenseInfo(
            work_place=license_info.get("WorkPlace", ""),
            end_date=license_info.get("EndDate"),
            remain=license_info.get("Remain", 0),
            total=license_info.get("Total", 0)
        )
        
        logger.info(
            "TNVED license info retrieved successfully",
            request_id=request_id,
            work_place=response.work_place,
            remain=response.remain
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get license info",
            request_id=request_id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get license info: {str(e)}"
        )


@router.get("/health", response_model=SuccessResponse)
async def health_check(
    service: Optional[TNVEDInfoService] = Depends(get_tnved_info_service)
):
    """
    Проверка работоспособности TNVED API
    """
    
    request_id = str(uuid.uuid4())
    
    if not service:
        return SuccessResponse(
            success=False,
            message="TNVED Info service not configured",
            data={"status": "not_configured"}
        )
    
    try:
        logger.info(
            "Checking TNVED API health",
            request_id=request_id
        )
        
        is_healthy = await service.health_check()
        
        if is_healthy:
            message = "TNVED API is healthy"
            status = "healthy"
        else:
            message = "TNVED API is not responding"
            status = "unhealthy"
        
        logger.info(
            "TNVED API health check completed",
            request_id=request_id,
            status=status
        )
        
        return SuccessResponse(
            success=is_healthy,
            message=message,
            data={"status": status}
        )
        
    except Exception as e:
        logger.error(
            "TNVED API health check failed",
            request_id=request_id,
            error=str(e),
            exc_info=True
        )
        
        return SuccessResponse(
            success=False,
            message=f"Health check failed: {str(e)}",
            data={"status": "error"}
        )


@router.post("/cache/clear", response_model=SuccessResponse)
async def clear_cache(
    service: Optional[TNVEDInfoService] = Depends(get_tnved_info_service)
):
    """
    Очистка кэша TNVED API
    """
    
    request_id = str(uuid.uuid4())
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="TNVED Info service not configured"
        )
    
    try:
        logger.info(
            "Clearing TNVED cache",
            request_id=request_id
        )
        
        service.clear_cache()
        
        logger.info(
            "TNVED cache cleared successfully",
            request_id=request_id
        )
        
        return SuccessResponse(
            success=True,
            message="TNVED cache cleared successfully"
        )
        
    except Exception as e:
        logger.error(
            "Failed to clear TNVED cache",
            request_id=request_id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )
