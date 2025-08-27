"""
Сервис для работы с ТН ВЭД API (tnved.info, keden.kz)
"""

import asyncio
from typing import List, Optional, Dict, Any
from decimal import Decimal

import aiohttp
import structlog

from app.models.schemas import TNVEDInfo, CargoCategory

logger = structlog.get_logger(__name__)


class TNVEDService:
    """Сервис для работы с ТН ВЭД API"""
    
    def __init__(self, tnved_api_key: Optional[str] = None, keden_api_key: Optional[str] = None):
        self.tnved_api_key = tnved_api_key
        self.keden_api_key = keden_api_key
        
        # Базовые URL для API
        self.tnved_base_url = "https://api.tnved.info"
        self.keden_base_url = "https://api.keden.kz"
        
        # Кэш для часто используемых кодов
        self._cache = {}
    
    async def _make_request(
        self, 
        url: str, 
        headers: Optional[Dict] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Выполнение HTTP запроса"""
        
        default_headers = {
            "Content-Type": "application/json",
            "User-Agent": "AI-Logistics-Hub/1.0"
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=default_headers,
                    timeout=timeout
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"TNVED API error: {response.status} - {error_text}"
                        )
                        raise Exception(f"TNVED API error: {response.status}")
                        
        except asyncio.TimeoutError:
            logger.error("TNVED API request timeout")
            raise Exception("TNVED API request timeout")
        except Exception as e:
            logger.error(f"TNVED API request failed: {e}")
            raise
    
    async def classify_product(
        self, 
        description: str, 
        category: Optional[CargoCategory] = None,
        request_id: Optional[str] = None
    ) -> TNVEDInfo:
        """
        Автоматическое определение ТН ВЭД кода по описанию товара
        
        TODO: Интегрировать с реальными API tnved.info/keden.kz
        Пока используем простую логику на основе ключевых слов
        """
        
        try:
            logger.info(
                "Classifying product",
                request_id=request_id,
                description_length=len(description),
                category=category
            )
            
            # Простая логика классификации на основе ключевых слов
            # В реальном проекте здесь будет интеграция с AI/ML моделью
            tnved_code = self._simple_classification(description, category)
            
            # Получаем дополнительную информацию о коде
            tnved_info = await self.get_tnved_info(tnved_code)
            
            if not tnved_info:
                # Создаём базовую информацию если API недоступен
                tnved_info = TNVEDInfo(
                    code=tnved_code,
                    description=description,
                    duty_rate=Decimal("5.0"),  # Базовая ставка
                    vat_rate=Decimal("12.0"),  # НДС в Казахстане
                    required_documents=self._get_required_documents(category),
                    restrictions=[]
                )
            
            logger.info(
                "Product classified successfully",
                request_id=request_id,
                tnved_code=tnved_code
            )
            
            return tnved_info
            
        except Exception as e:
            logger.error(
                "Product classification failed",
                request_id=request_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    def _simple_classification(self, description: str, category: Optional[CargoCategory] = None) -> str:
        """Простая классификация на основе ключевых слов"""
        
        description_lower = description.lower()
        
        # Электроника
        if any(word in description_lower for word in ["led", "light", "bulb", "lamp", "electronic"]):
            return "8539.31.000.0"  # Лампы светодиодные
        
        # Одежда
        if any(word in description_lower for word in ["shirt", "dress", "clothing", "fabric"]):
            return "6104.43.000.0"  # Платья женские
        
        # Машины и оборудование
        if any(word in description_lower for word in ["machine", "equipment", "tool"]):
            return "8471.30.000.0"  # Портативные вычислительные машины
        
        # Химия
        if any(word in description_lower for word in ["chemical", "paint", "varnish"]):
            return "3208.10.000.0"  # Краски и лаки
        
        # Продукты питания
        if any(word in description_lower for word in ["food", "tea", "coffee"]):
            return "0901.11.000.0"  # Чай зеленый
        
        # По умолчанию - прочие товары
        return "9999.99.000.0"
    
    def _get_required_documents(self, category: Optional[CargoCategory] = None) -> List[str]:
        """Получение списка требуемых документов по категории"""
        
        base_documents = ["Инвойс", "Упаковочный лист", "Сертификат происхождения"]
        
        if category == CargoCategory.ELECTRONICS:
            return base_documents + ["Сертификат соответствия", "Декларация соответствия"]
        elif category == CargoCategory.CHEMICALS:
            return base_documents + ["Сертификат безопасности", "Паспорт безопасности"]
        elif category == CargoCategory.FOOD:
            return base_documents + ["Сертификат качества", "Ветеринарный сертификат"]
        else:
            return base_documents
    
    async def get_tnved_info(self, tnved_code: str) -> Optional[TNVEDInfo]:
        """Получение информации о ТН ВЭД коде"""
        
        # Проверяем кэш
        if tnved_code in self._cache:
            return self._cache[tnved_code]
        
        try:
            # Пытаемся получить информацию из tnved.info
            if self.tnved_api_key:
                url = f"{self.tnved_base_url}/api/v1/codes/{tnved_code}"
                headers = {"Authorization": f"Bearer {self.tnved_api_key}"}
                
                response = await self._make_request(url, headers)
                
                if response:
                    tnved_info = TNVEDInfo(
                        code=tnved_code,
                        description=response.get("description", ""),
                        duty_rate=Decimal(str(response.get("duty_rate", 5.0))),
                        vat_rate=Decimal(str(response.get("vat_rate", 12.0))),
                        required_documents=response.get("required_documents", []),
                        restrictions=response.get("restrictions", [])
                    )
                    
                    # Сохраняем в кэш
                    self._cache[tnved_code] = tnved_info
                    return tnved_info
            
            # Если tnved.info недоступен, пробуем keden.kz
            if self.keden_api_key:
                url = f"{self.keden_base_url}/api/tnved/{tnved_code}"
                headers = {"X-API-Key": self.keden_api_key}
                
                response = await self._make_request(url, headers)
                
                if response:
                    tnved_info = TNVEDInfo(
                        code=tnved_code,
                        description=response.get("name", ""),
                        duty_rate=Decimal(str(response.get("duty", 5.0))),
                        vat_rate=Decimal(str(response.get("vat", 12.0))),
                        required_documents=response.get("documents", []),
                        restrictions=response.get("restrictions", [])
                    )
                    
                    # Сохраняем в кэш
                    self._cache[tnved_code] = tnved_info
                    return tnved_info
            
            # Если API недоступны, возвращаем None
            return None
            
        except Exception as e:
            logger.error(f"Failed to get TNVED info for code {tnved_code}: {e}")
            return None
    
    async def search_tnved_codes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Поиск ТН ВЭД кодов по ключевым словам"""
        
        try:
            results = []
            
            # Пытаемся найти в tnved.info
            if self.tnved_api_key:
                url = f"{self.tnved_base_url}/api/v1/search?q={query}&limit={limit}"
                headers = {"Authorization": f"Bearer {self.tnved_api_key}"}
                
                response = await self._make_request(url, headers)
                
                if response and "results" in response:
                    results.extend(response["results"])
            
            # Если результатов мало, пробуем keden.kz
            if len(results) < limit and self.keden_api_key:
                url = f"{self.keden_base_url}/api/search?query={query}&limit={limit - len(results)}"
                headers = {"X-API-Key": self.keden_api_key}
                
                response = await self._make_request(url, headers)
                
                if response and "items" in response:
                    results.extend(response["items"])
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search TNVED codes: {e}")
            return []
    
    async def get_duty_info(self, tnved_code: str) -> Optional[Dict[str, Any]]:
        """Получение информации о пошлинах для ТН ВЭД кода"""
        
        try:
            tnved_info = await self.get_tnved_info(tnved_code)
            
            if not tnved_info:
                return None
            
            return {
                "tnved_code": tnved_code,
                "duty_rate": float(tnved_info.duty_rate) if tnved_info.duty_rate else None,
                "vat_rate": float(tnved_info.vat_rate) if tnved_info.vat_rate else None,
                "required_documents": tnved_info.required_documents,
                "restrictions": tnved_info.restrictions,
                "description": tnved_info.description
            }
            
        except Exception as e:
            logger.error(f"Failed to get duty info for code {tnved_code}: {e}")
            return None
    
    def clear_cache(self) -> None:
        """Очистка кэша"""
        self._cache.clear()
        logger.info("TNVED cache cleared")
