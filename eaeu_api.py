"""
Модуль для работы с API Евразийской Экономической Комиссии (ЕЭК).
Предоставляет класс EaeuClient для поиска справочников и получения информации о кодах ТН ВЭД.
"""

import aiohttp
import logging
from typing import Optional, Dict, Any
import asyncio

logger = logging.getLogger(__name__)

BASE_URL = "https://nsi.eaeunion.org/api/v1"
REQUEST_TIMEOUT = 30  # секунд
MAX_RETRIES = 3
RETRY_DELAY = 1  # секунд


class EaeuClient:
    """
    Клиент для работы с API Евразийской Экономической Комиссии.
    
    Использует асинхронные запросы через aiohttp для получения информации
    о справочниках и кодах ТН ВЭД.
    """
    
    def __init__(self):
        """Инициализация клиента."""
        self.base_url = BASE_URL
        self.tnved_dictionary_id: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать сессию aiohttp."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Закрыть сессию aiohttp."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def find_dictionary_id(self, name_part: str) -> Optional[str]:
        """
        Найти ID справочника по части названия.
        
        Args:
            name_part: Часть названия справочника для поиска
            
        Returns:
            ID справочника или None, если не найден
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/dictionaries"
            params = {
                "conditions[0].conditionType": "like",
                "conditions[0].code": "data.titleName",
                "conditions[0].value": name_part
            }
            
            logger.info(f"Поиск справочника: {name_part}")
            
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with session.get(url, params=params, timeout=timeout) as response:
                if response.status != 200:
                    logger.error(f"Ошибка API: статус {response.status}")
                    return None
                
                data = await response.json()
                
                # Обработка структуры ответа: pagination -> elements -> data
                if "pagination" in data and "elements" in data["pagination"]:
                    elements = data["pagination"]["elements"]
                    if elements and len(elements) > 0:
                        # Берем первый найденный справочник
                        dictionary_id = elements[0].get("id")
                        logger.info(f"Найден справочник ID: {dictionary_id}")
                        return dictionary_id
                
                logger.warning(f"Справочник '{name_part}' не найден")
                return None
                
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при поиске справочника: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при поиске справочника: {e}")
            return None
    
    async def _ensure_tnved_dictionary_id(self):
        """Убедиться, что ID справочника ТН ВЭД закеширован."""
        if self.tnved_dictionary_id is None:
            self.tnved_dictionary_id = await self.find_dictionary_id(
                "Товарная номенклатура внешнеэкономической деятельности"
            )
            if self.tnved_dictionary_id is None:
                # Попробуем альтернативные варианты поиска
                alternative_names = [
                    "ТН ВЭД",
                    "Товарная номенклатура",
                    "ВЭД"
                ]
                for alt_name in alternative_names:
                    self.tnved_dictionary_id = await self.find_dictionary_id(alt_name)
                    if self.tnved_dictionary_id:
                        break
    
    async def get_tnved_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о коде ТН ВЭД из официальной базы ЕЭК.
        
        Args:
            code: Код ТН ВЭД (10 знаков)
            
        Returns:
            Словарь с информацией о товаре или None, если не найден
        """
        try:
            # Убеждаемся, что ID справочника закеширован
            await self._ensure_tnved_dictionary_id()
            
            if self.tnved_dictionary_id is None:
                logger.error("Не удалось найти справочник ТН ВЭД")
                return None
            
            session = await self._get_session()
            url = f"{self.base_url}/dictionaries/{self.tnved_dictionary_id}/elements"
            params = {
                "conditions[0].conditionType": "eq",
                "conditions[0].code": "Code",
                "conditions[0].value": code
            }
            
            logger.info(f"Поиск кода ТН ВЭД: {code}")
            
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with session.get(url, params=params, timeout=timeout) as response:
                if response.status != 200:
                    logger.error(f"Ошибка API: статус {response.status}")
                    return None
                
                data = await response.json()
                
                # Обработка структуры ответа: pagination -> elements -> data
                if "pagination" in data and "elements" in data["pagination"]:
                    elements = data["pagination"]["elements"]
                    if elements and len(elements) > 0:
                        element_data = elements[0].get("data", {})
                        
                        # Извлекаем название/описание товара
                        result = {
                            "code": code,
                            "name": element_data.get("Name") or element_data.get("Description") or element_data.get("titleName"),
                            "full_data": element_data
                        }
                        
                        logger.info(f"Найдена информация для кода {code}")
                        return result
                
                logger.warning(f"Код ТН ВЭД '{code}' не найден")
                return None
                
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при получении информации о коде: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении информации о коде: {e}")
            return None
    
    async def __aenter__(self):
        """Поддержка async context manager."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие сессии при выходе из context manager."""
        await self.close()

