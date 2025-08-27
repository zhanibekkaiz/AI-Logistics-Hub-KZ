"""
Сервис для интеграции с API tnved.info
Лицензия ТНВЭД API также действует и на сайте tnved.info
"""

import base64
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

import aiohttp
import structlog

from app.models.schemas import TNVEDInfo, CargoCategory

logger = structlog.get_logger(__name__)


class TNVEDInfoService:
    """Сервис для работы с API tnved.info"""
    
    def __init__(self, username: str, password: str):
        """
        Инициализация сервиса
        
        Args:
            username: Логин для входа на tnved.info
            password: Пароль для входа на tnved.info
        """
        self.username = username
        self.password = password
        self.base_url = "https://api.tnved.info"
        self.search_endpoint = "/ExternalApi/Search"
        
        # Создаём Basic authentication header
        self.auth_header = self._create_auth_header()
        
        # Кэш для часто используемых кодов
        self._cache = {}
        
        logger.info("TNVED Info service initialized", username=username)
    
    def _create_auth_header(self) -> str:
        """Создание Basic authentication header"""
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        return f"Basic {encoded_credentials}"
    
    async def _make_request(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Выполнение HTTP запроса к API tnved.info"""
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": self.auth_header,
            "User-Agent": "AI-Logistics-Hub/1.0"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=timeout
                ) as response:
                    
                    response_text = await response.text()
                    
                    if response.status == 200:
                        try:
                            return await response.json()
                        except Exception as e:
                            logger.error(f"Failed to parse JSON response: {e}")
                            raise Exception(f"Invalid JSON response: {response_text}")
                    
                    elif response.status == 401:
                        logger.error("Unauthorized access to TNVED API")
                        raise Exception("Unauthorized access to TNVED API. Check username and password.")
                    
                    elif response.status == 403:
                        logger.error("TNVED API license expired")
                        raise Exception("TNVED API license expired. Please renew your license.")
                    
                    elif response.status == 203:
                        logger.info("No results found for the query")
                        return {"Result": [], "ResponseState": 203}
                    
                    elif response.status == 301:
                        logger.warning("Incomplete TNVED code provided")
                        return {"Result": [], "ResponseState": 301, "ErrorMessage": "Incomplete TNVED code"}
                    
                    elif response.status == 449:
                        logger.warning("TNVED API is updating. Please try again later.")
                        raise Exception("TNVED API is updating. Please try again in a few seconds.")
                    
                    elif response.status == 500:
                        logger.error("TNVED API internal server error")
                        raise Exception("TNVED API internal server error")
                    
                    else:
                        logger.error(f"TNVED API error: {response.status} - {response_text}")
                        raise Exception(f"TNVED API error: {response.status}")
                        
        except asyncio.TimeoutError:
            logger.error("TNVED API request timeout")
            raise Exception("TNVED API request timeout")
        except Exception as e:
            logger.error(f"TNVED API request failed: {e}")
            raise
    
    async def search_tnved_codes(
        self, 
        query: str, 
        group: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Поиск ТН ВЭД кодов по описанию или коду
        
        Args:
            query: Поисковый запрос (описание товара или код ТН ВЭД)
            group: Фильтр по группам (например, "0704")
            request_id: ID запроса для логирования
            
        Returns:
            Словарь с результатами поиска
        """
        
        try:
            logger.info(
                "Searching TNVED codes",
                request_id=request_id,
                query=query,
                group=group
            )
            
            # Формируем параметры запроса
            params = {"query": query}
            if group:
                params["group"] = group
            
            # Выполняем запрос
            url = f"{self.base_url}{self.search_endpoint}"
            response = await self._make_request(url, params)
            
            # Проверяем состояние ответа
            response_state = response.get("ResponseState", 0)
            
            if response_state in [200, 201]:
                results = response.get("Result", [])
                license_info = response.get("License", {})
                
                logger.info(
                    "TNVED search completed successfully",
                    request_id=request_id,
                    results_count=len(results),
                    license_remain=license_info.get("Remain", 0)
                )
                
                return {
                    "success": True,
                    "results": results,
                    "license_info": license_info,
                    "response_state": response_state,
                    "error_message": response.get("ErrorMessage")
                }
            
            else:
                logger.warning(
                    "TNVED search returned non-success state",
                    request_id=request_id,
                    response_state=response_state,
                    error_message=response.get("ErrorMessage")
                )
                
                return {
                    "success": False,
                    "results": [],
                    "response_state": response_state,
                    "error_message": response.get("ErrorMessage")
                }
                
        except Exception as e:
            logger.error(
                "TNVED search failed",
                request_id=request_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def get_tnved_info(
        self, 
        tnved_code: str,
        request_id: Optional[str] = None
    ) -> Optional[TNVEDInfo]:
        """
        Получение информации о конкретном коде ТН ВЭД
        
        Args:
            tnved_code: Код ТН ВЭД
            request_id: ID запроса для логирования
            
        Returns:
            Информация о ТН ВЭД коде или None
        """
        
        # Проверяем кэш
        cache_key = f"tnved_{tnved_code}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            logger.info(
                "Getting TNVED info",
                request_id=request_id,
                tnved_code=tnved_code
            )
            
            # Ищем код в API
            search_result = await self.search_tnved_codes(tnved_code, request_id=request_id)
            
            if not search_result["success"]:
                logger.warning(
                    "Failed to get TNVED info",
                    request_id=request_id,
                    tnved_code=tnved_code,
                    error=search_result.get("error_message")
                )
                return None
            
            results = search_result.get("results", [])
            
            # Ищем точное совпадение кода
            exact_match = None
            for result in results:
                if result.get("Code") == tnved_code:
                    exact_match = result
                    break
            
            if not exact_match and results:
                # Если точного совпадения нет, берём первый результат
                exact_match = results[0]
            
            if exact_match:
                # Создаём объект TNVEDInfo
                tnved_info = TNVEDInfo(
                    code=exact_match.get("Code", tnved_code),
                    description=exact_match.get("Description", ""),
                    duty_rate=Decimal("5.0"),  # Базовая ставка (можно расширить)
                    vat_rate=Decimal("12.0"),  # НДС в Казахстане
                    required_documents=self._get_required_documents_by_code(tnved_code),
                    restrictions=[]
                )
                
                # Сохраняем в кэш
                self._cache[cache_key] = tnved_info
                
                logger.info(
                    "TNVED info retrieved successfully",
                    request_id=request_id,
                    tnved_code=tnved_code
                )
                
                return tnved_info
            
            logger.warning(
                "TNVED code not found",
                request_id=request_id,
                tnved_code=tnved_code
            )
            return None
            
        except Exception as e:
            logger.error(
                "Failed to get TNVED info",
                request_id=request_id,
                tnved_code=tnved_code,
                error=str(e),
                exc_info=True
            )
            return None
    
    async def classify_product(
        self, 
        description: str, 
        category: Optional[CargoCategory] = None,
        request_id: Optional[str] = None
    ) -> Optional[TNVEDInfo]:
        """
        Автоматическое определение ТН ВЭД кода по описанию товара
        
        Args:
            description: Описание товара
            category: Категория товара
            request_id: ID запроса для логирования
            
        Returns:
            Информация о ТН ВЭД коде или None
        """
        
        try:
            logger.info(
                "Classifying product using TNVED API",
                request_id=request_id,
                description_length=len(description),
                category=category
            )
            
            # Ищем по описанию
            search_result = await self.search_tnved_codes(description, request_id=request_id)
            
            if not search_result["success"]:
                logger.warning(
                    "Product classification failed",
                    request_id=request_id,
                    error=search_result.get("error_message")
                )
                return None
            
            results = search_result.get("results", [])
            
            if not results:
                logger.warning(
                    "No TNVED codes found for product description",
                    request_id=request_id
                )
                return None
            
            # Берём результат с наивысшей вероятностью
            best_match = max(results, key=lambda x: x.get("Probability", 0))
            
            # Создаём объект TNVEDInfo
            tnved_info = TNVEDInfo(
                code=best_match.get("Code", ""),
                description=best_match.get("Description", description),
                duty_rate=Decimal("5.0"),  # Базовая ставка
                vat_rate=Decimal("12.0"),  # НДС в Казахстане
                required_documents=self._get_required_documents_by_category(category),
                restrictions=[]
            )
            
            logger.info(
                "Product classified successfully",
                request_id=request_id,
                tnved_code=tnved_info.code,
                probability=best_match.get("Probability", 0)
            )
            
            return tnved_info
            
        except Exception as e:
            logger.error(
                "Product classification failed",
                request_id=request_id,
                error=str(e),
                exc_info=True
            )
            return None
    
    def _get_required_documents_by_code(self, tnved_code: str) -> List[str]:
        """Получение требуемых документов по коду ТН ВЭД"""
        
        base_documents = ["Инвойс", "Упаковочный лист", "Сертификат происхождения"]
        
        # Простая логика на основе кода
        if tnved_code.startswith("85"):  # Электроника
            return base_documents + ["Сертификат соответствия", "Декларация соответствия"]
        elif tnved_code.startswith("61") or tnved_code.startswith("62"):  # Одежда
            return base_documents + ["Сертификат качества"]
        elif tnved_code.startswith("32"):  # Химия
            return base_documents + ["Сертификат безопасности", "Паспорт безопасности"]
        elif tnved_code.startswith("09"):  # Продукты питания
            return base_documents + ["Сертификат качества", "Ветеринарный сертификат"]
        else:
            return base_documents
    
    def _get_required_documents_by_category(self, category: Optional[CargoCategory]) -> List[str]:
        """Получение требуемых документов по категории товара"""
        
        base_documents = ["Инвойс", "Упаковочный лист", "Сертификат происхождения"]
        
        if category == CargoCategory.ELECTRONICS:
            return base_documents + ["Сертификат соответствия", "Декларация соответствия"]
        elif category == CargoCategory.CHEMICALS:
            return base_documents + ["Сертификат безопасности", "Паспорт безопасности"]
        elif category == CargoCategory.FOOD:
            return base_documents + ["Сертификат качества", "Ветеринарный сертификат"]
        else:
            return base_documents
    
    async def get_license_info(self) -> Optional[Dict[str, Any]]:
        """Получение информации о лицензии"""
        
        try:
            # Делаем тестовый запрос для получения информации о лицензии
            search_result = await self.search_tnved_codes("test")
            
            if search_result["success"]:
                return search_result.get("license_info")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get license info: {e}")
            return None
    
    def clear_cache(self) -> None:
        """Очистка кэша"""
        self._cache.clear()
        logger.info("TNVED Info cache cleared")
    
    async def health_check(self) -> bool:
        """Проверка работоспособности API"""
        
        try:
            # Делаем простой запрос для проверки
            search_result = await self.search_tnved_codes("test")
            return search_result["success"]
            
        except Exception as e:
            logger.error(f"TNVED API health check failed: {e}")
            return False
